import time

import pytest

from allgreen import (
    CheckStatus,
    check,
    get_registry,
    make_sure,
)


class TestTimeoutFunctionality:
    def test_check_with_timeout_passes(self):
        """Test that checks completing within timeout work normally."""
        registry = get_registry()
        registry.clear()

        @check("Quick check with timeout", timeout=2)
        def quick_check():
            time.sleep(0.1)  # Well under timeout
            make_sure(True)

        check_obj = registry.get_checks()[0]
        result = check_obj.execute()

        assert result.status == CheckStatus.PASSED
        assert result.duration_ms is not None
        assert result.duration_ms > 100  # At least 100ms due to sleep

    def test_check_timeout_error(self):
        """Test that checks exceeding timeout are handled properly."""
        registry = get_registry()
        registry.clear()

        @check("Slow check with timeout", timeout=1)
        def slow_check():
            time.sleep(2)  # Exceeds 1 second timeout
            make_sure(True, "Should not reach this")

        check_obj = registry.get_checks()[0]
        result = check_obj.execute()

        assert result.status == CheckStatus.ERROR
        assert "timed out after 1 seconds" in result.error
        assert result.message == "Check timed out"
        assert result.duration_ms is not None

    def test_default_timeout(self):
        """Test that checks use default 10 second timeout."""
        registry = get_registry()
        registry.clear()

        @check("Check with default timeout")
        def default_timeout_check():
            # This should complete well within 10 seconds
            make_sure(True)

        check_obj = registry.get_checks()[0]
        assert check_obj.timeout == 10

    def test_custom_timeout(self):
        """Test that custom timeouts are properly set."""
        registry = get_registry()
        registry.clear()

        @check("Check with custom timeout", timeout=30)
        def custom_timeout_check():
            make_sure(True)

        check_obj = registry.get_checks()[0]
        assert check_obj.timeout == 30

    def test_timeout_with_rate_limiting(self):
        """Test timeout works with rate-limited checks."""
        registry = get_registry()
        registry.clear()

        @check("Rate limited timeout check", timeout=1, run="10 times per hour")
        def rate_limited_timeout_check():
            time.sleep(2)  # Will timeout
            make_sure(True)

        check_obj = registry.get_checks()[0]

        # First few runs should timeout normally (we have plenty of quota)
        result = check_obj.execute()
        assert result.status == CheckStatus.ERROR
        assert "timed out" in result.error

        # Verify rate limiting is configured
        assert check_obj.run == "10 times per hour"

    def test_timeout_with_assertion_error(self):
        """Test that assertion errors within timeout work properly."""
        registry = get_registry()
        registry.clear()

        @check("Failing check with timeout", timeout=5)
        def failing_check_with_timeout():
            time.sleep(0.1)  # Short delay, well under timeout
            make_sure(False, "This check should fail")

        check_obj = registry.get_checks()[0]
        result = check_obj.execute()

        assert result.status == CheckStatus.FAILED
        assert "This check should fail" in result.message
        assert result.duration_ms is not None
        assert result.duration_ms > 100  # Should include sleep time

    def test_timeout_with_exception(self):
        """Test that regular exceptions within timeout are handled."""
        registry = get_registry()
        registry.clear()

        @check("Exception check with timeout", timeout=5)
        def exception_check_with_timeout():
            time.sleep(0.1)
            raise ValueError("Something went wrong")

        check_obj = registry.get_checks()[0]
        result = check_obj.execute()

        assert result.status == CheckStatus.ERROR
        assert "ValueError: Something went wrong" in result.error
        assert "Something went wrong" in result.message  # Should have traceback

    @pytest.mark.skipif(
        not hasattr(time, 'sleep'),
        reason="Platform doesn't support sleep"
    )
    def test_very_short_timeout(self):
        """Test very short timeouts work correctly."""
        registry = get_registry()
        registry.clear()

        @check("Very short timeout", timeout=1)
        def very_short_timeout():
            time.sleep(1.5)  # Slightly over 1 second
            make_sure(True)

        check_obj = registry.get_checks()[0]
        start_time = time.time()
        result = check_obj.execute()
        end_time = time.time()

        # Should timeout quickly
        assert result.status == CheckStatus.ERROR
        assert "timed out" in result.error
        # Should complete in roughly the timeout period (plus some overhead)
        assert (end_time - start_time) < 2.0  # Should be close to 1 second

    def test_zero_timeout_handling(self):
        """Test that zero timeout is handled sensibly."""
        registry = get_registry()
        registry.clear()

        # Zero timeout should default to something reasonable
        @check("Zero timeout check", timeout=0)
        def zero_timeout_check():
            make_sure(True)

        check_obj = registry.get_checks()[0]
        # Zero timeout should be converted to default
        assert check_obj.timeout == 10  # Default timeout
