from collections import defaultdict
from enum import Enum
import typing
import logging
from common.mixins import BaseLoggerMixin
from evaluation.event_flow.helpers.db_helper import EventFlowDbHelper

from evaluation.models import EventFlow, EventFlowProcessorState
from config.celery import app
from evaluation.event_flow.core.dag_config import DAG, PROCESSOR_QUEUE_MAPPING


logger = logging.getLogger(__name__)


class TerminationCause(Enum):
        MANUAL = 1
        PROCESSOR_ERROR = 2

TERMINATION_CAUSE_EVENTFLOW_STATUS_MAP = {
    TerminationCause.MANUAL : EventFlow.Status.ABORTED,
    TerminationCause.PROCESSOR_ERROR: EventFlow.Status.ERROR,
}

class Orchestrator(BaseLoggerMixin):

    _logger = logger

    def get_formatted_msg(self, msg):
        return f"OrchestratorLog:[{self.id}]:{msg}"

    @staticmethod
    def get_dag_from_eventflow_type(eventflow_type: str):
        return DAG[eventflow_type]

    @staticmethod
    def start_new_eventflow(*, eventflow_type: str = "default", root_args: typing.Dict, initiated_by: str) -> str:
        dag = Orchestrator.get_dag_from_eventflow_type(eventflow_type)
        
        ef = EventFlow.objects.create(type=eventflow_type, 
                                      root_arguments=root_args,
                                      initiated_by=initiated_by)
        logger.info(f"OrchestratorLog:[{ef.id}]:Created eventflow = {ef}. Type-{eventflow_type}.")
        
        Orchestrator.initialise_eventflow_processors(ef.id, dag["processors"].keys())

        logger.info(f"OrchestratorLog:[{ef.id}]:Created processors states for event flow = {ef}. Type-{eventflow_type}.")
        
        Orchestrator(eventflow_id=ef.id, root_args=root_args, initial=True)
        return ef.id
    
    @staticmethod
    def initialise_eventflow_processors(eventflow_id, processor_names):
        efp_states = []
        for processor in processor_names:
            efp_states.append(EventFlowProcessorState(event_flow_id=eventflow_id,
                                                      processor_name=processor))

        EventFlowProcessorState.objects.bulk_create(efp_states)

    @staticmethod
    def reset_and_restart_eventflow(*, eventflow_id):
        ef_db_helper = EventFlowDbHelper(eventflow_id)
        dag = Orchestrator.get_dag_from_eventflow_type(ef_db_helper.eventflow_type)
        ef_db_helper.reset_all_processors_state(termination_processors=dag["termination_processor"].keys())
        logger.info(f"OrchestratorLog:[{eventflow_id}]:Restarting eventflow, Type-{ef_db_helper.eventflow_type}, with args {ef_db_helper.eventflow_root_args}")
        Orchestrator(eventflow_id=eventflow_id, initial=True, 
                     root_args=ef_db_helper.eventflow_root_args)

    @staticmethod
    def retry_eventflow(*, eventflow_id):
        orchestrator = Orchestrator(eventflow_id=eventflow_id, root_args=None)
        orchestrator._retry_eventflow()

    def _retry_eventflow(self):
        """
        Get all erred processors
        Iterate over error processors, if not all their providers are complete, raise error. This is unexpected, since
        all providers should have completed before running this.
        Reset all error and aborted processors.
        Delete all termination processor states
        Set eventflow state to started again, so orchestration doesn't ignore running the processors.
        Call the error processors again, they will further trigger the next processors
        """
        error_processor_names = self.ef_db_helper.get_processor_names_by_status(EventFlowProcessorState.Status.ERROR)
        termination_processors = self.dag["termination_processor"].keys()
        for processor_name in error_processor_names:
            if processor_name in termination_processors:
                continue
            if not self.check_if_providers_are_done(processor_name=processor_name):
                raise ValueError(f"Unexpected State - Processor {processor_name} is in error state but all of its "
                                 f"providers are not done. Won't restart. Fix state manually. Eventflow id - {self.id}.")
        self.ef_db_helper.reset_aborted_and_error_processor_states()
        self.ef_db_helper.delete_processors(list(termination_processors))
        self.ef_db_helper.set_eventflow_status(EventFlow.Status.STARTED)
        for processor_name in error_processor_names:
            if processor_name in termination_processors:
                continue
            self.call_next_processor(processor_name)

    def __init__(self, *, eventflow_id: str, root_args: typing.Dict|None, initial: bool = False):
        self.id = str(eventflow_id)
        self.ef_db_helper = EventFlowDbHelper(eventflow_id)
        if root_args is None:
            #TODO - Ideally init should not have root arguments param and should always be fetched from db
            self.root_args = self.ef_db_helper.eventflow_root_args
        else:
            self.root_args = root_args
        self.dag = Orchestrator.get_dag_from_eventflow_type(self.ef_db_helper.eventflow_type)
        
        self.provider_to_dependents_dict = defaultdict(list)
        
        for name, values in self.dag["processors"].items():
            for provider_name in values["depends_on"]:
                self.provider_to_dependents_dict[provider_name].append(name)
        
        self.log_debug(f"Provider to dependents dict for tree {self.id} - {self.provider_to_dependents_dict}")
        
        if initial:
            root_processors = [k for k, v in self.dag["processors"].items() if len(v["depends_on"]) == 0]
            self.log_debug(f"Initial processors being called - {root_processors}")
            
            for processor in root_processors:
                self.call_next_processor(processor)

    def get_all_providers(self,processor_name:str):
        return self.dag["processors"][processor_name]["depends_on"]

    @staticmethod
    def get_eventflow_status_from_termination_cause(termination_cause: TerminationCause):
        return TERMINATION_CAUSE_EVENTFLOW_STATUS_MAP[termination_cause]

    def abort_eventflow(self, termination_cause = TerminationCause.PROCESSOR_ERROR):
        self.log_info(f"Aborting event_flow, caused by: {termination_cause.name}")

        status = self.get_eventflow_status_from_termination_cause(termination_cause)
        
        self.ef_db_helper.set_eventflow_status(status)
        
        self.ef_db_helper.mark_pending_processor_aborted()

        termination_processor = self.dag["termination_processor"].keys()
        Orchestrator.initialise_eventflow_processors(self.id, termination_processor)

        self.log_info(f"Calling termination handler processors, processor: {termination_processor}")
        for processor in termination_processor:
            self.call_next_processor(processor)


    def on_processor_complete(self, *, processor_name: str, result_dict: typing.Dict, error_stacktrace = None):
        if error_stacktrace is None:
            self.ef_db_helper.mark_processor_complete(processor_name=processor_name, result_dict=result_dict)
        else:
            self.ef_db_helper.mark_processor_complete_with_error(processor_name=processor_name, 
                                                                 result_dict=result_dict,
                                                                 error_stacktrace=error_stacktrace)
        
        if not self.ef_db_helper.is_eventflow_terminated:
            for depending_processor in self.provider_to_dependents_dict[processor_name]:
                if self.check_if_providers_are_done(processor_name=depending_processor):
                    self.call_next_processor(depending_processor)
        else:
            self.log_info(f"Not calling dependent processor for {processor_name} since this event_flow has been terminated")

    def check_if_providers_are_done(self, *, processor_name: str):
        providers = self.dag["processors"][processor_name]["depends_on"]
        return self.ef_db_helper.are_given_processors_done(processor_names=providers)

    def get_assembled_results(self, *, processor_names: typing.List[str])->typing.Dict:
        results_to_be_sent = {}
        
        processor_states = self.ef_db_helper.get_processor_states(processor_names=processor_names)
            
        for processor, state in processor_states.items():
            results_to_be_sent[processor] = state.result
        
        return results_to_be_sent

    def call_next_processor(self, processor_name: str):

        if processor_name in self.dag["processors"]:
            providers = self.dag["processors"][processor_name]["depends_on"]
        elif processor_name in self.dag["termination_processor"]:
            providers = []
        else:
            raise KeyError(f"Error, {processor_name} is not present in the dag")

        assembled_results = {}
        if providers:
            assembled_results = self.get_assembled_results(processor_names=providers)
        
        self.log_debug(f"Calling processor - {processor_name} with inputs of - {list(assembled_results.keys())}")

        self.ef_db_helper.mark_processor_inprogress(processor_name)
        queue_name = PROCESSOR_QUEUE_MAPPING.get(processor_name,"default")
        app.send_task("evaluation.tasks.call_event_processor",kwargs={"processor_name": processor_name,"eventflow_id":self.id,
                                                 "root_arguments":self.root_args,
                                                 "inputs": assembled_results}, queue=queue_name)

    def submit_result(self, *, processor_name: str, result_dict: typing.Dict, error_stacktrace=None):
        if processor_name not in self.dag["processors"] and processor_name not in self.dag["termination_processor"]:
            raise ValueError(
                f"{processor_name} is not present in the tree-{self.id}. Keys present - {list(self.dag['processors'].keys())}")
        
        self.on_processor_complete(processor_name=processor_name, result_dict=result_dict, 
                                   error_stacktrace=error_stacktrace)

    def submit_retriable_error(self, *, processor_name: str, stacktrace: str):
        self.ef_db_helper.mark_processor_retriable_error(processor_name=processor_name, stacktrace=stacktrace)

    def submit_error(self, *, processor_name: str, stacktrace: str, abort_flow=False):
        self.ef_db_helper.mark_processor_error(processor_name=processor_name, stacktrace=stacktrace)

        if abort_flow:
            self.abort_eventflow()