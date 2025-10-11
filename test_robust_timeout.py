#!/usr/bin/env python3
"""Test robust timeout enforcement with blocking operations."""

import asyncio
import time
from allgreen import check, get_registry, CheckTimeoutError
from allgreen.core import execute_with_robust_timeout, execute_with_async_timeout


def blocking_sleep(seconds: float):
    """A truly blocking operation that can't be interrupted by signals."""
    time.sleep(seconds)


def test_robust_sync_timeout():
    """Test that robust timeout can interrupt blocking operations."""
    print("🔄 Testing robust sync timeout...")
    
    # Test successful execution under timeout
    try:
        result = execute_with_robust_timeout(lambda: blocking_sleep(0.1), 1.0)
        print("✅ Short operation completed within timeout")
    except CheckTimeoutError:
        print("❌ Short operation unexpectedly timed out")
        return False
    
    # Test timeout enforcement 
    start_time = time.time()
    try:
        execute_with_robust_timeout(lambda: blocking_sleep(2.0), 0.5)
        print("❌ Long operation should have timed out")
        return False
    except CheckTimeoutError as e:
        duration = time.time() - start_time
        print(f"✅ Long operation correctly timed out after {duration:.2f}s")
        # Should timeout close to 0.5 seconds, not wait for the full 2 seconds
        if duration < 1.0:  # Much less than the 2-second sleep
            print("✅ Timeout enforcement is robust (interrupted blocking operation)")
            return True
        else:
            print("❌ Timeout was not robust (waited for full sleep)")
            return False


async def test_robust_async_timeout():
    """Test that async timeout works in event loop context."""
    print("🔄 Testing robust async timeout...")
    
    # Test successful execution
    try:
        await execute_with_async_timeout(lambda: blocking_sleep(0.1), 1.0)
        print("✅ Short async operation completed")
    except CheckTimeoutError:
        print("❌ Short async operation unexpectedly timed out")
        return False
        
    # Test timeout enforcement
    start_time = time.time()
    try:
        await execute_with_async_timeout(lambda: blocking_sleep(2.0), 0.5)
        print("❌ Long async operation should have timed out")
        return False
    except CheckTimeoutError:
        duration = time.time() - start_time
        print(f"✅ Long async operation correctly timed out after {duration:.2f}s")
        return duration < 1.0  # Should be much faster than 2 seconds


def test_check_with_robust_timeout():
    """Test that check decorator uses robust timeout."""
    print("🔄 Testing check with robust timeout...")
    
    registry = get_registry()
    registry.clear()
    
    @check("Blocking operation test", timeout=1)
    def blocking_check():
        blocking_sleep(2.0)  # This should timeout
    
    start_time = time.time()
    results = registry.run_all()
    duration = time.time() - start_time
    
    check_obj, result = results[0]
    print(f"Check status: {result.status.value}")
    print(f"Check message: {result.message}")
    print(f"Execution time: {duration:.2f}s")
    
    # Should timeout and not wait for full 2 seconds
    if result.status.value == "error" and "timeout" in result.message.lower():
        if duration < 1.5:  # Much less than 2 seconds
            print("✅ Check-level robust timeout working!")
            return True
        else:
            print("❌ Check timeout was not robust")
            return False
    else:
        print("❌ Check should have timed out")
        return False


async def test_async_check_registry():
    """Test async check registry with robust timeout."""
    print("🔄 Testing async check registry...")
    
    registry = get_registry()
    registry.clear()
    
    @check("Async blocking test", timeout=0.5)
    def async_blocking_check():
        blocking_sleep(1.5)  # Should timeout quickly
    
    start_time = time.time()
    results = await registry.run_all_async()
    duration = time.time() - start_time
    
    check_obj, result = results[0]
    print(f"Async check status: {result.status.value}")
    print(f"Async execution time: {duration:.2f}s")
    
    # Should timeout robustly
    success = (
        result.status.value == "error" and 
        "timeout" in result.message.lower() and
        duration < 1.0
    )
    
    if success:
        print("✅ Async check registry with robust timeout working!")
    else:
        print("❌ Async check timeout not working properly")
    
    return success


async def main():
    """Run all timeout tests."""
    print("🚀 Testing Robust Timeout Enforcement\n")
    
    tests = [
        ("Sync Timeout", test_robust_sync_timeout()),
        ("Async Timeout", await test_robust_async_timeout()),
        ("Check Integration", test_check_with_robust_timeout()),
        ("Async Registry", await test_async_check_registry())
    ]
    
    passed = 0
    for test_name, result in tests:
        if result:
            passed += 1
        print()
    
    print(f"📊 Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All robust timeout tests passed!")
        print("💪 Blocking operations can now be reliably interrupted!")
    else:
        print("❌ Some timeout tests failed")
    
    return passed == len(tests)


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)