import signal
import threading
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, List, Optional, Union


class CheckStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class CheckResult:
    status: CheckStatus
    message: Optional[str] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    skip_reason: Optional[str] = None

    @property
    def passed(self) -> bool:
        return self.status == CheckStatus.PASSED

    @property
    def failed(self) -> bool:
        return self.status in (CheckStatus.FAILED, CheckStatus.ERROR)

    @property
    def skipped(self) -> bool:
        return self.status == CheckStatus.SKIPPED


class AllgreenError(Exception):
    pass


class CheckAssertionError(AllgreenError):
    pass


class CheckTimeoutError(AllgreenError):
    pass


@contextmanager
def timeout_context(seconds: int):
    """Context manager for timing out function execution."""
    if hasattr(signal, 'SIGALRM'):
        # Unix systems - use signals (more reliable)
        def timeout_handler(signum, frame):
            raise CheckTimeoutError(f"Check timed out after {seconds} seconds")

        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:
        # Windows/other systems - use threading (less reliable but works)
        timer_expired = threading.Event()

        def timeout_func():
            timer_expired.set()

        timer = threading.Timer(seconds, timeout_func)
        timer.start()

        try:
            yield
            if timer_expired.is_set():
                raise CheckTimeoutError(f"Check timed out after {seconds} seconds")
        finally:
            timer.cancel()


class Expectation:
    def __init__(self, actual: Any):
        self.actual = actual

    def to_eq(self, expected: Any) -> None:
        if self.actual != expected:
            raise CheckAssertionError(
                f"Expected {self.actual!r} to equal {expected!r}"
            )

    def to_be_greater_than(self, expected: Union[int, float]) -> None:
        if not (isinstance(self.actual, (int, float)) and self.actual > expected):
            raise CheckAssertionError(
                f"Expected {self.actual!r} to be greater than {expected!r}"
            )

    def to_be_less_than(self, expected: Union[int, float]) -> None:
        if not (isinstance(self.actual, (int, float)) and self.actual < expected):
            raise CheckAssertionError(
                f"Expected {self.actual!r} to be less than {expected!r}"
            )


def expect(actual: Any) -> Expectation:
    return Expectation(actual)


def make_sure(condition: Any, message: Optional[str] = None) -> None:
    if not condition:
        raise CheckAssertionError(message or f"Expected {condition!r} to be truthy")


class Check:
    def __init__(
        self,
        description: str,
        func: Callable[[], None],
        timeout: Optional[int] = None,
        only: Optional[Union[str, List[str]]] = None,
        except_env: Optional[Union[str, List[str]]] = None,
        if_condition: Optional[Union[bool, Callable[[], bool]]] = None,
        run: Optional[str] = None,
    ):
        self.description = description
        self.func = func
        self.timeout = timeout or 10  # Default 10 second timeout
        self.only = self._normalize_env_list(only)
        self.except_env = self._normalize_env_list(except_env)
        self.if_condition = if_condition
        self.run = run

    def _normalize_env_list(self, env: Optional[Union[str, List[str]]]) -> Optional[List[str]]:
        if env is None:
            return None
        if isinstance(env, str):
            return [env]
        return env

    def should_run(self, environment: str = "development") -> tuple[bool, Optional[str]]:
        # Check environment conditions
        if self.only and environment not in self.only:
            return False, f"Only runs in {', '.join(self.only)}, current: {environment}"

        if self.except_env and environment in self.except_env:
            return False, f"Skipped in {environment} environment"

        # Check if condition
        if self.if_condition is not None:
            if callable(self.if_condition):
                try:
                    if not self.if_condition():
                        return False, "Custom condition not met"
                except Exception as e:
                    return False, f"Custom condition failed: {e}"
            elif not self.if_condition:
                return False, "Custom condition is False"

        return True, None

    def execute(self, environment: str = "development") -> CheckResult:
        # Check basic conditions (environment, if_condition)
        should_run, skip_reason = self.should_run(environment)
        if not should_run:
            return CheckResult(
                status=CheckStatus.SKIPPED,
                skip_reason=skip_reason
            )

        # Check rate limiting if specified
        if self.run:
            should_run_rate, skip_reason_rate, cached_result = self._check_rate_limit()
            if not should_run_rate:
                # Return cached result if we have one, otherwise create skipped result
                if cached_result:
                    # For rate-limited checks, we return SKIPPED status but include cached info
                    return CheckResult(
                        status=CheckStatus.SKIPPED,
                        message=f"Cached result: {cached_result.get('message', 'N/A')}",
                        skip_reason=skip_reason_rate
                    )
                else:
                    return CheckResult(
                        status=CheckStatus.SKIPPED,
                        skip_reason=skip_reason_rate
                    )

        start_time = time.time()
        try:
            # Execute with timeout
            with timeout_context(self.timeout):
                self.func()

            duration_ms = (time.time() - start_time) * 1000
            result = CheckResult(
                status=CheckStatus.PASSED,
                message="Check passed",
                duration_ms=duration_ms
            )

            # Cache result for rate-limited checks
            if self.run:
                self._cache_result(result)

            return result

        except CheckTimeoutError as e:
            duration_ms = (time.time() - start_time) * 1000
            result = CheckResult(
                status=CheckStatus.ERROR,
                error=str(e),
                message="Check timed out",
                duration_ms=duration_ms
            )
            if self.run:
                self._cache_result(result)
            return result

        except CheckAssertionError as e:
            duration_ms = (time.time() - start_time) * 1000
            result = CheckResult(
                status=CheckStatus.FAILED,
                message=str(e),
                duration_ms=duration_ms
            )
            if self.run:
                self._cache_result(result)
            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = CheckResult(
                status=CheckStatus.ERROR,
                error=f"{type(e).__name__}: {e}",
                message=traceback.format_exc(),
                duration_ms=duration_ms
            )
            if self.run:
                self._cache_result(result)
            return result

    def _check_rate_limit(self) -> tuple[bool, Optional[str], Optional[dict]]:
        """Check if this rate-limited check should run."""
        if not self.run:
            return True, None, None

        # Import locally to avoid circular imports
        from .rate_limiting import RateLimitConfig, get_rate_tracker

        try:
            config = RateLimitConfig(self.run)
            tracker = get_rate_tracker()
            return tracker.should_run_check(self.description, config)
        except ValueError:
            # Invalid rate limit pattern - run the check but log error
            return True, None, None

    def _cache_result(self, result: CheckResult) -> None:
        """Cache the result of a rate-limited check."""
        if not self.run:
            return

        from .rate_limiting import get_rate_tracker

        # Convert CheckResult to dict for caching
        result_dict = {
            "status": result.status,
            "message": result.message,
            "error": result.error,
            "duration_ms": result.duration_ms,
        }

        tracker = get_rate_tracker()
        tracker.record_result(self.description, result_dict)


class CheckRegistry:
    def __init__(self):
        self._checks: List[Check] = []

    def register(self, check: Check) -> None:
        self._checks.append(check)

    def get_checks(self) -> List[Check]:
        return self._checks.copy()

    def clear(self) -> None:
        self._checks.clear()

    def run_all(self, environment: str = "development") -> List[tuple[Check, CheckResult]]:
        results = []
        for check in self._checks:
            result = check.execute(environment)
            results.append((check, result))
        return results


# Global registry
_registry = CheckRegistry()


def check(
    description: str,
    timeout: Optional[int] = None,
    only: Optional[Union[str, List[str]]] = None,
    except_env: Optional[Union[str, List[str]]] = None,
    if_condition: Optional[Union[bool, Callable[[], bool]]] = None,
    run: Optional[str] = None,
):
    def decorator(func: Callable[[], None]) -> Callable[[], None]:
        check_obj = Check(
            description=description,
            func=func,
            timeout=timeout,
            only=only,
            except_env=except_env,
            if_condition=if_condition,
            run=run,
        )
        _registry.register(check_obj)
        return func

    return decorator


def get_registry() -> CheckRegistry:
    return _registry
