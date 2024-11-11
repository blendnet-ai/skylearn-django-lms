
from evaluation.event_flow.processors.base_event_processor import EventProcessor
from evaluation.models import UserAttemptResponseEvaluation


class AbortHandler(EventProcessor):

    def initialize(self):
        self.evaluation_id = self.root_arguments.get("evaluation_id")
        
    def _execute(self):
        self.initialize()
        eval_object = UserAttemptResponseEvaluation.objects.get(id=self.evaluation_id)
        eval_object.summary = {"text": "Evaluation was aborted"}
        eval_object.status = UserAttemptResponseEvaluation.Status.ERROR
        eval_object.save()
        return {}