import logging
import typing
from django.db import transaction
from django.utils import timezone

from evaluation.models import EventFlow, EventFlowProcessorState


logger = logging.getLogger(__name__)


class EventFlowDbHelper:

    def __init__(self, event_flow_id: str) -> None:
        self.eventflow: EventFlow = EventFlow.objects.get(id=event_flow_id)

    @property
    def eventflow_type(self):
        return self.eventflow.type

    @property
    def eventflow_status(self):
        return self.eventflow.status

    @property
    def is_eventflow_terminated(self):
        return self.eventflow.status in EventFlow.TERMINATION_STATES

    @property
    def eventflow_root_args(self):
        return self.eventflow.root_arguments

    def set_eventflow_status(self, status):
        self.eventflow.status = status
        self.eventflow.save()

    def get_processor_names_by_status(self, status:EventFlowProcessorState.Status):
        return self.eventflow.processors.filter(status=status).values_list("processor_name", flat=True)

    def mark_pending_processor_aborted(self):
        pending_processors = self.eventflow.processors.filter(status=EventFlowProcessorState.Status.PENDING)
        pending_processors.update(status=EventFlowProcessorState.Status.ABORTED)

    def are_given_processors_done(self, processor_names: list[str]):
        return self.eventflow.check_if_given_processors_are_done(processor_names=processor_names)

    def get_processor_states(self, processor_names: typing.List[str]) -> typing.Dict:
        # Here' distinct is needed for in_bulk to work, 
        # it would have no effect since for a given even_flow processor_name is anyway unique
        processor_states = self.eventflow.processors.distinct(
            'processor_name'
            ).in_bulk(processor_names, field_name='processor_name')

        return processor_states

    @staticmethod
    def update_processor_termination_time(event_flow_state: EventFlowProcessorState):
        event_flow_state.end_time = timezone.now()
        if event_flow_state.start_time is not None:
            event_flow_state.run_duration = event_flow_state.end_time - event_flow_state.start_time
        else:
            logger.warn(
                f"EventFlowProcessorState, start time wasn't set \
                efstate_id: {event_flow_state.pk}, processor_name {event_flow_state.processor_name}")

    @staticmethod
    def update_processor_start_time(event_flow_state: EventFlowProcessorState):
        event_flow_state.start_time = timezone.now()

    def mark_processor_inprogress(self, processor_name: str):
        ef_state = self.eventflow.processors.get(
            processor_name=processor_name
            )
        ef_state.status = EventFlowProcessorState.Status.IN_PROGRESS

        self.update_processor_start_time(ef_state)

        ef_state.save()

    def mark_processor_error(self, processor_name: str, stacktrace: str):
        with transaction.atomic():
            ef_state = EventFlowProcessorState.objects.select_for_update().get(event_flow=self.eventflow,
                                                                                processor_name=processor_name)
            ef_state.error = stacktrace
            ef_state.status = EventFlowProcessorState.Status.ERROR

            self.update_processor_termination_time(ef_state)

            ef_state.save()

    def mark_processor_retriable_error(self, processor_name: str, stacktrace: str):
        with transaction.atomic():
            ef_state = EventFlowProcessorState.objects.select_for_update().get(event_flow=self.eventflow,
                                                                                processor_name=processor_name)
            ef_state.retriable_error = stacktrace
            ef_state.status = EventFlowProcessorState.Status.RETRIABLE_ERROR

            self.update_processor_termination_time(ef_state)

            ef_state.save()

    def mark_processor_complete(self, *, processor_name: str, result_dict: typing.Dict):
        with transaction.atomic():
            ef_state = EventFlowProcessorState.objects.select_for_update().get(event_flow=self.eventflow,
                                                                                processor_name=processor_name)
            ef_state.result = result_dict
            ef_state.status = EventFlowProcessorState.Status.COMPLETED

            self.update_processor_termination_time(ef_state)

            ef_state.save()
        #Calling save method to trigger check for completion
        self.eventflow.save()

    def mark_processor_complete_with_error(self, *, processor_name: str, result_dict: typing.Dict, error_stacktrace):
        with transaction.atomic():
            ef_state = EventFlowProcessorState.objects.select_for_update().get(event_flow=self.eventflow,
                                                                                processor_name=processor_name)
            ef_state.result = result_dict
            ef_state.error = error_stacktrace
            ef_state.status = EventFlowProcessorState.Status.COMPLETED_WITH_ERROR

            self.update_processor_termination_time(ef_state)

            ef_state.save()

    def delete_processors(self, processor_names:typing.List[str]):
        self.eventflow.processors.filter(processor_name__in=processor_names).delete()

    def reset_aborted_and_error_processor_states(self):
        self.eventflow.processors.filter(status__in=[EventFlowProcessorState.Status.PENDING,
                                                     EventFlowProcessorState.Status.COMPLETED_WITH_ERROR,
                                                     EventFlowProcessorState.Status.ABORTED]).update(result={},
                                         status=EventFlowProcessorState.Status.PENDING,
                                         run_duration=None,
                                         start_time=None,
                                         end_time=None
                                         )

    def reset_all_processors_state(self, termination_processors:typing.List[str]=None):
        self.set_eventflow_status(EventFlow.Status.STARTED)
        self.delete_processors(list(termination_processors))
        self.eventflow.processors.update(result={},
                                         status=EventFlowProcessorState.Status.PENDING,
                                         run_duration=None,
                                         start_time=None,
                                         end_time=None
                                         )