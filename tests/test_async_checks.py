import asyncio
import time

from allgreen.core import Check, CheckStatus, make_sure


def _make_check(func, **kwargs) -> Check:
    return Check(description="async test check", func=func, **kwargs)


def test_async_check_passes_in_sync_context():
    async def passing_check():
        await asyncio.sleep(0.01)
        make_sure(True)

    result = _make_check(passing_check).execute("test")
    assert result.status == CheckStatus.PASSED
    assert result.duration_ms is not None


def test_async_check_fails_in_sync_context():
    async def failing_check():
        make_sure(False, "Async failure message")

    result = _make_check(failing_check).execute("test")
    assert result.status == CheckStatus.FAILED
    assert "Async failure message" in result.message


def test_async_check_error_in_sync_context():
    async def error_check():
        raise RuntimeError("Boom")

    result = _make_check(error_check).execute("test")
    assert result.status == CheckStatus.ERROR
    assert "RuntimeError" in result.error


def test_async_check_timeout_in_sync_context():
    async def slow_check():
        await asyncio.sleep(3)

    start = time.time()
    result = _make_check(slow_check, timeout=1).execute("test")
    elapsed = time.time() - start

    assert result.status == CheckStatus.ERROR
    assert "timed out" in result.error
    assert elapsed < 2  # Cancelled at ~1s, not after the full 3s sleep


def test_async_check_passes_in_async_context():
    async def passing_check():
        await asyncio.sleep(0.01)
        make_sure(True)

    async def main():
        return await _make_check(passing_check).execute_async("test")

    result = asyncio.run(main())
    assert result.status == CheckStatus.PASSED


def test_async_check_timeout_in_async_context():
    async def slow_check():
        await asyncio.sleep(3)

    async def main():
        return await _make_check(slow_check, timeout=1).execute_async("test")

    start = time.time()
    result = asyncio.run(main())
    elapsed = time.time() - start

    assert result.status == CheckStatus.ERROR
    assert "timed out" in result.error
    assert elapsed < 2


def test_sync_check_still_works_in_async_context():
    def sync_check():
        make_sure(True)

    async def main():
        return await _make_check(sync_check).execute_async("test")

    result = asyncio.run(main())
    assert result.status == CheckStatus.PASSED


def test_async_check_via_sync_execute_inside_running_loop():
    """Sync execute() called while an event loop is running must not crash."""

    async def passing_check():
        await asyncio.sleep(0.01)
        make_sure(True)

    async def main():
        # Deliberately call the *sync* execute from async code
        return _make_check(passing_check).execute("test")

    result = asyncio.run(main())
    assert result.status == CheckStatus.PASSED
