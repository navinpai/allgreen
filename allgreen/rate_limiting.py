"""
Rate limiting functionality for expensive health checks.

Supports patterns like:
- "2 times per day"
- "4 times per hour"
- "1 time per minute"
"""

import pickle
import re
import threading
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_CACHE_DIR = Path.home() / ".allgreen" / "rate_limits"


class RateLimitConfig:
    """Configuration for a rate-limited check."""

    def __init__(self, run_pattern: str):
        self.pattern = run_pattern
        self.count, self.period = self._parse_pattern(run_pattern)

    def _parse_pattern(self, pattern: str) -> tuple[int, str]:
        """Parse patterns like '2 times per day' into (2, 'day')."""
        # Normalize the pattern
        pattern = pattern.lower().strip()

        # Match patterns like "2 times per day", "4 times per hour", etc.
        match = re.match(r"(\d+)\s+times?\s+per\s+(day|hour|minute)", pattern)
        if not match:
            raise ValueError(f"Invalid rate limit pattern: {pattern}")

        count = int(match.group(1))
        period = match.group(2)

        return count, period

    def get_period_duration(self) -> timedelta:
        """Get the duration of one period."""
        if self.period == "day":
            return timedelta(days=1)
        elif self.period == "hour":
            return timedelta(hours=1)
        elif self.period == "minute":
            return timedelta(minutes=1)
        else:
            raise ValueError(f"Unsupported period: {self.period}")

    def get_period_start(self, now: datetime | None = None) -> datetime:
        """Get the start of the current period."""
        if now is None:
            now = datetime.now()

        if self.period == "day":
            # Start of day
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif self.period == "hour":
            # Start of hour
            return now.replace(minute=0, second=0, microsecond=0)
        elif self.period == "minute":
            # Start of minute
            return now.replace(second=0, microsecond=0)
        else:
            raise ValueError(f"Unsupported period: {self.period}")


class RateLimitTracker:
    """Thread-safe rate limit tracking with persistent storage."""

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _get_cache_file(self, check_id: str) -> Path:
        """Get the cache file path for a specific check."""
        # Use check description as ID, but sanitize for filesystem
        safe_id = re.sub(r'[^\w\-_.]', '_', check_id)
        return self.cache_dir / f"{safe_id}.pkl"

    def _load_state(self, check_id: str) -> dict:
        """Load the rate limit state from disk."""
        cache_file = self._get_cache_file(check_id)
        if not cache_file.exists():
            return {"count": 0, "period_start": None, "last_result": None}

        try:
            with open(cache_file, "rb") as f:
                return pickle.load(f)
        except (OSError, pickle.PickleError):
            # If cache is corrupted, start fresh
            return {"count": 0, "period_start": None, "last_result": None}

    def _save_state(self, check_id: str, state: dict) -> None:
        """Save the rate limit state to disk."""
        cache_file = self._get_cache_file(check_id)
        try:
            with open(cache_file, "wb") as f:
                pickle.dump(state, f)
        except OSError:
            # If we can't save to cache, continue without persistence
            pass

    def should_run_check(
        self, check_id: str, config: RateLimitConfig, now: datetime | None = None
    ) -> tuple[bool, str | None, dict | None]:
        """
        Check if a rate-limited check should run.

        Returns:
            (should_run, skip_reason, cached_result)
        """
        if now is None:
            now = datetime.now()

        with self._lock:
            state = self._load_state(check_id)

            period_start = config.get_period_start(now)
            current_period_start = state.get("period_start")

            # If we're in a new period, reset the counter
            if (
                current_period_start is None
                or period_start > current_period_start
            ):
                state = {
                    "count": 0,
                    "period_start": period_start,
                    "last_result": state.get("last_result"),
                }

            # Check if we've exceeded the rate limit
            if state["count"] >= config.count:
                # Calculate when the next period starts
                next_period = period_start + config.get_period_duration()
                remaining_time = next_period - now

                if remaining_time.total_seconds() > 0:
                    # Format remaining time
                    if remaining_time.days > 0:
                        time_str = f"{remaining_time.days}d {remaining_time.seconds // 3600}h"
                    elif remaining_time.seconds > 3600:
                        time_str = f"{remaining_time.seconds // 3600}h {(remaining_time.seconds % 3600) // 60}m"
                    else:
                        time_str = f"{remaining_time.seconds // 60}m"

                    skip_reason = (
                        f"Rate limited: {state['count']}/{config.count} runs used this {config.period}. "
                        f"Next run in {time_str}"
                    )
                    return False, skip_reason, state.get("last_result")

            # Should run - increment counter
            state["count"] += 1
            self._save_state(check_id, state)

            return True, None, None

    def record_result(
        self, check_id: str, result: dict, now: datetime | None = None
    ) -> None:
        """Record the result of a rate-limited check."""
        with self._lock:
            state = self._load_state(check_id)
            state["last_result"] = result
            self._save_state(check_id, state)

    def get_remaining_runs(
        self, check_id: str, config: RateLimitConfig, now: datetime | None = None
    ) -> tuple[int, datetime]:
        """Get the number of remaining runs and when the limit resets."""
        if now is None:
            now = datetime.now()

        with self._lock:
            state = self._load_state(check_id)
            period_start = config.get_period_start(now)

            # If we're in a new period, all runs are available
            if (
                state.get("period_start") is None
                or period_start > state.get("period_start")
            ):
                remaining = config.count
            else:
                remaining = max(0, config.count - state.get("count", 0))

            next_reset = period_start + config.get_period_duration()
            return remaining, next_reset


# Global rate limit tracker instance
_rate_tracker = RateLimitTracker()


def get_rate_tracker() -> RateLimitTracker:
    """Get the global rate limit tracker instance."""
    return _rate_tracker


def set_rate_tracker_cache_dir(cache_dir: Path) -> None:
    """Set the cache directory for rate limiting data."""
    global _rate_tracker
    _rate_tracker = RateLimitTracker(cache_dir)
