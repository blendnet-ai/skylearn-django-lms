from evaluation.event_flow.processors.base_event_processor import EventProcessor


class TestingProcessor(EventProcessor):

    def initialize(self):
        self.output=self.root_arguments.get("output")

    def _execute(self):
        self.initialize()
        return {"output":self.output}