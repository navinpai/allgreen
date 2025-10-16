#!/usr/bin/env python3
"""
Core-only allgreen example (no web framework dependencies).

This shows how to use allgreen for health checks without any web framework.
Perfect for CLI tools, background services, or custom integrations.

Install:
    pip install allgreen  # No extra dependencies needed!

Run:
    python examples/core_only_example.py
"""

import json

from allgreen import check, expect, get_registry, load_config, make_sure


# Define some health checks directly in code
@check("System has enough memory")
def memory_check():
    import psutil
    try:
        memory = psutil.virtual_memory()
        expect(memory.percent).to_be_less_than(90)
    except ImportError:
        make_sure(True, "psutil not available - assuming memory is OK")

@check("Basic math still works")
def math_check():
    expect(2 + 2).to_eq(4)
    expect(10).to_be_greater_than(5)

@check("Environment variables accessible")
def env_check():
    import os
    make_sure('PATH' in os.environ, "PATH should be set")

def run_health_checks():
    """Run all health checks and return results."""
    # Load additional checks from config file (if available)
    try:
        load_config("examples/allgreen_config.py", "development")
    except Exception:
        print("💡 No config file found, using inline checks only")

    # Get all registered checks
    registry = get_registry()
    results = registry.run_all("development")

    return results

def print_results_table(results):
    """Print results in a nice table format."""
    print("\n" + "="*80)
    print(f"{'STATUS':<10} {'DURATION':<10} {'DESCRIPTION':<30} {'MESSAGE'}")
    print("="*80)

    passed = failed = skipped = 0

    for check_obj, result in results:
        # Status icon and counts
        if result.passed:
            status_icon = "✅ PASS"
            passed += 1
        elif result.failed:
            status_icon = "❌ FAIL"
            failed += 1
        elif result.skipped:
            status_icon = "⏭️ SKIP"
            skipped += 1
        else:
            status_icon = "⚠️ UNKN"

        # Duration
        duration = f"{result.duration_ms:.1f}ms" if result.duration_ms else "N/A"

        # Message
        message = ""
        if result.skip_reason:
            message = f"Skipped: {result.skip_reason}"
        elif result.message and not result.passed:
            message = result.message[:40] + "..." if len(result.message) > 40 else result.message

        print(f"{status_icon:<10} {duration:<10} {check_obj.description[:30]:<30} {message}")

    print("="*80)
    print(f"Summary: {passed} passed, {failed} failed, {skipped} skipped")
    return passed, failed, skipped

def export_json_results(results, filename="health_check_results.json"):
    """Export results to JSON file."""
    json_results = []
    for check_obj, result in results:
        json_results.append({
            "description": check_obj.description,
            "status": result.status.value,
            "passed": result.passed,
            "message": result.message,
            "error": result.error,
            "duration_ms": result.duration_ms,
            "skip_reason": result.skip_reason,
        })

    output = {
        "timestamp": "2023-01-01 12:00:00",  # Would use real timestamp
        "environment": "development",
        "total_checks": len(results),
        "results": json_results
    }

    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"📄 Results exported to {filename}")

if __name__ == '__main__':
    print("🚀 Allgreen Core-Only Example")
    print("💡 No web framework dependencies required!")
    print("\nRunning health checks...")

    # Run the checks
    results = run_health_checks()

    # Display results in table format
    passed, failed, skipped = print_results_table(results)

    # Export to JSON
    export_json_results(results)

    # Exit with appropriate code for CI/CD
    exit_code = 0 if failed == 0 else 1
    print(f"\n🎯 Exit code: {exit_code} ({'success' if exit_code == 0 else 'failure'})")

    exit(exit_code)
