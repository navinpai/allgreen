from allgreen.core import Check, CheckResult, CheckStatus
from allgreen.reporting import (
    calculate_stats,
    format_json_response,
    get_overall_status,
)


def _check(description: str) -> Check:
    return Check(description, lambda: None)


def _results():
    return [
        (_check("Passed"), CheckResult(CheckStatus.PASSED)),
        (_check("Failed"), CheckResult(CheckStatus.FAILED, message="nope")),
        (
            _check("Errored"),
            CheckResult(
                CheckStatus.ERROR,
                error="ValueError: boom",
                traceback="Traceback (most recent call last):\n...",
            ),
        ),
        (_check("Skipped"), CheckResult(CheckStatus.SKIPPED, skip_reason="prod only")),
    ]


def test_stats_raw_counts_not_double_counted():
    stats = calculate_stats(_results())

    assert stats["total"] == 4
    assert stats["passed"] == 1
    assert stats["failed"] == 1
    assert stats["error"] == 1
    assert stats["skipped"] == 1
    assert stats["failing"] == 2


def test_overall_status_failed_on_error_only():
    results = [(_check("Errored"), CheckResult(CheckStatus.ERROR, error="boom"))]
    stats = calculate_stats(results)

    assert stats["failed"] == 0
    assert get_overall_status(stats) == "failed"


def test_json_response_hides_tracebacks_by_default():
    results = _results()
    stats = calculate_stats(results)

    data = format_json_response(results, stats, "failed", "App", "production")

    errored = next(c for c in data["checks"] if c["description"] == "Errored")
    assert errored["error"] == "ValueError: boom"
    assert errored["traceback"] is None


def test_json_response_includes_tracebacks_when_enabled():
    results = _results()
    stats = calculate_stats(results)

    data = format_json_response(
        results, stats, "failed", "App", "development", include_tracebacks=True
    )

    errored = next(c for c in data["checks"] if c["description"] == "Errored")
    assert "Traceback (most recent call last)" in errored["traceback"]
