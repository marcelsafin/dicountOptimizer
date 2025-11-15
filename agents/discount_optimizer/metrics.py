"""
Metrics collection and monitoring for observability.

This module provides comprehensive metrics collection for:
- Agent execution time and success rate
- API call latency and success rate
- Cache hit/miss rate
- Performance profiling hooks
- Prometheus-compatible metric export

Requirements: 10.2, 10.3, 10.6
"""

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Iterator, Literal
from collections import defaultdict
import structlog

from .config import settings

logger = structlog.get_logger(__name__)


# =============================================================================
# Metric Data Classes
# =============================================================================

@dataclass
class TimingMetric:
    """Timing metric for measuring operation duration.
    
    Tracks count, total time, min, max, and calculates average.
    """
    count: int = 0
    total_seconds: float = 0.0
    min_seconds: float = float('inf')
    max_seconds: float = 0.0
    
    @property
    def average_seconds(self) -> float:
        """Calculate average duration in seconds."""
        if self.count == 0:
            return 0.0
        return self.total_seconds / self.count
    
    @property
    def average_ms(self) -> float:
        """Calculate average duration in milliseconds."""
        return self.average_seconds * 1000.0
    
    def record(self, duration_seconds: float) -> None:
        """Record a new timing measurement.
        
        Args:
            duration_seconds: Duration to record in seconds
        """
        self.count += 1
        self.total_seconds += duration_seconds
        self.min_seconds = min(self.min_seconds, duration_seconds)
        self.max_seconds = max(self.max_seconds, duration_seconds)
    
    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary for JSON serialization."""
        return {
            'count': self.count,
            'total_seconds': round(self.total_seconds, 3),
            'average_ms': round(self.average_ms, 2),
            'min_ms': round(self.min_seconds * 1000, 2),
            'max_ms': round(self.max_seconds * 1000, 2),
        }


@dataclass
class CounterMetric:
    """Counter metric for tracking occurrences.
    
    Simple counter that can be incremented.
    """
    count: int = 0
    
    def increment(self, amount: int = 1) -> None:
        """Increment the counter.
        
        Args:
            amount: Amount to increment by (default: 1)
        """
        self.count += amount
    
    def to_dict(self) -> dict[str, int]:
        """Convert to dictionary for JSON serialization."""
        return {'count': self.count}


@dataclass
class SuccessRateMetric:
    """Success rate metric for tracking success/failure ratios.
    
    Tracks total attempts, successes, and failures.
    """
    total: int = 0
    successes: int = 0
    failures: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage (0-100)."""
        if self.total == 0:
            return 0.0
        return (self.successes / self.total) * 100.0
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate as percentage (0-100)."""
        if self.total == 0:
            return 0.0
        return (self.failures / self.total) * 100.0
    
    def record_success(self) -> None:
        """Record a successful operation."""
        self.total += 1
        self.successes += 1
    
    def record_failure(self) -> None:
        """Record a failed operation."""
        self.total += 1
        self.failures += 1
    
    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary for JSON serialization."""
        return {
            'total': self.total,
            'successes': self.successes,
            'failures': self.failures,
            'success_rate': round(self.success_rate, 2),
            'failure_rate': round(self.failure_rate, 2),
        }


@dataclass
class CacheMetrics:
    """Cache performance metrics.
    
    Tracks cache hits, misses, and calculates hit rate.
    """
    hits: int = 0
    misses: int = 0
    sets: int = 0
    evictions: int = 0
    
    @property
    def total_requests(self) -> int:
        """Total number of cache get requests."""
        return self.hits + self.misses
    
    @property
    def hit_rate(self) -> float:
        """Cache hit rate as percentage (0-100)."""
        if self.total_requests == 0:
            return 0.0
        return (self.hits / self.total_requests) * 100.0
    
    @property
    def miss_rate(self) -> float:
        """Cache miss rate as percentage (0-100)."""
        if self.total_requests == 0:
            return 0.0
        return (self.misses / self.total_requests) * 100.0
    
    def record_hit(self) -> None:
        """Record a cache hit."""
        self.hits += 1
    
    def record_miss(self) -> None:
        """Record a cache miss."""
        self.misses += 1
    
    def record_set(self) -> None:
        """Record a cache set operation."""
        self.sets += 1
    
    def record_eviction(self) -> None:
        """Record a cache eviction."""
        self.evictions += 1
    
    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary for JSON serialization."""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'sets': self.sets,
            'evictions': self.evictions,
            'total_requests': self.total_requests,
            'hit_rate': round(self.hit_rate, 2),
            'miss_rate': round(self.miss_rate, 2),
        }


# =============================================================================
# Metrics Collector
# =============================================================================

class MetricsCollector:
    """Central metrics collector for the application.
    
    Collects and aggregates metrics for:
    - Agent execution (timing, success rate)
    - API calls (timing, success rate, by endpoint)
    - Cache performance (hit rate, miss rate)
    - Custom counters and timers
    
    Thread-safe for concurrent access.
    
    Example:
        >>> collector = MetricsCollector()
        >>> with collector.time_agent("meal_suggester"):
        ...     # Agent execution code
        ...     pass
        >>> collector.record_agent_success("meal_suggester")
        >>> metrics = collector.get_metrics()
    """
    
    def __init__(self) -> None:
        """Initialize the metrics collector."""
        # Agent metrics
        self.agent_timing: dict[str, TimingMetric] = defaultdict(TimingMetric)
        self.agent_success_rate: dict[str, SuccessRateMetric] = defaultdict(SuccessRateMetric)
        
        # API metrics
        self.api_timing: dict[str, TimingMetric] = defaultdict(TimingMetric)
        self.api_success_rate: dict[str, SuccessRateMetric] = defaultdict(SuccessRateMetric)
        
        # Cache metrics
        self.cache_metrics = CacheMetrics()
        
        # Custom counters
        self.counters: dict[str, CounterMetric] = defaultdict(CounterMetric)
        
        # Custom timers
        self.timers: dict[str, TimingMetric] = defaultdict(TimingMetric)
        
        # Startup time
        self.startup_time = datetime.now()
        
        logger.info(
            "metrics_collector_initialized",
            metrics_enabled=settings.enable_metrics,
        )
    
    # =========================================================================
    # Agent Metrics
    # =========================================================================
    
    @contextmanager
    def time_agent(self, agent_name: str) -> Iterator[None]:
        """Context manager for timing agent execution.
        
        Args:
            agent_name: Name of the agent being timed
        
        Example:
            >>> with collector.time_agent("meal_suggester"):
            ...     # Agent execution code
            ...     pass
        """
        if not settings.enable_metrics:
            yield
            return
        
        start_time = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start_time
            self.agent_timing[agent_name].record(duration)
            
            logger.debug(
                "agent_execution_timed",
                agent=agent_name,
                duration_ms=round(duration * 1000, 2),
            )
    
    def record_agent_success(self, agent_name: str) -> None:
        """Record a successful agent execution.
        
        Args:
            agent_name: Name of the agent
        """
        if not settings.enable_metrics:
            return
        
        self.agent_success_rate[agent_name].record_success()
        
        logger.debug(
            "agent_success_recorded",
            agent=agent_name,
            success_rate=self.agent_success_rate[agent_name].success_rate,
        )
    
    def record_agent_failure(self, agent_name: str, error_type: str | None = None) -> None:
        """Record a failed agent execution.
        
        Args:
            agent_name: Name of the agent
            error_type: Optional error type for categorization
        """
        if not settings.enable_metrics:
            return
        
        self.agent_success_rate[agent_name].record_failure()
        
        # Track error types
        if error_type:
            error_key = f"agent_error:{agent_name}:{error_type}"
            self.counters[error_key].increment()
        
        logger.debug(
            "agent_failure_recorded",
            agent=agent_name,
            error_type=error_type,
            failure_rate=self.agent_success_rate[agent_name].failure_rate,
        )
    
    # =========================================================================
    # API Metrics
    # =========================================================================
    
    @contextmanager
    def time_api_call(self, api_name: str, endpoint: str | None = None) -> Iterator[None]:
        """Context manager for timing API calls.
        
        Args:
            api_name: Name of the API (e.g., "salling", "google_maps")
            endpoint: Optional specific endpoint being called
        
        Example:
            >>> with collector.time_api_call("salling", "/food-waste"):
            ...     response = await client.get(url)
        """
        if not settings.enable_metrics:
            yield
            return
        
        metric_key = f"{api_name}:{endpoint}" if endpoint else api_name
        start_time = time.perf_counter()
        
        try:
            yield
        finally:
            duration = time.perf_counter() - start_time
            self.api_timing[metric_key].record(duration)
            
            logger.debug(
                "api_call_timed",
                api=api_name,
                endpoint=endpoint,
                duration_ms=round(duration * 1000, 2),
            )
    
    def record_api_success(self, api_name: str, endpoint: str | None = None) -> None:
        """Record a successful API call.
        
        Args:
            api_name: Name of the API
            endpoint: Optional specific endpoint
        """
        if not settings.enable_metrics:
            return
        
        metric_key = f"{api_name}:{endpoint}" if endpoint else api_name
        self.api_success_rate[metric_key].record_success()
        
        logger.debug(
            "api_success_recorded",
            api=api_name,
            endpoint=endpoint,
            success_rate=self.api_success_rate[metric_key].success_rate,
        )
    
    def record_api_failure(
        self,
        api_name: str,
        endpoint: str | None = None,
        status_code: int | None = None,
        error_type: str | None = None
    ) -> None:
        """Record a failed API call.
        
        Args:
            api_name: Name of the API
            endpoint: Optional specific endpoint
            status_code: Optional HTTP status code
            error_type: Optional error type for categorization
        """
        if not settings.enable_metrics:
            return
        
        metric_key = f"{api_name}:{endpoint}" if endpoint else api_name
        self.api_success_rate[metric_key].record_failure()
        
        # Track error types and status codes
        if status_code:
            error_key = f"api_error:{api_name}:status_{status_code}"
            self.counters[error_key].increment()
        
        if error_type:
            error_key = f"api_error:{api_name}:{error_type}"
            self.counters[error_key].increment()
        
        logger.debug(
            "api_failure_recorded",
            api=api_name,
            endpoint=endpoint,
            status_code=status_code,
            error_type=error_type,
            failure_rate=self.api_success_rate[metric_key].failure_rate,
        )
    
    # =========================================================================
    # Cache Metrics
    # =========================================================================
    
    def record_cache_hit(self) -> None:
        """Record a cache hit."""
        if not settings.enable_metrics:
            return
        
        self.cache_metrics.record_hit()
    
    def record_cache_miss(self) -> None:
        """Record a cache miss."""
        if not settings.enable_metrics:
            return
        
        self.cache_metrics.record_miss()
    
    def record_cache_set(self) -> None:
        """Record a cache set operation."""
        if not settings.enable_metrics:
            return
        
        self.cache_metrics.record_set()
    
    def record_cache_eviction(self) -> None:
        """Record a cache eviction."""
        if not settings.enable_metrics:
            return
        
        self.cache_metrics.record_eviction()
    
    # =========================================================================
    # Custom Metrics
    # =========================================================================
    
    def increment_counter(self, name: str, amount: int = 1) -> None:
        """Increment a custom counter.
        
        Args:
            name: Counter name
            amount: Amount to increment by (default: 1)
        
        Example:
            >>> collector.increment_counter("requests_processed")
            >>> collector.increment_counter("items_processed", amount=5)
        """
        if not settings.enable_metrics:
            return
        
        self.counters[name].increment(amount)
    
    @contextmanager
    def time_operation(self, name: str) -> Iterator[None]:
        """Context manager for timing custom operations.
        
        Args:
            name: Operation name
        
        Example:
            >>> with collector.time_operation("database_query"):
            ...     result = await db.query()
        """
        if not settings.enable_metrics:
            yield
            return
        
        start_time = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start_time
            self.timers[name].record(duration)
    
    # =========================================================================
    # Metrics Retrieval
    # =========================================================================
    
    def get_metrics(self) -> dict[str, Any]:
        """Get all collected metrics as a dictionary.
        
        Returns:
            Dictionary containing all metrics organized by category
        
        Example:
            >>> metrics = collector.get_metrics()
            >>> print(f"Cache hit rate: {metrics['cache']['hit_rate']}%")
        """
        uptime = datetime.now() - self.startup_time
        
        return {
            'system': {
                'uptime_seconds': uptime.total_seconds(),
                'uptime_human': str(uptime).split('.')[0],  # Remove microseconds
                'metrics_enabled': settings.enable_metrics,
                'environment': settings.environment,
            },
            'agents': {
                'timing': {
                    name: metric.to_dict()
                    for name, metric in self.agent_timing.items()
                },
                'success_rate': {
                    name: metric.to_dict()
                    for name, metric in self.agent_success_rate.items()
                },
            },
            'api': {
                'timing': {
                    name: metric.to_dict()
                    for name, metric in self.api_timing.items()
                },
                'success_rate': {
                    name: metric.to_dict()
                    for name, metric in self.api_success_rate.items()
                },
            },
            'cache': self.cache_metrics.to_dict(),
            'counters': {
                name: metric.to_dict()
                for name, metric in self.counters.items()
            },
            'timers': {
                name: metric.to_dict()
                for name, metric in self.timers.items()
            },
        }
    
    def get_summary(self) -> dict[str, Any]:
        """Get a summary of key metrics.
        
        Returns:
            Dictionary with high-level metric summary
        
        Example:
            >>> summary = collector.get_summary()
            >>> print(f"Total agent executions: {summary['total_agent_executions']}")
        """
        total_agent_executions = sum(
            metric.count for metric in self.agent_timing.values()
        )
        total_api_calls = sum(
            metric.count for metric in self.api_timing.values()
        )
        
        # Calculate overall success rates
        total_agent_successes = sum(
            metric.successes for metric in self.agent_success_rate.values()
        )
        total_agent_attempts = sum(
            metric.total for metric in self.agent_success_rate.values()
        )
        overall_agent_success_rate = (
            (total_agent_successes / total_agent_attempts * 100.0)
            if total_agent_attempts > 0 else 0.0
        )
        
        total_api_successes = sum(
            metric.successes for metric in self.api_success_rate.values()
        )
        total_api_attempts = sum(
            metric.total for metric in self.api_success_rate.values()
        )
        overall_api_success_rate = (
            (total_api_successes / total_api_attempts * 100.0)
            if total_api_attempts > 0 else 0.0
        )
        
        uptime = datetime.now() - self.startup_time
        
        return {
            'uptime_seconds': uptime.total_seconds(),
            'total_agent_executions': total_agent_executions,
            'total_api_calls': total_api_calls,
            'overall_agent_success_rate': round(overall_agent_success_rate, 2),
            'overall_api_success_rate': round(overall_api_success_rate, 2),
            'cache_hit_rate': round(self.cache_metrics.hit_rate, 2),
            'cache_total_requests': self.cache_metrics.total_requests,
        }
    
    def reset(self) -> None:
        """Reset all metrics to zero.
        
        Useful for testing or when starting a new monitoring period.
        """
        self.agent_timing.clear()
        self.agent_success_rate.clear()
        self.api_timing.clear()
        self.api_success_rate.clear()
        self.cache_metrics = CacheMetrics()
        self.counters.clear()
        self.timers.clear()
        self.startup_time = datetime.now()
        
        logger.info("metrics_reset")
    
    # =========================================================================
    # Prometheus Export
    # =========================================================================
    
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text format.
        
        Returns:
            Metrics in Prometheus exposition format
        
        Example:
            >>> prometheus_text = collector.export_prometheus()
            >>> # Can be served at /metrics endpoint
        """
        lines: list[str] = []
        
        # System metrics
        uptime = (datetime.now() - self.startup_time).total_seconds()
        lines.append('# HELP shopping_optimizer_uptime_seconds Application uptime in seconds')
        lines.append('# TYPE shopping_optimizer_uptime_seconds gauge')
        lines.append(f'shopping_optimizer_uptime_seconds {uptime}')
        lines.append('')
        
        # Agent timing metrics
        lines.append('# HELP shopping_optimizer_agent_duration_seconds Agent execution duration')
        lines.append('# TYPE shopping_optimizer_agent_duration_seconds summary')
        for agent_name, metric in self.agent_timing.items():
            labels = f'agent="{agent_name}"'
            lines.append(f'shopping_optimizer_agent_duration_seconds_count{{{labels}}} {metric.count}')
            lines.append(f'shopping_optimizer_agent_duration_seconds_sum{{{labels}}} {metric.total_seconds}')
        lines.append('')
        
        # Agent success rate
        lines.append('# HELP shopping_optimizer_agent_success_total Successful agent executions')
        lines.append('# TYPE shopping_optimizer_agent_success_total counter')
        for agent_name, success_metric in self.agent_success_rate.items():
            labels = f'agent="{agent_name}"'
            lines.append(f'shopping_optimizer_agent_success_total{{{labels}}} {success_metric.successes}')
        lines.append('')
        
        lines.append('# HELP shopping_optimizer_agent_failure_total Failed agent executions')
        lines.append('# TYPE shopping_optimizer_agent_failure_total counter')
        for agent_name, success_metric in self.agent_success_rate.items():
            labels = f'agent="{agent_name}"'
            lines.append(f'shopping_optimizer_agent_failure_total{{{labels}}} {success_metric.failures}')
        lines.append('')
        
        # API timing metrics
        lines.append('# HELP shopping_optimizer_api_duration_seconds API call duration')
        lines.append('# TYPE shopping_optimizer_api_duration_seconds summary')
        for api_name, metric in self.api_timing.items():
            labels = f'api="{api_name}"'
            lines.append(f'shopping_optimizer_api_duration_seconds_count{{{labels}}} {metric.count}')
            lines.append(f'shopping_optimizer_api_duration_seconds_sum{{{labels}}} {metric.total_seconds}')
        lines.append('')
        
        # API success rate
        lines.append('# HELP shopping_optimizer_api_success_total Successful API calls')
        lines.append('# TYPE shopping_optimizer_api_success_total counter')
        for api_name, success_metric in self.api_success_rate.items():
            labels = f'api="{api_name}"'
            lines.append(f'shopping_optimizer_api_success_total{{{labels}}} {success_metric.successes}')
        lines.append('')
        
        lines.append('# HELP shopping_optimizer_api_failure_total Failed API calls')
        lines.append('# TYPE shopping_optimizer_api_failure_total counter')
        for api_name, success_metric in self.api_success_rate.items():
            labels = f'api="{api_name}"'
            lines.append(f'shopping_optimizer_api_failure_total{{{labels}}} {success_metric.failures}')
        lines.append('')
        
        # Cache metrics
        lines.append('# HELP shopping_optimizer_cache_hits_total Cache hits')
        lines.append('# TYPE shopping_optimizer_cache_hits_total counter')
        lines.append(f'shopping_optimizer_cache_hits_total {self.cache_metrics.hits}')
        lines.append('')
        
        lines.append('# HELP shopping_optimizer_cache_misses_total Cache misses')
        lines.append('# TYPE shopping_optimizer_cache_misses_total counter')
        lines.append(f'shopping_optimizer_cache_misses_total {self.cache_metrics.misses}')
        lines.append('')
        
        lines.append('# HELP shopping_optimizer_cache_hit_rate Cache hit rate percentage')
        lines.append('# TYPE shopping_optimizer_cache_hit_rate gauge')
        lines.append(f'shopping_optimizer_cache_hit_rate {self.cache_metrics.hit_rate}')
        lines.append('')
        
        return '\n'.join(lines)


# =============================================================================
# Global Metrics Collector
# =============================================================================

# Global metrics collector instance
_global_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance.
    
    Creates the collector on first access (lazy initialization).
    
    Returns:
        Global MetricsCollector instance
    
    Example:
        >>> collector = get_metrics_collector()
        >>> with collector.time_agent("meal_suggester"):
        ...     # Agent code
        ...     pass
    """
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector


def reset_metrics() -> None:
    """Reset the global metrics collector.
    
    Useful for testing or when starting a new monitoring period.
    """
    collector = get_metrics_collector()
    collector.reset()


# =============================================================================
# Performance Profiling
# =============================================================================

@contextmanager
def profile_operation(
    operation_name: str,
    log_threshold_ms: float = 1000.0,
) -> Iterator[None]:
    """Context manager for profiling operations with automatic logging.
    
    Profiles an operation and logs a warning if it exceeds the threshold.
    Also records the timing in metrics.
    
    Args:
        operation_name: Name of the operation being profiled
        log_threshold_ms: Log warning if operation exceeds this duration (ms)
    
    Example:
        >>> with profile_operation("expensive_calculation", log_threshold_ms=500):
        ...     result = expensive_function()
    """
    collector = get_metrics_collector()
    start_time = time.perf_counter()
    
    try:
        yield
    finally:
        duration = time.perf_counter() - start_time
        duration_ms = duration * 1000
        
        # Record in metrics
        collector.timers[operation_name].record(duration)
        
        # Log if exceeds threshold
        if duration_ms > log_threshold_ms:
            logger.warning(
                "slow_operation_detected",
                operation=operation_name,
                duration_ms=round(duration_ms, 2),
                threshold_ms=log_threshold_ms,
            )
        else:
            logger.debug(
                "operation_profiled",
                operation=operation_name,
                duration_ms=round(duration_ms, 2),
            )
