#!/usr/bin/env python3
"""Test cached result semantics for rate limiting."""

import tempfile
import time
from pathlib import Path

from allgreen import check, get_registry
from allgreen.rate_limiting import RateLimitTracker


def test_cached_result_semantics():
    """Test that cached results preserve original status."""
    
    # Use a temporary cache directory
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir)
        
        # Create a tracker with the temp cache
        tracker = RateLimitTracker(cache_dir)
        
        # Clear registry and set up test check
        registry = get_registry()
        registry.clear()
        
        # Add a check that will pass initially
        @check("Test cached result", run="1 time per hour")
        def passing_check():
            return True  # This will pass
        
        print("🔄 Testing cached result semantics...")
        
        # First run - should execute and pass
        results = registry.run_all("test_env")
        assert len(results) == 1
        
        check_obj, result1 = results[0]
        print(f"1st run: {result1.status.value} - {result1.message}")
        
        # Should pass
        assert result1.status.value == "passed"
        assert result1.message == "Check passed"
        assert "cached" not in result1.message.lower()
        
        # Second run immediately - should return cached result
        results = registry.run_all("test_env") 
        assert len(results) == 1
        
        check_obj, result2 = results[0]
        print(f"2nd run: {result2.status.value} - {result2.message}")
        
        # Should still be "passed" status with cached indicator
        assert result2.status.value == "passed"  # NOT "skipped"!
        assert "cached result" in result2.message.lower()
        assert result2.skip_reason is None  # Not actually skipped
        
        # Test with different environment (should get separate cache)
        results = registry.run_all("different_env")
        check_obj, result3 = results[0]
        print(f"Different env: {result3.status.value} - {result3.message}")
        
        # Should execute again since different environment
        assert result3.status.value == "passed" 
        assert "cached" not in result3.message.lower()
        
        print("✅ Cached result semantics work correctly!")
        print("✅ Environment-based cache namespacing works!")


def test_failed_cached_result():
    """Test that failed cached results preserve failure status."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir)
        tracker = RateLimitTracker(cache_dir)
        
        registry = get_registry()
        registry.clear()
        
        @check("Test cached failure", run="1 time per hour")  
        def failing_check():
            from allgreen import make_sure
            make_sure(False, "This check always fails")
        
        print("🔄 Testing failed cached result...")
        
        # First run - should fail
        results = registry.run_all("test_env")
        check_obj, result1 = results[0]
        print(f"1st run: {result1.status.value} - {result1.message}")
        assert result1.status.value == "failed"
        
        # Second run - should return cached failure 
        results = registry.run_all("test_env")
        check_obj, result2 = results[0]
        print(f"2nd run: {result2.status.value} - {result2.message}")
        
        # Should still be "failed" status (not "skipped")
        assert result2.status.value == "failed"  
        assert "cached result" in result2.message.lower()
        
        print("✅ Failed cached results preserve failure status!")


if __name__ == "__main__":
    test_cached_result_semantics()
    print()
    test_failed_cached_result()
    print("\n🎉 All cached result tests passed!")