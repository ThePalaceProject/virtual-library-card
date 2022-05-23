import logging
from logging.handlers import QueueHandler
from queue import Empty, Queue

from django.test import TestCase

from tests.base import BaseUnitTest
from virtual_library_card.logging import Logging, LoggingMixin


class TestLogging(LoggingMixin, BaseUnitTest, TestCase):
    def setup_method(self, request):
        self._q = Queue()
        logging.getLogger(Logging.DEFAULT_LOG_NAME).addHandler(QueueHandler(self._q))
        return super().setup_method(request)

    def test_log(self):
        # Default mode is warning
        assert self.log._logger.level == logging.NOTSET
        assert self.log._logger.root.level == logging.WARNING

        self.log.warning("msg")
        record = self._q.get(False)
        assert record.msg == "msg"
        assert record.name == Logging.DEFAULT_LOG_NAME

        # Debug should not get logged (self.debug is overwritten)
        self.log.debug("msg")
        self.assertRaises(Empty, self._q.get, False)

        self.log.error("error")
        record: logging.LogRecord = self._q.get(False)
        assert record.msg == "error"
        assert record.levelno == logging.ERROR

        self.log.critical("critical")
        record: logging.LogRecord = self._q.get(False)
        assert record.msg == "critical"
        assert record.levelno == logging.CRITICAL

        self.log._logger.setLevel(logging.DEBUG)
        self.log.debug("debug")
        record: logging.LogRecord = self._q.get(False)
        assert record.msg == "debug"
        assert record.levelno == logging.DEBUG
