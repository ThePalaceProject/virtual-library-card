import logging


class Logging:
    DEFAULT_LOG_NAME = "djangoapp"

    def __init__(self, log_name=DEFAULT_LOG_NAME) -> None:
        self.log_name = log_name
        self._logger = logging.getLogger(log_name)

    def _log(self, msg, *args, level=logging.DEBUG):
        self._logger.log(level, msg, *args)

    def debug(self, msg, *args):
        self._log(msg, *args, level=logging.DEBUG)

    def warning(self, msg, *args):
        self._log(msg, *args, level=logging.WARNING)

    def error(self, msg, *args):
        self._log(msg, *args, level=logging.ERROR)

    def critical(self, msg, *args):
        self._log(msg, *args, level=logging.CRITICAL)

    def exception(self, msg, *args):
        self._logger.exception(msg, *args)

    @classmethod
    def log(cls, msg, *args, log_name=DEFAULT_LOG_NAME, level=logging.DEBUG):
        """For static/class invocations"""
        logging.getLogger(log_name).log(level, msg, *args)


class LoggingMixin:
    LOG_NAME = Logging.DEFAULT_LOG_NAME

    def __init__(self, *args, **kwargs):
        self.log = Logging(log_name=self.LOG_NAME)
        return super().__init__(*args, **kwargs)


# Default logging mechanism
log = Logging()
