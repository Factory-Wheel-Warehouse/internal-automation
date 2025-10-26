import json
import logging
from types import SimpleNamespace

from src.util.logging.JsonLogFormatter import JsonLogFormatter
from src.util.logging import set_up_logging, _setup_json_handler
from src.util.logging.sns_exception_logging_decorator import log_exceptions


def test_json_log_formatter_includes_exception():
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=(ValueError, ValueError("boom"), None),
    )
    payload = json.loads(formatter.format(record))
    assert payload["message"] == "hello"
    assert "exception" in payload


def test_log_exceptions_decorator_posts_to_sns(mocker):
    post_sns = mocker.patch("src.util.logging.sns_exception_logging_decorator.aws.post_exception_to_sns")

    @log_exceptions
    def unstable():
        raise RuntimeError("fail")

    unstable()
    post_sns.assert_called_once()


def test_set_up_logging_configures_handlers(mocker):
    stream_handler = logging.StreamHandler()
    cloud_handler = logging.StreamHandler()
    mocker.patch(
        "src.util.logging.watchtower.CloudWatchLogHandler",
        return_value=cloud_handler,
    )
    boto_client = mocker.Mock()
    mocker.patch(
        "src.util.logging.boto3_session.client",
        return_value=boto_client,
    )
    mocker.patch("src.util.logging._setup_json_handler", side_effect=lambda h: h)
    mocker.patch("src.util.logging.logging.basicConfig")
    mocker.patch("src.util.logging.logging.StreamHandler", return_value=stream_handler)

    set_up_logging()

    logging.basicConfig.assert_called_once()


def test_setup_json_handler_assigns_formatter(mocker):
    handler = mocker.Mock()
    result = _setup_json_handler(handler)
    handler.setFormatter.assert_called_once()
    assert result is handler
