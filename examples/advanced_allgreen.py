# Advanced allgreen.py configuration demonstrating rate limiting and timeouts

@check("Basic health check")
def basic_check():
    make_sure(True, "System is operational")


@check("Quick timeout test", timeout=2)
def timeout_test():
    # This should complete within 2 seconds
    import time
    time.sleep(0.5)
    make_sure(True, "Quick operation completed")


@check("Long operation with timeout", timeout=5)
def long_operation():
    # This operation gets 5 seconds to complete
    import time
    time.sleep(1)  # Simulate some work
    expect(2 + 2).to_eq(4)


@check("Expensive API call", run="2 times per hour", timeout=30)
def expensive_api_check():
    # This expensive check only runs 2 times per hour
    # and has a 30 second timeout
    import time
    time.sleep(0.1)  # Simulate API call
    make_sure(True, "API is responding")


@check("Daily database backup check", run="1 time per day")
def daily_backup_check():
    # This only runs once per day - perfect for expensive operations
    make_sure(True, "Daily backup completed successfully")


@check("Hourly metrics collection", run="4 times per hour", timeout=15)
def metrics_collection():
    # Collect metrics up to 4 times per hour with 15 second timeout
    import random
    # Simulate metrics collection
    cpu_usage = random.randint(10, 80)
    expect(cpu_usage).to_be_less_than(90)


@check("Production-only expensive check", only="production", run="1 time per hour", timeout=60)
def production_expensive_check():
    # Only runs in production, once per hour, with 1 minute timeout
    make_sure(ENVIRONMENT == "production", "Should only run in production")


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
    import shutil
    try:
        total, used, free = shutil.disk_usage("/")
        usage_percent = (used / total) * 100
        expect(usage_percent).to_be_less_than(90)
    except Exception as e:
        make_sure(False, f"Could not check disk usage: {e}")


# This will timeout deliberately to test timeout handling
@check("Timeout demonstration", timeout=2)
def timeout_demo():
    import time
    time.sleep(5)  # This will timeout after 2 seconds
    make_sure(True, "Should not reach this point")
