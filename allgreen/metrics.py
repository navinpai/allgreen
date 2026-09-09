"""
Prometheus text exposition format rendering for check results.

No dependency on prometheus_client - the format is generated directly per
https://prometheus.io/docs/instrumenting/exposition_formats/

Exposed metrics:
- allgreen_up: 1 if all checks pass, 0 otherwise
- allgreen_checks{status}: number of checks per status (passed/failed/skipped/error)
- allgreen_check_status{check}: 1 for a passing check, 0 for failing/error
- allgreen_check_duration_seconds{check}: execution time of each check
"""

from .core import Check, CheckResult, CheckStatus
from .reporting import calculate_stats, get_overall_status

PROMETHEUS_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


def _escape_label_value(value: str) -> str:
    """Escape a label value per the Prometheus exposition format spec."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def render_prometheus_metrics(results: list[tuple[Check, CheckResult]]) -> str:
    """Render check results in Prometheus text exposition format."""
    stats = calculate_stats(results)
    overall_status = get_overall_status(stats)

    status_counts = {
        "passed": stats["passed"],
        "failed": stats["failed"] - stats["error"],  # Undo the failed+error merge
        "skipped": stats["skipped"],
        "error": stats["error"],
    }

    lines = [
        "# HELP allgreen_up Overall health status (1 = all checks passing)",
        "# TYPE allgreen_up gauge",
        f"allgreen_up {1 if overall_status == 'passed' else 0}",
        "# HELP allgreen_checks Number of health checks by status",
        "# TYPE allgreen_checks gauge",
    ]

    for status, count in status_counts.items():
        lines.append(f'allgreen_checks{{status="{status}"}} {count}')

    status_lines = []
    duration_lines = []
    for check, result in results:
        label = _escape_label_value(check.description)

        if result.status == CheckStatus.PASSED:
            status_lines.append(f'allgreen_check_status{{check="{label}"}} 1')
        elif result.status in (CheckStatus.FAILED, CheckStatus.ERROR):
            status_lines.append(f'allgreen_check_status{{check="{label}"}} 0')
        # Skipped checks have no pass/fail status and are omitted

        if result.duration_ms is not None:
            duration_seconds = result.duration_ms / 1000
            duration_lines.append(
                f'allgreen_check_duration_seconds{{check="{label}"}} '
                f"{duration_seconds:.6f}"
            )

    if status_lines:
        lines.append(
            "# HELP allgreen_check_status Health check result (1 = passed, 0 = failed)"
        )
        lines.append("# TYPE allgreen_check_status gauge")
        lines.extend(status_lines)

    if duration_lines:
        lines.append(
            "# HELP allgreen_check_duration_seconds Health check execution time"
        )
        lines.append("# TYPE allgreen_check_duration_seconds gauge")
        lines.extend(duration_lines)

    return "\n".join(lines) + "\n"
