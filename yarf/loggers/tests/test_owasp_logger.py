import logging

from yarf.loggers.owasp_logger import get_owasp_logger


class TestPrettyJSONFormatter:
    def test_format_valid_json(self):
        formatter = get_owasp_logger().handlers[0].formatter
        record = logging.LogRecord(
            name="owasp",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg='{"key": "value", "number": 123}',
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert '"key": "value",\n  "number": 123' in formatted

    def test_format_invalid_json(self):
        formatter = get_owasp_logger().handlers[0].formatter
        record = logging.LogRecord(
            name="owasp",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="This is not JSON",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert "This is not JSON" in formatted


class TestOwaspLogger:
    def test_logger_creation(self):
        logger = get_owasp_logger()

        assert logger.name == "owasp"
        assert not logger.propagate
        assert any(
            isinstance(handler, logging.FileHandler)
            for handler in logger.handlers
        )
