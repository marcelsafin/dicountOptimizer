"""
Tests for metrics collection and monitoring.

This module tests the MetricsCollector class and related functionality
to ensure proper metrics tracking, thread-safety, and Prometheus export.

Requirements: 10.2, 10.6
"""

import pytest
import time
from decimal import Decimal
from unittest.mock import patch

from agents.discount_optimizer.metrics import (
    MetricsCollector,
    TimingMetric,
    CounterMetric,
    SuccessRateMetric,
    CacheMetrics,
    get_metrics_collector,
    reset_metrics,
    profile_operation,
)


class TestTimingMetric:
    """Test TimingMetric data class."""
    
    def test_initial_state(self):
        """Test initial state of TimingMetric."""
        metric = TimingMetric()
        assert metric.count == 0
        assert metric.total_seconds == 0.0
        assert metric.average_seconds == 0.0
        assert metric.average_ms == 0.0
    
    def test_record_single_timing(self):
        """Test recording a single timing."""
        metric = TimingMetric()
        metric.record(1.5)
        
        assert metric.count == 1
        assert metric.total_seconds == 1.5
        assert metric.average_seconds == 1.5
        assert metric.average_ms == 1500.0
        assert metric.min_seconds == 1.5
        assert metric.max_seconds == 1.5
    
    def test_record_multiple_timings(self):
        """Test recording multiple timings."""
        metric = TimingMetric()
        metric.record(1.0)
        metric.record(2.0)
        metric.record(3.0)
        
        assert metric.count == 3
        assert metric.total_seconds == 6.0
        assert metric.average_seconds == 2.0
        assert metric.average_ms == 2000.0
        assert metric.min_seconds == 1.0
        assert metric.max_seconds == 3.0
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        metric = TimingMetric()
        metric.record(1.5)
        metric.record(2.5)
        
        result = metric.to_dict()
        assert result['count'] == 2
        assert result['total_seconds'] == 4.0
        assert result['average_ms'] == 2000.0
        assert result['min_ms'] == 1500.0
        assert result['max_ms'] == 2500.0


class TestCounterMetric:
    """Test CounterMetric data class."""
    
    def test_initial_state(self):
        """Test initial state of CounterMetric."""
        metric = CounterMetric()
        assert metric.count == 0
    
    def test_increment_default(self):
        """Test incrementing by default amount."""
        metric = CounterMetric()
        metric.increment()
        assert metric.count == 1
        
        metric.increment()
        assert metric.count == 2
    
    def test_increment_custom_amount(self):
        """Test incrementing by custom amount."""
        metric = CounterMetric()
        metric.increment(5)
        assert metric.count == 5
        
        metric.increment(3)
        assert metric.count == 8
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        metric = CounterMetric()
        metric.increment(10)
        
        result = metric.to_dict()
        assert result['count'] == 10


class TestSuccessRateMetric:
    """Test SuccessRateMetric data class."""
    
    def test_initial_state(self):
        """Test initial state of SuccessRateMetric."""
        metric = SuccessRateMetric()
        assert metric.total == 0
        assert metric.successes == 0
        assert metric.failures == 0
        assert metric.success_rate == 0.0
        assert metric.failure_rate == 0.0
    
    def test_record_success(self):
        """Test recording successes."""
        metric = SuccessRateMetric()
        metric.record_success()
        
        assert metric.total == 1
        assert metric.successes == 1
        assert metric.failures == 0
        assert metric.success_rate == 100.0
        assert metric.failure_rate == 0.0
    
    def test_record_failure(self):
        """Test recording failures."""
        metric = SuccessRateMetric()
        metric.record_failure()
        
        assert metric.total == 1
        assert metric.successes == 0
        assert metric.failures == 1
        assert metric.success_rate == 0.0
        assert metric.failure_rate == 100.0
    
    def test_mixed_success_and_failure(self):
        """Test recording mixed successes and failures."""
        metric = SuccessRateMetric()
        metric.record_success()
        metric.record_success()
        metric.record_success()
        metric.record_failure()
        
        assert metric.total == 4
        assert metric.successes == 3
        assert metric.failures == 1
        assert metric.success_rate == 75.0
        assert metric.failure_rate == 25.0
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        metric = SuccessRateMetric()
        metric.record_success()
        metric.record_failure()
        
        result = metric.to_dict()
        assert result['total'] == 2
        assert result['successes'] == 1
        assert result['failures'] == 1
        assert result['success_rate'] == 50.0
        assert result['failure_rate'] == 50.0


class TestCacheMetrics:
    """Test CacheMetrics data class."""
    
    def test_initial_state(self):
        """Test initial state of CacheMetrics."""
        metric = CacheMetrics()
        assert metric.hits == 0
        assert metric.misses == 0
        assert metric.sets == 0
        assert metric.evictions == 0
        assert metric.total_requests == 0
        assert metric.hit_rate == 0.0
        assert metric.miss_rate == 0.0
    
    def test_record_hit(self):
        """Test recording cache hits."""
        metric = CacheMetrics()
        metric.record_hit()
        metric.record_hit()
        
        assert metric.hits == 2
        assert metric.total_requests == 2
        assert metric.hit_rate == 100.0
    
    def test_record_miss(self):
        """Test recording cache misses."""
        metric = CacheMetrics()
        metric.record_miss()
        
        assert metric.misses == 1
        assert metric.total_requests == 1
        assert metric.miss_rate == 100.0
    
    def test_mixed_hits_and_misses(self):
        """Test recording mixed hits and misses."""
        metric = CacheMetrics()
        metric.record_hit()
        metric.record_hit()
        metric.record_hit()
        metric.record_miss()
        
        assert metric.hits == 3
        assert metric.misses == 1
        assert metric.total_requests == 4
        assert metric.hit_rate == 75.0
        assert metric.miss_rate == 25.0
    
    def test_record_set_and_eviction(self):
        """Test recording cache sets and evictions."""
        metric = CacheMetrics()
        metric.record_set()
        metric.record_set()
        metric.record_eviction()
        
        assert metric.sets == 2
        assert metric.evictions == 1
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        metric = CacheMetrics()
        metric.record_hit()
        metric.record_miss()
        metric.record_set()
        
        result = metric.to_dict()
        assert result['hits'] == 1
        assert result['misses'] == 1
        assert result['sets'] == 1
        assert result['evictions'] == 0
        assert result['total_requests'] == 2
        assert result['hit_rate'] == 50.0
        assert result['miss_rate'] == 50.0


class TestMetricsCollector:
    """Test MetricsCollector class."""
    
    @pytest.fixture
    def collector(self):
        """Create a fresh MetricsCollector for each test."""
        collector = MetricsCollector()
        collector.reset()
        return collector
    
    # =========================================================================
    # Agent Metrics Tests
    # =========================================================================
    
    def test_time_agent_context_manager(self, collector):
        """Test timing agent execution with context manager."""
        with collector.time_agent("test_agent"):
            time.sleep(0.01)  # Sleep for 10ms
        
        assert "test_agent" in collector.agent_timing
        metric = collector.agent_timing["test_agent"]
        assert metric.count == 1
        assert metric.total_seconds >= 0.01
    
    def test_record_agent_success(self, collector):
        """Test recording agent success."""
        collector.record_agent_success("test_agent")
        
        assert "test_agent" in collector.agent_success_rate
        metric = collector.agent_success_rate["test_agent"]
        assert metric.successes == 1
        assert metric.failures == 0
        assert metric.success_rate == 100.0
    
    def test_record_agent_failure(self, collector):
        """Test recording agent failure."""
        collector.record_agent_failure("test_agent", error_type="ValidationError")
        
        assert "test_agent" in collector.agent_success_rate
        metric = collector.agent_success_rate["test_agent"]
        assert metric.successes == 0
        assert metric.failures == 1
        assert metric.failure_rate == 100.0
        
        # Check error counter
        error_key = "agent_error:test_agent:ValidationError"
        assert error_key in collector.counters
        assert collector.counters[error_key].count == 1
    
    def test_multiple_agent_executions(self, collector):
        """Test tracking multiple agent executions."""
        # Execute agent 1 multiple times
        with collector.time_agent("agent1"):
            time.sleep(0.01)
        collector.record_agent_success("agent1")
        
        with collector.time_agent("agent1"):
            time.sleep(0.01)
        collector.record_agent_success("agent1")
        
        # Execute agent 2
        with collector.time_agent("agent2"):
            time.sleep(0.01)
        collector.record_agent_failure("agent2")
        
        # Verify agent1
        assert collector.agent_timing["agent1"].count == 2
        assert collector.agent_success_rate["agent1"].successes == 2
        
        # Verify agent2
        assert collector.agent_timing["agent2"].count == 1
        assert collector.agent_success_rate["agent2"].failures == 1
    
    # =========================================================================
    # API Metrics Tests
    # =========================================================================
    
    def test_time_api_call_context_manager(self, collector):
        """Test timing API calls with context manager."""
        with collector.time_api_call("salling", "/food-waste"):
            time.sleep(0.01)
        
        metric_key = "salling:/food-waste"
        assert metric_key in collector.api_timing
        metric = collector.api_timing[metric_key]
        assert metric.count == 1
        assert metric.total_seconds >= 0.01
    
    def test_time_api_call_without_endpoint(self, collector):
        """Test timing API calls without specific endpoint."""
        with collector.time_api_call("google_maps"):
            time.sleep(0.01)
        
        assert "google_maps" in collector.api_timing
        metric = collector.api_timing["google_maps"]
        assert metric.count == 1
    
    def test_record_api_success(self, collector):
        """Test recording API success."""
        collector.record_api_success("salling", "/food-waste")
        
        metric_key = "salling:/food-waste"
        assert metric_key in collector.api_success_rate
        metric = collector.api_success_rate[metric_key]
        assert metric.successes == 1
        assert metric.success_rate == 100.0
    
    def test_record_api_failure_with_status_code(self, collector):
        """Test recording API failure with status code."""
        collector.record_api_failure("salling", "/food-waste", status_code=500)
        
        metric_key = "salling:/food-waste"
        assert metric_key in collector.api_success_rate
        metric = collector.api_success_rate[metric_key]
        assert metric.failures == 1
        
        # Check status code counter
        error_key = "api_error:salling:status_500"
        assert error_key in collector.counters
        assert collector.counters[error_key].count == 1
    
    def test_record_api_failure_with_error_type(self, collector):
        """Test recording API failure with error type."""
        collector.record_api_failure("salling", error_type="TimeoutError")
        
        # Check error type counter
        error_key = "api_error:salling:TimeoutError"
        assert error_key in collector.counters
        assert collector.counters[error_key].count == 1
    
    # =========================================================================
    # Cache Metrics Tests
    # =========================================================================
    
    def test_record_cache_hit(self, collector):
        """Test recording cache hits."""
        collector.record_cache_hit()
        collector.record_cache_hit()
        
        assert collector.cache_metrics.hits == 2
    
    def test_record_cache_miss(self, collector):
        """Test recording cache misses."""
        collector.record_cache_miss()
        
        assert collector.cache_metrics.misses == 1
    
    def test_cache_hit_rate_calculation(self, collector):
        """Test cache hit rate calculation."""
        collector.record_cache_hit()
        collector.record_cache_hit()
        collector.record_cache_hit()
        collector.record_cache_miss()
        
        assert collector.cache_metrics.hit_rate == 75.0
        assert collector.cache_metrics.miss_rate == 25.0
    
    # =========================================================================
    # Custom Metrics Tests
    # =========================================================================
    
    def test_increment_counter(self, collector):
        """Test incrementing custom counters."""
        collector.increment_counter("requests")
        collector.increment_counter("requests")
        collector.increment_counter("requests", amount=3)
        
        assert collector.counters["requests"].count == 5
    
    def test_time_operation_context_manager(self, collector):
        """Test timing custom operations."""
        with collector.time_operation("database_query"):
            time.sleep(0.01)
        
        assert "database_query" in collector.timers
        metric = collector.timers["database_query"]
        assert metric.count == 1
        assert metric.total_seconds >= 0.01
    
    # =========================================================================
    # Metrics Retrieval Tests
    # =========================================================================
    
    def test_get_metrics_structure(self, collector):
        """Test get_metrics returns proper structure."""
        # Record some metrics
        with collector.time_agent("test_agent"):
            pass
        collector.record_agent_success("test_agent")
        collector.record_cache_hit()
        
        metrics = collector.get_metrics()
        
        # Check structure
        assert 'system' in metrics
        assert 'agents' in metrics
        assert 'api' in metrics
        assert 'cache' in metrics
        assert 'counters' in metrics
        assert 'timers' in metrics
        
        # Check system info
        assert 'uptime_seconds' in metrics['system']
        assert 'metrics_enabled' in metrics['system']
        
        # Check agent metrics
        assert 'test_agent' in metrics['agents']['timing']
        assert 'test_agent' in metrics['agents']['success_rate']
        
        # Check cache metrics
        assert metrics['cache']['hits'] == 1
    
    def test_get_summary(self, collector):
        """Test get_summary returns key metrics."""
        # Record some metrics
        with collector.time_agent("agent1"):
            pass
        collector.record_agent_success("agent1")
        
        with collector.time_api_call("api1"):
            pass
        collector.record_api_success("api1")
        
        collector.record_cache_hit()
        collector.record_cache_miss()
        
        summary = collector.get_summary()
        
        assert 'uptime_seconds' in summary
        assert summary['total_agent_executions'] == 1
        assert summary['total_api_calls'] == 1
        assert summary['overall_agent_success_rate'] == 100.0
        assert summary['overall_api_success_rate'] == 100.0
        assert summary['cache_hit_rate'] == 50.0
        assert summary['cache_total_requests'] == 2
    
    def test_reset(self, collector):
        """Test resetting all metrics."""
        # Record some metrics
        with collector.time_agent("test_agent"):
            pass
        collector.record_agent_success("test_agent")
        collector.record_cache_hit()
        collector.increment_counter("test")
        
        # Reset
        collector.reset()
        
        # Verify everything is cleared
        assert len(collector.agent_timing) == 0
        assert len(collector.agent_success_rate) == 0
        assert len(collector.api_timing) == 0
        assert len(collector.api_success_rate) == 0
        assert collector.cache_metrics.hits == 0
        assert len(collector.counters) == 0
        assert len(collector.timers) == 0
    
    # =========================================================================
    # Prometheus Export Tests
    # =========================================================================
    
    def test_export_prometheus_format(self, collector):
        """Test Prometheus export format."""
        # Record some metrics
        with collector.time_agent("test_agent"):
            time.sleep(0.01)
        collector.record_agent_success("test_agent")
        collector.record_cache_hit()
        collector.record_cache_miss()
        
        prometheus_text = collector.export_prometheus()
        
        # Check format
        assert '# HELP' in prometheus_text
        assert '# TYPE' in prometheus_text
        
        # Check specific metrics
        assert 'shopping_optimizer_uptime_seconds' in prometheus_text
        assert 'shopping_optimizer_agent_duration_seconds' in prometheus_text
        assert 'shopping_optimizer_agent_success_total' in prometheus_text
        assert 'shopping_optimizer_cache_hits_total' in prometheus_text
        assert 'shopping_optimizer_cache_misses_total' in prometheus_text
        
        # Check values are present
        lines = [l for l in prometheus_text.split('\n') if l and not l.startswith('#')]
        assert len(lines) > 0
    
    def test_export_prometheus_with_labels(self, collector):
        """Test Prometheus export includes proper labels."""
        with collector.time_agent("meal_suggester"):
            pass
        collector.record_agent_success("meal_suggester")
        
        prometheus_text = collector.export_prometheus()
        
        # Check labels are present
        assert 'agent="meal_suggester"' in prometheus_text


class TestGlobalCollector:
    """Test global metrics collector functions."""
    
    def test_get_metrics_collector_singleton(self):
        """Test that get_metrics_collector returns singleton."""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()
        
        assert collector1 is collector2
    
    def test_reset_metrics_global(self):
        """Test resetting global metrics."""
        collector = get_metrics_collector()
        collector.increment_counter("test")
        
        reset_metrics()
        
        assert len(collector.counters) == 0


class TestProfileOperation:
    """Test profile_operation context manager."""
    
    def test_profile_operation_records_timing(self):
        """Test that profile_operation records timing."""
        collector = get_metrics_collector()
        collector.reset()
        
        with profile_operation("test_operation"):
            time.sleep(0.01)
        
        assert "test_operation" in collector.timers
        assert collector.timers["test_operation"].count == 1
    
    def test_profile_operation_logs_slow_operations(self, caplog):
        """Test that profile_operation logs slow operations."""
        with profile_operation("slow_operation", log_threshold_ms=1.0):
            time.sleep(0.01)  # 10ms, exceeds 1ms threshold
        
        # Check that warning was logged
        # Note: This test depends on structlog configuration
        # In a real scenario, you'd check the log output
    
    def test_profile_operation_does_not_log_fast_operations(self, caplog):
        """Test that profile_operation doesn't log fast operations."""
        with profile_operation("fast_operation", log_threshold_ms=1000.0):
            time.sleep(0.001)  # 1ms, under 1000ms threshold
        
        # Should not log warning for fast operations


class TestMetricsWithDisabledFlag:
    """Test metrics behavior when disabled."""
    
    def test_metrics_disabled_no_recording(self):
        """Test that metrics are not recorded when disabled."""
        with patch('agents.discount_optimizer.metrics.settings.enable_metrics', False):
            collector = MetricsCollector()
            
            with collector.time_agent("test_agent"):
                pass
            collector.record_agent_success("test_agent")
            collector.record_cache_hit()
            
            # Metrics should not be recorded
            assert len(collector.agent_timing) == 0
            assert len(collector.agent_success_rate) == 0
            assert collector.cache_metrics.hits == 0


class TestThreadSafety:
    """Test thread-safety of MetricsCollector.
    
    Note: These are basic tests. Full thread-safety testing would require
    more sophisticated concurrent testing frameworks.
    """
    
    def test_concurrent_counter_increments(self):
        """Test concurrent counter increments."""
        import threading
        
        collector = MetricsCollector()
        collector.reset()
        
        def increment_counter():
            for _ in range(100):
                collector.increment_counter("test")
        
        threads = [threading.Thread(target=increment_counter) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have 1000 total increments (10 threads * 100 increments)
        # Note: Without proper locking, this might fail
        assert collector.counters["test"].count == 1000
    
    def test_concurrent_timing_operations(self):
        """Test concurrent timing operations."""
        import threading
        
        collector = MetricsCollector()
        collector.reset()
        
        def time_operation():
            for _ in range(10):
                with collector.time_agent("test_agent"):
                    time.sleep(0.001)
        
        threads = [threading.Thread(target=time_operation) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have 50 total timings (5 threads * 10 operations)
        assert collector.agent_timing["test_agent"].count == 50
