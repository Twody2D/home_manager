import json
import logging

from home_manager.core.logging import JsonFormatter


def _make_record(**extra: object) -> logging.LogRecord:
    record = logging.LogRecord(
        name="home_manager.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="something happened",
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_json_formatter_produces_valid_json_with_expected_fields() -> None:
    record = _make_record(request_id="abc-123", status_code=200)

    line = JsonFormatter().format(record)
    payload = json.loads(line)

    assert payload["level"] == "INFO"
    assert payload["logger"] == "home_manager.test"
    assert payload["message"] == "something happened"
    assert payload["request_id"] == "abc-123"
    assert payload["status_code"] == 200


def test_json_formatter_includes_exception_traceback() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record = logging.LogRecord(
            name="home_manager.test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="unhandled_exception",
            args=(),
            exc_info=sys.exc_info(),
        )

    payload = json.loads(JsonFormatter().format(record))

    assert "ValueError: boom" in payload["exception"]
