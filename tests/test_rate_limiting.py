import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from allgreen.rate_limiting import RateLimitConfig, RateLimitTracker


class TestRateLimitConfig:
    def test_parse_valid_patterns(self):
        # Test various valid patterns
        patterns = [
            ("2 times per day", 2, "day"),
            ("4 times per hour", 4, "hour"),
            ("1 time per minute", 1, "minute"),
            ("10 times per day", 10, "day"),
        ]

        for pattern, expected_count, expected_period in patterns:
            config = RateLimitConfig(pattern)
            assert config.count == expected_count
            assert config.period == expected_period

    def test_parse_invalid_patterns(self):
        invalid_patterns = [
            "invalid pattern",
            "2 times per week",  # week not supported
            "abc times per day",
            "2 per day",  # missing "times"
            "",
        ]

        for pattern in invalid_patterns:
            with pytest.raises(ValueError):
                RateLimitConfig(pattern)

    def test_period_durations(self):
        day_config = RateLimitConfig("1 time per day")
        assert day_config.get_period_duration() == timedelta(days=1)

        hour_config = RateLimitConfig("1 time per hour")
        assert hour_config.get_period_duration() == timedelta(hours=1)

        minute_config = RateLimitConfig("1 time per minute")
        assert minute_config.get_period_duration() == timedelta(minutes=1)

    def test_period_start_calculation(self):
        test_time = datetime(2023, 10, 15, 14, 30, 45)  # Oct 15, 2:30:45 PM

        day_config = RateLimitConfig("1 time per day")
        expected_day_start = datetime(2023, 10, 15, 0, 0, 0)
        assert day_config.get_period_start(test_time) == expected_day_start

        hour_config = RateLimitConfig("1 time per hour")
        expected_hour_start = datetime(2023, 10, 15, 14, 0, 0)
        assert hour_config.get_period_start(test_time) == expected_hour_start

        minute_config = RateLimitConfig("1 time per minute")
        expected_minute_start = datetime(2023, 10, 15, 14, 30, 0)
        assert minute_config.get_period_start(test_time) == expected_minute_start


class TestRateLimitTracker:
    def test_basic_rate_limiting(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = RateLimitTracker(Path(tmpdir))
            config = RateLimitConfig("2 times per hour")
            check_id = "test_check"

            # First run should be allowed
            should_run, skip_reason, cached_result = tracker.should_run_check(check_id, config)
            assert should_run is True
            assert skip_reason is None
            assert cached_result is None

            # Second run should be allowed
            should_run, skip_reason, cached_result = tracker.should_run_check(check_id, config)
            assert should_run is True
            assert skip_reason is None

            # Third run should be rate limited
            should_run, skip_reason, cached_result = tracker.should_run_check(check_id, config)
            assert should_run is False
            assert "Rate limited" in skip_reason
            assert "2/2 runs used" in skip_reason

    def test_period_reset(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = RateLimitTracker(Path(tmpdir))
            config = RateLimitConfig("1 time per minute")
            check_id = "test_check"

            now = datetime(2023, 10, 15, 14, 30, 0)  # Minute start

            # Use up the limit
            should_run, _, _ = tracker.should_run_check(check_id, config, now)
            assert should_run is True

            # Should be rate limited in same minute
            should_run, skip_reason, _ = tracker.should_run_check(check_id, config, now)
            assert should_run is False
            assert "Rate limited" in skip_reason

            # Move to next minute - should be allowed again
            next_minute = now + timedelta(minutes=1)
            should_run, _, _ = tracker.should_run_check(check_id, config, next_minute)
            assert should_run is True

    def test_result_caching(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = RateLimitTracker(Path(tmpdir))
            config = RateLimitConfig("1 time per hour")
            check_id = "test_check"

            # Use up the rate limit first
            should_run, _, _ = tracker.should_run_check(check_id, config)
            assert should_run is True

            # Record a result after the first run
            result = {
                "status": "passed",
                "message": "Test passed",
                "duration_ms": 100.0
            }
            tracker.record_result(check_id, result)

            # Should get cached result when rate limited
            should_run, skip_reason, cached_result = tracker.should_run_check(check_id, config)
            assert should_run is False
            assert cached_result == result

    def test_remaining_runs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = RateLimitTracker(Path(tmpdir))
            config = RateLimitConfig("3 times per hour")
            check_id = "test_check"

            now = datetime(2023, 10, 15, 14, 0, 0)

            # Initially should have 3 runs remaining
            remaining, reset_time = tracker.get_remaining_runs(check_id, config, now)
            assert remaining == 3
            assert reset_time == datetime(2023, 10, 15, 15, 0, 0)  # Next hour

            # Use one run
            tracker.should_run_check(check_id, config, now)
            remaining, _ = tracker.get_remaining_runs(check_id, config, now)
            assert remaining == 2

            # Use another run
            tracker.should_run_check(check_id, config, now)
            remaining, _ = tracker.get_remaining_runs(check_id, config, now)
            assert remaining == 1

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            config = RateLimitConfig("2 times per hour")
            check_id = "persistent_test"

            # Create tracker and use up limit
            tracker1 = RateLimitTracker(cache_dir)
            tracker1.should_run_check(check_id, config)
            tracker1.should_run_check(check_id, config)

            # Create new tracker - should remember previous state
            tracker2 = RateLimitTracker(cache_dir)
            should_run, skip_reason, _ = tracker2.should_run_check(check_id, config)
            assert should_run is False
            assert "Rate limited" in skip_reason

    def test_corrupted_cache_handling(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = RateLimitTracker(Path(tmpdir))
            config = RateLimitConfig("1 time per hour")
            check_id = "corrupted_test"

            # Create a corrupted cache file
            cache_file = tracker._get_cache_file(check_id)
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text("invalid pickle data")

            # Should handle corruption gracefully
            should_run, _, _ = tracker.should_run_check(check_id, config)
            assert should_run is True  # Should start fresh
