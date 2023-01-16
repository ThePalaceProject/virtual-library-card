import logging

DEFAULT_LOG_NAME = "app"


class LoggingMixin:
    LOG_NAME = DEFAULT_LOG_NAME

    def __init__(self, *args, **kwargs):
        self.log = logging.getLogger(self.LOG_NAME)
        return super().__init__(*args, **kwargs)


# Default logging mechanism
log = logging.getLogger(DEFAULT_LOG_NAME)
