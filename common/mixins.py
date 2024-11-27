
class BaseLoggerMixin:

    @property
    def _logger(self):
        raise NotImplementedError

    def get_formatted_msg(self, msg: str) -> str:
        return msg
    
    def log_debug(self, msg: str, *args, **kwargs):
        self._logger.debug(self.get_formatted_msg(msg), *args, **kwargs)

    def log_info(self, msg: str, *args, **kwargs):
        self._logger.info(self.get_formatted_msg(msg), *args, **kwargs)

    def log_warn(self, msg: str, *args, **kwargs):
        self._logger.warn(self.get_formatted_msg(msg), *args, **kwargs)

    def log_error(self, msg: str, *args, **kwargs):
        self._logger.error(self.get_formatted_msg(msg), *args, **kwargs)

    def log_exception(self, msg: str, *args, **kwargs):
        self._logger.exception(self.get_formatted_msg(msg), *args, **kwargs)
    