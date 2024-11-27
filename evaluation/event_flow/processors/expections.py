import typing
import traceback


class BaseProcessorException(Exception):
    
    def __init__(self, *, message: str, original_error: Exception, extra_info: typing.Dict):
        super().__init__(message)
        self.original_error_name = original_error.__class__.__name__
        self.original_error_stack_trace = ''.join(traceback.format_tb(original_error.__traceback__))


class ProcessorException(BaseProcessorException):
    pass


class CriticalProcessorException(BaseProcessorException):
    pass


class ProcessorEvaluationException(Exception):
    pass