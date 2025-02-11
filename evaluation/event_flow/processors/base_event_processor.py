import abc
import logging
import traceback
import typing

from evaluation.models import EventFlow
import openai

from common.mixins import BaseLoggerMixin
from evaluation.event_flow.processors.expections import CriticalProcessorException, ProcessorException

logger = logging.getLogger(__name__)


class EventProcessor(abc.ABC, BaseLoggerMixin):

    _logger = logger
    _fallback_result = {}

    def get_fallback_result(self):
        raise NotImplementedError

    def __init__(self, eventflow_id: str, inputs: typing.Dict, root_arguments: typing.Dict):
        self.inputs = inputs
        self.root_arguments = root_arguments
        self.eventflow_id = eventflow_id
        self.eventflow = EventFlow.objects.get(id=eventflow_id)
        self.log_debug(f"Init function of processor called - {self.__class__.__name__}")

    def get_formatted_msg(self, msg):
        return f"ProcessorLog:[{self.eventflow_id}]:[{self.__class__.__name__}]:{msg}"

    def execute(self):
        self.log_info(f"Execution starting.")
        try:
            results = self._execute()
        except CriticalProcessorException as cpe:
            self.log_exception(f"Processor {self.__class__.__name__} failed with error - {cpe.original_error_name}")
            self.log_info(f"Processor-DONE -{self.__class__.__name__}-ERROR")
            
            stacktrace = cpe.original_error_stack_trace
            self.handle_critical_exception(stacktrace=stacktrace)
        # Catch this Exception if Fallback Results are supported
        # except ProcessorException as pe:
        #     self.log_exception(f"Processor failed with error - {pe.original_error_name}")
        #     self.log_info(f"Processor-DONE -{self.__class__.__name__}-ERROR")
        #
        #     stacktrace = pe.original_error_stack_trace
        #     self.submit_result(results=self.get_fallback_result(), error_stacktrace=stacktrace)
        except openai.RateLimitError as e:
            self.log_info(f"Processor got a retriable error - {e}")
            stacktrace = traceback.format_exc()
            self.submit_error(stacktrace,retriable=True)
            raise e
        except Exception as e:
            self.log_exception(f"Processor failed with error - {e}")
            self.log_info(f"Processor-DONE -{self.__class__.__name__}-ERROR")
            
            stacktrace = traceback.format_exc()
            self.submit_error(stacktrace, retriable=True)
        else:
            self.log_info(f"Processor-DONE -{self.__class__.__name__}")
            self.submit_result(results)

    @abc.abstractmethod
    def _execute(self) -> typing.Dict:
        pass

    def submit_error(self, stacktrace, retriable=False):
        from evaluation.event_flow.core.orchestrator import Orchestrator
        if retriable:
            Orchestrator(eventflow=self.eventflow, root_args=self.root_arguments).submit_retriable_error(
                processor_name=self.__class__.__name__,
                stacktrace=stacktrace)
        else:
            Orchestrator(eventflow=self.eventflow, root_args=self.root_arguments).submit_error(
            processor_name=self.__class__.__name__,
            stacktrace=stacktrace, abort_flow=True)

    def submit_result(self, results: typing.Dict, error_stacktrace=None):
        from evaluation.event_flow.core.orchestrator import Orchestrator
        Orchestrator(eventflow=self.eventflow, root_args=self.root_arguments).submit_result(
            processor_name=self.__class__.__name__,
            result_dict=results, error_stacktrace=error_stacktrace)
    
    def handle_critical_exception(self, stacktrace):
        from evaluation.event_flow.core.orchestrator import Orchestrator
        Orchestrator(eventflow=self.eventflow, root_args=self.root_arguments).submit_error(
            processor_name=self.__class__.__name__,
            stacktrace=stacktrace,
            abort_flow=True)