from allgreen.core import Check, CheckResult, CheckStatus
from allgreen.metrics import (
    PROMETHEUS_CONTENT_TYPE,
    _escape_label_value,
    render_prometheus_metrics,
)


def _check(description: str) -> Check:
    return Check(description, lambda: None)


def test_content_type_constant():
    assert PROMETHEUS_CONTENT_TYPE == "text/plain; version=0.0.4; charset=utf-8"


def test_all_passing():
    results = [
        (_check("Check A"), CheckResult(CheckStatus.PASSED, duration_ms=12.5)),
        (_check("Check B"), CheckResult(CheckStatus.PASSED, duration_ms=3.0)),
    ]

    output = render_prometheus_metrics(results)

    assert "allgreen_up 1" in output
    assert 'allgreen_checks{status="passed"} 2' in output
    assert 'allgreen_checks{status="failed"} 0' in output
    assert 'allgreen_check_status{check="Check A"} 1' in output
    assert 'allgreen_check_status{check="Check B"} 1' in output
    assert 'allgreen_check_duration_seconds{check="Check A"} 0.012500' in output
    assert output.endswith("\n")


def test_failure_sets_up_to_zero():
    results = [
        (_check("Good"), CheckResult(CheckStatus.PASSED)),
        (_check("Bad"), CheckResult(CheckStatus.FAILED, message="nope")),
    ]

    output = render_prometheus_metrics(results)

    assert "allgreen_up 0" in output
    assert 'allgreen_checks{status="passed"} 1' in output
    assert 'allgreen_checks{status="failed"} 1' in output
    assert 'allgreen_check_status{check="Bad"} 0' in output


def test_error_counted_separately_from_failed():
    results = [
        (_check("Broken"), CheckResult(CheckStatus.ERROR, error="boom")),
    ]

    output = render_prometheus_metrics(results)

    assert "allgreen_up 0" in output
    assert 'allgreen_checks{status="failed"} 0' in output
    assert 'allgreen_checks{status="error"} 1' in output
    assert 'allgreen_check_status{check="Broken"} 0' in output


def test_skipped_checks_have_no_status_metric():
    results = [
        (_check("Skipped"), CheckResult(CheckStatus.SKIPPED, skip_reason="prod only")),
    ]

    output = render_prometheus_metrics(results)

    assert 'allgreen_checks{status="skipped"} 1' in output
    assert "allgreen_check_status" not in output
    assert "allgreen_check_duration_seconds" not in output


def test_label_escaping():
    assert _escape_label_value('has "quotes"') == 'has \\"quotes\\"'
    assert _escape_label_value("back\\slash") == "back\\\\slash"
    assert _escape_label_value("new\nline") == "new\\nline"

    results = [
        (_check('Says "hello"'), CheckResult(CheckStatus.PASSED)),
    ]
    output = render_prometheus_metrics(results)
    assert 'allgreen_check_status{check="Says \\"hello\\""} 1' in output


def test_help_and_type_lines():
    results = [(_check("A"), CheckResult(CheckStatus.PASSED, duration_ms=1.0))]

    output = render_prometheus_metrics(results)

    assert "# HELP allgreen_up" in output
    assert "# TYPE allgreen_up gauge" in output
    assert "# TYPE allgreen_checks gauge" in output
    assert "# TYPE allgreen_check_status gauge" in output
    assert "# TYPE allgreen_check_duration_seconds gauge" in output
