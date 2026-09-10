# Advanced allgreen_config.py demonstrating rate limiting, timeouts,
# async checks, expectation matchers, and parallel execution behavior

import asyncio
import random
import shutil
import time


@check("Basic health check")
def basic_check():
    make_sure(True, "System is operational")


@check("Quick timeout test", timeout=2)
def timeout_test():
    # This should complete within 2 seconds
    time.sleep(0.5)
    make_sure(True, "Quick operation completed")


@check("Long operation with timeout", timeout=5)
def long_operation():
    # This operation gets 5 seconds to complete
    time.sleep(1)  # Simulate some work
    expect(2 + 2).to_eq(4)


@check("Sub-second timeout", timeout=0.5)
def float_timeout_check():
    # Timeouts can be floats for tight latency budgets
    time.sleep(0.1)
    make_sure(True, "Fast enough")


@check("Timeout disabled", timeout=0)
def no_timeout_check():
    # timeout=0 disables enforcement entirely - use for checks that
    # legitimately take a long time and must not be interrupted
    make_sure(True, "Runs without a deadline")


# Async checks are awaited natively in ASGI apps (FastAPI) and run
# transparently on an event loop everywhere else
@check("Async upstream check", timeout=5)
async def async_upstream_check():
    await asyncio.sleep(0.1)  # Simulate an async HTTP call
    make_sure(True, "Upstream is reachable")


# Expectation matchers
@check("Membership matchers")
def membership_check():
    enabled_features = ["healthcheck", "metrics", "rate_limiting"]
    expect(enabled_features).to_contain("healthcheck")
    expect(enabled_features).not_to_contain("debug_mode")
    # Works on strings, dicts (keys), and sets too
    expect("allgreen ok").to_contain("ok")


@check("Range matcher")
def range_check():
    cpu_usage = random.randint(10, 80)
    expect(cpu_usage).to_be_between(0, 95)  # inclusive bounds


@check("Presence matchers")
def presence_check():
    shutdown_reason = None
    config_value = "postgres://localhost/app"
    expect(shutdown_reason).to_be_none()
    expect(config_value).not_to_be_none()
    # Note: not_to_be_none checks identity, so falsy values like 0 or "" pass


@check("Expensive API call", run="2 times per hour", timeout=30)
def expensive_api_check():
    # This expensive check only runs 2 times per hour
    # and has a 30 second timeout
    time.sleep(0.1)  # Simulate API call
    make_sure(True, "API is responding")


@check("Daily database backup check", run="1 time per day")
def daily_backup_check():
    # This only runs once per day - perfect for expensive operations
    make_sure(True, "Daily backup completed successfully")


@check("Hourly metrics collection", run="4 times per hour", timeout=15)
def metrics_collection():
    # Collect metrics up to 4 times per hour with 15 second timeout
    cpu_usage = random.randint(10, 80)
    expect(cpu_usage).to_be_less_than(90)


@check(
    "Production-only expensive check",
    only_in="production",
    run="1 time per hour",
    timeout=60,
)
def production_expensive_check():
    # Only runs in production, once per hour, with 1 minute timeout
    make_sure(ENVIRONMENT == "production", "Should only run in production")


# Checks run concurrently (thread pool for sync, asyncio.gather for async),
# so these three sleeps cost ~0.2s total, not 0.6s. Results are still
# reported in registration order. Shared state must be thread-safe.
@check("Parallel check A")
def parallel_a():
    time.sleep(0.2)
    make_sure(True)


@check("Parallel check B")
def parallel_b():
    time.sleep(0.2)
    make_sure(True)


@check("Parallel check C")
def parallel_c():
    time.sleep(0.2)
    make_sure(True)


# Regular checks (no rate limiting)
@check("Memory usage check")
def memory_check():
    try:
        import psutil

        memory = psutil.virtual_memory()
        expect(memory.percent).to_be_less_than(85)
    except ImportError:
        make_sure(True, "psutil not available - skipping memory check")


@check("Disk space check")
def disk_check():
    try:
        total, used, free = shutil.disk_usage("/")
        usage_percent = (used / total) * 100
        expect(usage_percent).to_be_less_than(90)
    except Exception as e:
        make_sure(False, f"Could not check disk usage: {e}")


# This will timeout deliberately to test timeout handling
@check("Timeout demonstration", timeout=2)
def timeout_demo():
    time.sleep(5)  # This will timeout after 2 seconds
    make_sure(True, "Should not reach this point")
