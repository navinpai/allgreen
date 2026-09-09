"""Tests for concurrent check execution in run_all / run_all_async."""

import asyncio
import threading
import time

from allgreen import CheckStatus, check, get_registry, make_sure


def test_run_all_executes_checks_concurrently():
    """A barrier only releases if all checks run at the same time."""
    registry = get_registry()
    registry.clear()

    barrier = threading.Barrier(4)

    def make_check(index: int) -> None:
        @check(f"Barrier check {index}")
        def barrier_check():
            # Times out (BrokenBarrierError -> ERROR) if execution is sequential
            barrier.wait(timeout=2)

    for i in range(4):
        make_check(i)

    results = registry.run_all()
    assert len(results) == 4
    assert all(result.passed for _, result in results)


def test_run_all_preserves_registration_order():
    registry = get_registry()
    registry.clear()

    def make_check(index: int) -> None:
        @check(f"Ordered check {index}")
        def ordered_check():
            # Reverse-staggered sleeps so completion order differs from
            # registration order
            time.sleep((3 - index) * 0.05)
            make_sure(True)

    for i in range(4):
        make_check(i)

    results = registry.run_all()
    descriptions = [check_obj.description for check_obj, _ in results]
    assert descriptions == [f"Ordered check {i}" for i in range(4)]


def test_run_all_timeout_does_not_block_other_checks():
    """A timed-out check is reported promptly, not after it finishes."""
    registry = get_registry()
    registry.clear()

    @check("Slow check", timeout=0.3)
    def slow_check():
        time.sleep(5)

    @check("Fast check")
    def fast_check():
        make_sure(True)

    start = time.time()
    results = registry.run_all()
    elapsed = time.time() - start

    assert elapsed < 2, f"run_all blocked for {elapsed:.1f}s on a timed-out check"
    statuses = {check_obj.description: result for check_obj, result in results}
    assert statuses["Slow check"].status == CheckStatus.ERROR
    assert "timed out" in statuses["Slow check"].error
    assert statuses["Fast check"].passed


def test_run_all_mixed_outcomes():
    registry = get_registry()
    registry.clear()

    @check("Parallel passing")
    def passing():
        make_sure(True)

    @check("Parallel failing")
    def failing():
        make_sure(False, "expected failure")

    @check("Parallel erroring")
    def erroring():
        raise ValueError("boom")

    @check("Parallel skipped", only_in="production")
    def skipped():
        make_sure(True)

    results = {c.description: r for c, r in registry.run_all()}
    assert results["Parallel passing"].status == CheckStatus.PASSED
    assert results["Parallel failing"].status == CheckStatus.FAILED
    assert results["Parallel erroring"].status == CheckStatus.ERROR
    assert results["Parallel skipped"].status == CheckStatus.SKIPPED


def test_run_all_respects_max_workers():
    registry = get_registry()
    registry.clear()

    active = 0
    peak = 0
    lock = threading.Lock()

    def make_check(index: int) -> None:
        @check(f"Worker check {index}")
        def worker_check():
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            time.sleep(0.05)
            with lock:
                active -= 1

    for i in range(6):
        make_check(i)

    results = registry.run_all(max_workers=2)
    assert all(result.passed for _, result in results)
    assert peak <= 2


def test_run_all_async_executes_checks_concurrently():
    registry = get_registry()
    registry.clear()

    started = []

    async def main():
        release = asyncio.Event()

        def make_check(index: int) -> None:
            @check(f"Async barrier check {index}")
            async def async_barrier_check():
                started.append(index)
                if len(started) == 3:
                    release.set()
                # Times out if the checks don't all start concurrently
                await asyncio.wait_for(release.wait(), timeout=2)

        for i in range(3):
            make_check(i)

        return await registry.run_all_async()

    results = asyncio.run(main())
    assert len(results) == 3
    assert all(result.passed for _, result in results)


def test_run_all_async_preserves_order_with_mixed_checks():
    registry = get_registry()
    registry.clear()

    @check("Mixed async slow")
    async def async_slow():
        await asyncio.sleep(0.1)
        make_sure(True)

    @check("Mixed sync fast")
    def sync_fast():
        make_sure(True)

    @check("Mixed async failing")
    async def async_failing():
        make_sure(False, "async failure")

    results = asyncio.run(registry.run_all_async())
    descriptions = [check_obj.description for check_obj, _ in results]
    assert descriptions == [
        "Mixed async slow",
        "Mixed sync fast",
        "Mixed async failing",
    ]
    assert results[0][1].passed
    assert results[1][1].passed
    assert results[2][1].status == CheckStatus.FAILED
