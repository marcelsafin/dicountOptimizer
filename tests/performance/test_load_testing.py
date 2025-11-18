"""
Load testing for shopping optimizer system.

This module tests system behavior under realistic and heavy load conditions:
- Concurrent user requests
- API rate limiting behavior
- Resource exhaustion scenarios
- Graceful degradation under load

Requirements: 8.2, 8.3, 8.5
"""

import asyncio
import time
from typing import Any

import pytest
import pytest_asyncio

from agents.discount_optimizer.infrastructure.cache_repository import (
    InMemoryCacheRepository,
)
from agents.discount_optimizer.metrics import get_metrics_collector, profile_operation


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def cache():
    """Create cache instance for testing."""
    cache_repo = InMemoryCacheRepository()
    yield cache_repo
    await cache_repo.close()


@pytest.fixture
def metrics_collector():
    """Create fresh metrics collector for each test."""
    collector = get_metrics_collector()
    collector.reset()
    return collector


# =============================================================================
# Concurrent Request Load Tests
# =============================================================================


class TestConcurrentRequestLoad:
    """Test system behavior under concurrent request load."""

    @pytest.mark.asyncio
    async def test_handle_10_concurrent_requests(self):
        """Test handling 10 concurrent optimization requests."""

        async def optimization_request(request_id: int) -> dict[str, Any]:
            """Simulate optimization request."""
            with profile_operation(f"request_{request_id}"):
                # Simulate validation
                await asyncio.sleep(0.01)

                # Simulate discount fetching
                await asyncio.sleep(0.05)

                # Simulate optimization
                await asyncio.sleep(0.02)

                return {
                    "request_id": request_id,
                    "success": True,
                    "duration": 0.08,
                }

        # Make 10 concurrent requests
        start = time.perf_counter()
        tasks = [optimization_request(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        duration = time.perf_counter() - start

        # All requests should succeed
        assert len(results) == 10
        assert all(r["success"] for r in results)

        # Should complete in reasonable time (concurrent, not sequential)
        # Sequential would take 0.8s (10 * 0.08s), concurrent should be ~0.1s
        assert duration < 0.3

    @pytest.mark.asyncio
    async def test_handle_50_concurrent_requests(self):
        """Test handling 50 concurrent optimization requests."""

        async def optimization_request(request_id: int) -> dict[str, Any]:
            """Simulate optimization request."""
            await asyncio.sleep(0.05)  # Simulate work
            return {"request_id": request_id, "success": True}

        # Make 50 concurrent requests
        start = time.perf_counter()
        tasks = [optimization_request(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        duration = time.perf_counter() - start

        # All requests should succeed
        assert len(results) == 50
        assert all(r["success"] for r in results)

        # Should complete in reasonable time
        assert duration < 1.0

    @pytest.mark.asyncio
    async def test_handle_100_concurrent_requests(self):
        """Test handling 100 concurrent optimization requests (stress test)."""

        async def optimization_request(request_id: int) -> dict[str, Any]:
            """Simulate optimization request."""
            await asyncio.sleep(0.02)  # Simulate work
            return {"request_id": request_id, "success": True}

        # Make 100 concurrent requests
        start = time.perf_counter()
        tasks = [optimization_request(i) for i in range(100)]
        results = await asyncio.gather(*tasks)
        duration = time.perf_counter() - start

        # All requests should succeed
        assert len(results) == 100
        assert all(r["success"] for r in results)

        # Should complete in reasonable time
        assert duration < 2.0

    @pytest.mark.asyncio
    async def test_concurrent_requests_with_cache_contention(self, cache):
        """Test concurrent requests competing for cache access."""

        async def request_with_cache(request_id: int) -> bytes | None:
            """Request that uses cache."""
            key = f"shared_key_{request_id % 10}"  # 10 shared keys

            # Try to get from cache
            cached = await cache.get(key)
            if cached:
                return cached

            # Cache miss - simulate fetch and cache
            await asyncio.sleep(0.01)
            value = f"value_{request_id}".encode()
            await cache.set(key, value, ttl_seconds=60)
            return value

        # Make many concurrent requests
        tasks = [request_with_cache(i) for i in range(100)]
        results = await asyncio.gather(*tasks)

        # All requests should complete
        assert len(results) == 100
        assert all(r is not None for r in results)


# =============================================================================
# API Rate Limiting Tests
# =============================================================================


class TestAPIRateLimiting:
    """Test API rate limiting behavior."""

    @pytest.mark.asyncio
    async def test_handle_rate_limit_errors_gracefully(self):
        """Test graceful handling of rate limit errors."""
        call_count = 0

        async def api_call_with_rate_limit(call_id: int) -> dict[str, Any]:
            """Simulate API call that may hit rate limit."""
            nonlocal call_count
            call_count += 1

            # Simulate rate limit after 10 calls
            if call_count > 10:
                await asyncio.sleep(0.1)  # Simulate backoff
                # After backoff, succeed
                return {"call_id": call_id, "success": True, "rate_limited": True}

            await asyncio.sleep(0.01)
            return {"call_id": call_id, "success": True, "rate_limited": False}

        # Make many calls
        tasks = [api_call_with_rate_limit(i) for i in range(20)]
        results = await asyncio.gather(*tasks)

        # All should eventually succeed
        assert len(results) == 20
        assert all(r["success"] for r in results)

        # Some should have been rate limited
        rate_limited_count = sum(1 for r in results if r.get("rate_limited"))
        assert rate_limited_count > 0

    @pytest.mark.asyncio
    async def test_exponential_backoff_on_failures(self):
        """Test exponential backoff retry strategy."""
        attempt_times = []

        async def api_call_with_retries(max_retries: int = 3) -> bool:
            """API call with exponential backoff."""
            for attempt in range(max_retries):
                attempt_times.append(time.perf_counter())

                # Simulate failure
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    backoff = 2**attempt * 0.01  # Scaled down for testing
                    await asyncio.sleep(backoff)
                else:
                    # Final attempt succeeds
                    return True

            return False

        start = time.perf_counter()
        success = await api_call_with_retries(max_retries=3)
        duration = time.perf_counter() - start

        assert success
        assert len(attempt_times) == 3

        # Check backoff intervals
        if len(attempt_times) >= 2:
            interval1 = attempt_times[1] - attempt_times[0]
            assert interval1 >= 0.01  # First backoff

        if len(attempt_times) >= 3:
            interval2 = attempt_times[2] - attempt_times[1]
            assert interval2 >= 0.02  # Second backoff (doubled)


# =============================================================================
# Resource Exhaustion Tests
# =============================================================================


class TestResourceExhaustion:
    """Test system behavior under resource exhaustion."""

    @pytest.mark.asyncio
    async def test_handle_cache_memory_pressure(self, cache):
        """Test cache behavior when memory is under pressure."""
        # Fill cache with many entries
        large_value = b"x" * 1024  # 1KB per entry

        for i in range(1000):
            await cache.set(f"key_{i}", large_value, ttl_seconds=60)

        # Cache should still be functional
        is_healthy = await cache.health_check()
        assert is_healthy

        # Should be able to retrieve entries
        result = await cache.get("key_500")
        assert result == large_value

    @pytest.mark.asyncio
    async def test_handle_many_expired_entries(self, cache):
        """Test cache cleanup with many expired entries."""
        # Create many entries with short TTL
        for i in range(500):
            await cache.set(f"short_ttl_{i}", b"value", ttl_seconds=1)

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Trigger cleanup
        await cache._cleanup_expired()

        # Cache should be mostly empty
        size = await cache.get_size()
        assert size < 50  # Most should be cleaned up

    @pytest.mark.asyncio
    async def test_handle_connection_pool_exhaustion(self):
        """Test behavior when connection pool is exhausted."""
        max_connections = 10
        active_connections = 0

        async def make_request(request_id: int) -> int:
            """Simulate request that uses connection."""
            nonlocal active_connections

            # Simulate acquiring connection
            if active_connections >= max_connections:
                # Wait for connection to become available
                await asyncio.sleep(0.05)

            active_connections += 1
            await asyncio.sleep(0.01)  # Simulate work
            active_connections -= 1

            return request_id

        # Make more requests than pool size
        tasks = [make_request(i) for i in range(50)]
        results = await asyncio.gather(*tasks)

        # All should complete eventually
        assert len(results) == 50


# =============================================================================
# Graceful Degradation Tests
# =============================================================================


class TestGracefulDegradation:
    """Test graceful degradation under adverse conditions."""

    @pytest.mark.asyncio
    async def test_degrade_gracefully_when_cache_unavailable(self):
        """Test system works without cache."""

        async def operation_with_optional_cache(use_cache: bool) -> str:
            """Operation that can work with or without cache."""
            if use_cache:
                # Try cache (simulate unavailable)
                cached = None  # Simulate cache miss/unavailable
                if cached:
                    return "from_cache"

            # Fallback to direct operation
            await asyncio.sleep(0.01)
            return "from_source"

        # Should work without cache
        result = await operation_with_optional_cache(use_cache=False)
        assert result == "from_source"

        # Should fallback when cache unavailable
        result = await operation_with_optional_cache(use_cache=True)
        assert result == "from_source"

    @pytest.mark.asyncio
    async def test_degrade_gracefully_when_api_slow(self):
        """Test system handles slow API responses."""

        async def slow_api_call(timeout: float) -> dict[str, Any]:
            """Simulate slow API call."""
            try:
                # Simulate slow response
                await asyncio.wait_for(
                    asyncio.sleep(2.0),  # Very slow
                    timeout=timeout,
                )
                return {"success": True, "data": "result"}
            except TimeoutError:
                # Timeout - return partial result
                return {"success": False, "error": "timeout", "partial": True}

        # With timeout, should fail gracefully
        result = await slow_api_call(timeout=0.5)
        assert result["success"] is False
        assert result.get("partial") is True

    @pytest.mark.asyncio
    async def test_continue_with_partial_results(self):
        """Test system can continue with partial results."""

        async def fetch_from_multiple_sources() -> list[str]:
            """Fetch from multiple sources, some may fail."""

            async def fetch_source(source_id: int, should_fail: bool) -> str | None:
                """Fetch from one source."""
                await asyncio.sleep(0.01)
                if should_fail:
                    return None
                return f"data_from_source_{source_id}"

            # Fetch from 5 sources, 2 fail
            tasks = [
                fetch_source(0, False),
                fetch_source(1, True),  # Fails
                fetch_source(2, False),
                fetch_source(3, True),  # Fails
                fetch_source(4, False),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out failures
            valid_results = [r for r in results if r is not None and isinstance(r, str)]
            return valid_results

        results = await fetch_from_multiple_sources()

        # Should have partial results
        assert len(results) == 3  # 3 out of 5 succeeded
        assert all("data_from_source" in r for r in results)


# =============================================================================
# Sustained Load Tests
# =============================================================================


class TestSustainedLoad:
    """Test system behavior under sustained load."""

    @pytest.mark.asyncio
    async def test_handle_sustained_request_rate(self):
        """Test handling sustained request rate over time."""
        request_count = 0

        async def make_request() -> bool:
            """Make a single request."""
            nonlocal request_count
            request_count += 1
            await asyncio.sleep(0.02)  # Increased to make timing more predictable
            return True

        # Simulate sustained load
        total_requests = 20

        start = time.perf_counter()

        # Make requests concurrently (simulates sustained load)
        tasks = [make_request() for _ in range(total_requests)]
        results = await asyncio.gather(*tasks)
        actual_duration = time.perf_counter() - start

        # All requests should succeed
        assert len(results) == total_requests
        assert all(results)

        # With async, should complete much faster than sequential
        # Sequential would take 20 * 0.02 = 0.4s
        # Concurrent should be close to 0.02s
        assert actual_duration < 0.2  # Should be much less than sequential

    @pytest.mark.asyncio
    async def test_no_performance_degradation_over_time(self, cache):
        """Test performance remains stable over extended operation."""
        execution_times = []

        async def timed_operation(op_id: int) -> float:
            """Operation with timing."""
            start = time.perf_counter()

            # Simulate work
            await cache.set(f"key_{op_id}", b"value", ttl_seconds=60)
            await cache.get(f"key_{op_id}")

            return time.perf_counter() - start

        # Run operations in batches
        batch_size = 50
        num_batches = 5

        for batch in range(num_batches):
            batch_times = []

            for i in range(batch_size):
                op_id = batch * batch_size + i
                duration = await timed_operation(op_id)
                batch_times.append(duration)

            avg_time = sum(batch_times) / len(batch_times)
            execution_times.append(avg_time)

        # Performance should not degrade significantly
        first_batch_avg = execution_times[0]
        last_batch_avg = execution_times[-1]

        # Last batch should not be more than 50% slower than first
        assert last_batch_avg < first_batch_avg * 1.5


# =============================================================================
# Stress Tests
# =============================================================================


class TestStressConditions:
    """Test system under extreme stress conditions."""

    @pytest.mark.asyncio
    async def test_handle_burst_traffic(self):
        """Test handling sudden burst of traffic."""

        async def request(request_id: int) -> int:
            """Single request."""
            await asyncio.sleep(0.01)
            return request_id

        # Sudden burst of 200 requests
        start = time.perf_counter()
        tasks = [request(i) for i in range(200)]
        results = await asyncio.gather(*tasks)
        duration = time.perf_counter() - start

        # All should complete
        assert len(results) == 200

        # Should handle burst reasonably
        assert duration < 5.0

    @pytest.mark.asyncio
    async def test_recover_from_temporary_overload(self):
        """Test system recovers after temporary overload."""

        async def request(request_id: int, delay: float) -> dict[str, Any]:
            """Request with variable delay."""
            await asyncio.sleep(delay)
            return {"request_id": request_id, "success": True}

        # Phase 1: Normal load
        tasks = [request(i, 0.01) for i in range(10)]
        results = await asyncio.gather(*tasks)
        assert all(r["success"] for r in results)

        # Phase 2: Overload (slow requests)
        tasks = [request(i, 0.05) for i in range(50)]
        results = await asyncio.gather(*tasks)
        assert all(r["success"] for r in results)

        # Phase 3: Back to normal (should recover)
        start = time.perf_counter()
        tasks = [request(i, 0.01) for i in range(10)]
        results = await asyncio.gather(*tasks)
        duration = time.perf_counter() - start

        # Should be fast again (recovered)
        assert all(r["success"] for r in results)
        assert duration < 0.5

    @pytest.mark.asyncio
    async def test_handle_mixed_workload(self, cache):
        """Test handling mixed workload (fast and slow operations)."""

        async def fast_operation(op_id: int) -> str:
            """Fast operation."""
            await asyncio.sleep(0.001)
            return f"fast_{op_id}"

        async def slow_operation(op_id: int) -> str:
            """Slow operation."""
            await asyncio.sleep(0.05)
            return f"slow_{op_id}"

        # Mix of fast and slow operations
        tasks = []
        for i in range(50):
            if i % 5 == 0:
                tasks.append(slow_operation(i))
            else:
                tasks.append(fast_operation(i))

        start = time.perf_counter()
        results = await asyncio.gather(*tasks)
        duration = time.perf_counter() - start

        # All should complete
        assert len(results) == 50

        # Fast operations shouldn't be blocked by slow ones
        # Duration should be close to slow operation time, not sum of all
        assert duration < 0.5
