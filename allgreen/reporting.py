"""Shared result aggregation and serialization used by all integrations."""

from datetime import datetime
from typing import Any

from .core import Check, CheckResult, CheckStatus


def calculate_stats(results: list[tuple[Check, CheckResult]]) -> dict[str, int]:
    """Calculate statistics from check results.

    "passed"/"failed"/"skipped"/"error" are raw per-status counts;
    "failing" is the combined failed + error count for display purposes.
    """
    stats = {
        "total": len(results),
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "error": 0,
    }

    for _, result in results:
        if result.status == CheckStatus.PASSED:
            stats["passed"] += 1
        elif result.status == CheckStatus.FAILED:
            stats["failed"] += 1
        elif result.status == CheckStatus.SKIPPED:
            stats["skipped"] += 1
        elif result.status == CheckStatus.ERROR:
            stats["error"] += 1

    stats["failing"] = stats["failed"] + stats["error"]

    return stats


def get_overall_status(stats: dict[str, int]) -> str:
    """Determine overall health status."""
    if stats["failing"] > 0:
        return "failed"
    elif stats["total"] == stats["skipped"]:
        return "no_checks"
    elif stats["passed"] > 0:
        return "passed"
    else:
        return "unknown"


def format_json_response(
    results: list[tuple[Check, CheckResult]],
    stats: dict[str, int],
    overall_status: str,
    app_name: str,
    environment: str | None,
    include_tracebacks: bool = False,
) -> dict[str, Any]:
    """Format results for JSON response.

    Tracebacks are omitted unless explicitly requested, so unexpected
    exceptions don't leak internals on a public endpoint.
    """
    json_results = []
    for check, result in results:
        json_results.append(
            {
                "name": check.name,
                "description": check.description,
                "status": result.status.value,
                "message": result.message,
                "error": result.error,
                "duration_ms": result.duration_ms,
                "skip_reason": result.skip_reason,
                "traceback": result.traceback if include_tracebacks else None,
            }
        )

    return {
        "status": overall_status,
        "stats": stats,
        "environment": environment,
        "app_name": app_name,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "checks": json_results,
    }
