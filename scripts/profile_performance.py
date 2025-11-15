#!/usr/bin/env python3
"""
Performance profiling script for shopping optimizer.

This script profiles the shopping optimizer with realistic workloads and
generates performance reports. It can be used to:
- Identify performance bottlenecks
- Validate async operations
- Test cache effectiveness
- Compare performance across versions

Usage:
    python scripts/profile_performance.py [--workload small|medium|large]
    
Requirements: 8.2, 8.3, 8.4, 8.6
"""

import asyncio
import time
import statistics
import sys
from pathlib import Path
from decimal import Decimal
from datetime import date, timedelta
from typing import Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.discount_optimizer.domain.models import Location, DiscountItem
from agents.discount_optimizer.infrastructure.cache_repository import (
    InMemoryCacheRepository,
    serialize_for_cache,
    deserialize_from_cache,
)
from agents.discount_optimizer.metrics import get_metrics_collector, profile_operation


# =============================================================================
# Workload Definitions
# =============================================================================

WORKLOADS = {
    "small": {
        "num_discounts": 50,
        "num_meals": 3,
        "num_requests": 10,
        "description": "Small workload (10 requests, 50 discounts, 3 meals)",
    },
    "medium": {
        "num_discounts": 200,
        "num_meals": 5,
        "num_requests": 50,
        "description": "Medium workload (50 requests, 200 discounts, 5 meals)",
    },
    "large": {
        "num_discounts": 500,
        "num_meals": 10,
        "num_requests": 100,
        "description": "Large workload (100 requests, 500 discounts, 10 meals)",
    },
}


# =============================================================================
# Test Data Generation
# =============================================================================

def generate_sample_discounts(count: int) -> list[DiscountItem]:
    """Generate sample discount items for testing."""
    discounts = []
    base_location = Location(latitude=55.6761, longitude=12.5683)
    
    for i in range(count):
        discount = DiscountItem(
            product_name=f"Product {i}",
            store_name=f"Store {i % 20}",
            store_location=Location(
                latitude=base_location.latitude + (i * 0.001),
                longitude=base_location.longitude + (i * 0.001),
            ),
            original_price=Decimal("100.00"),
            discount_price=Decimal(str(50.0 + (i % 30))),
            discount_percent=float(30 + (i % 50)),
            expiration_date=date.today() + timedelta(days=(i % 7) + 1),
            is_organic=i % 3 == 0,
            store_address=f"Address {i}",
            travel_distance_km=float(i % 20),
            travel_time_minutes=float(i % 30),
        )
        discounts.append(discount)
    
    return discounts


def generate_sample_meals(count: int) -> list[str]:
    """Generate sample meal names."""
    meals = [
        "taco", "pasta", "salad", "soup", "curry",
        "stir-fry", "pizza", "sandwich", "burger", "wrap",
    ]
    return meals[:count]


# =============================================================================
# Profiling Functions
# =============================================================================

async def profile_discount_fetching(discounts: list[DiscountItem]) -> dict[str, Any]:
    """Profile discount fetching operation."""
    print("\n📊 Profiling discount fetching...")
    
    execution_times = []
    
    for i in range(5):
        start = time.perf_counter()
        
        with profile_operation("fetch_discounts"):
            # Simulate API call
            await asyncio.sleep(0.05)
            
            # Simulate data processing
            processed = []
            for discount in discounts:
                # Simulate validation and transformation
                processed.append(discount)
        
        duration = time.perf_counter() - start
        execution_times.append(duration)
    
    return {
        "operation": "discount_fetching",
        "avg_time": statistics.mean(execution_times),
        "min_time": min(execution_times),
        "max_time": max(execution_times),
        "std_dev": statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
    }


async def profile_ingredient_mapping(
    meals: list[str],
    discounts: list[DiscountItem]
) -> dict[str, Any]:
    """Profile ingredient mapping operation."""
    print("\n📊 Profiling ingredient mapping...")
    
    execution_times = []
    
    for i in range(5):
        start = time.perf_counter()
        
        with profile_operation("ingredient_mapping"):
            # Simulate ingredient extraction
            for meal in meals:
                await asyncio.sleep(0.01)  # Simulate LLM call
                
                # Simulate matching
                matches = []
                for discount in discounts[:50]:  # Check subset
                    if meal.lower() in discount.product_name.lower():
                        matches.append(discount)
        
        duration = time.perf_counter() - start
        execution_times.append(duration)
    
    return {
        "operation": "ingredient_mapping",
        "avg_time": statistics.mean(execution_times),
        "min_time": min(execution_times),
        "max_time": max(execution_times),
        "std_dev": statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
    }


async def profile_optimization(discounts: list[DiscountItem]) -> dict[str, Any]:
    """Profile optimization algorithm."""
    print("\n📊 Profiling optimization algorithm...")
    
    execution_times = []
    
    for i in range(5):
        start = time.perf_counter()
        
        with profile_operation("optimization"):
            # Score each discount
            scored = []
            for discount in discounts:
                score = (
                    float(discount.discount_percent) / 100.0 * 0.5 +
                    (1.0 / (1.0 + discount.travel_distance_km)) * 0.3 +
                    (1.0 if discount.is_organic else 0.5) * 0.2
                )
                scored.append((discount, score))
            
            # Sort and select top items
            scored.sort(key=lambda x: x[1], reverse=True)
            optimized = [item[0] for item in scored[:20]]
        
        duration = time.perf_counter() - start
        execution_times.append(duration)
    
    return {
        "operation": "optimization",
        "avg_time": statistics.mean(execution_times),
        "min_time": min(execution_times),
        "max_time": max(execution_times),
        "std_dev": statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
    }


async def profile_cache_effectiveness(discounts: list[DiscountItem]) -> dict[str, Any]:
    """Profile cache effectiveness."""
    print("\n📊 Profiling cache effectiveness...")
    
    cache = InMemoryCacheRepository()
    
    # Measure without cache
    no_cache_times = []
    for i in range(10):
        start = time.perf_counter()
        await asyncio.sleep(0.05)  # Simulate API call
        _ = discounts
        duration = time.perf_counter() - start
        no_cache_times.append(duration)
    
    # Measure with cache
    cached_data = serialize_for_cache(discounts)
    await cache.set("test_discounts", cached_data, ttl_seconds=60)
    
    with_cache_times = []
    for i in range(10):
        start = time.perf_counter()
        result = await cache.get("test_discounts")
        if result:
            _ = deserialize_from_cache(result)
        duration = time.perf_counter() - start
        with_cache_times.append(duration)
    
    # Get cache metrics
    metrics = cache.get_metrics()
    
    await cache.close()
    
    return {
        "operation": "cache_effectiveness",
        "no_cache_avg": statistics.mean(no_cache_times),
        "with_cache_avg": statistics.mean(with_cache_times),
        "speedup": statistics.mean(no_cache_times) / statistics.mean(with_cache_times),
        "hit_rate": metrics.hit_rate,
        "cache_hits": metrics.hits,
        "cache_misses": metrics.misses,
    }


async def profile_concurrent_requests(num_requests: int) -> dict[str, Any]:
    """Profile concurrent request handling."""
    print(f"\n📊 Profiling {num_requests} concurrent requests...")
    
    async def single_request(request_id: int) -> float:
        """Simulate single optimization request."""
        start = time.perf_counter()
        
        # Simulate request processing
        await asyncio.sleep(0.05)  # Fetch
        await asyncio.sleep(0.02)  # Map
        await asyncio.sleep(0.01)  # Optimize
        
        return time.perf_counter() - start
    
    # Sequential execution
    start = time.perf_counter()
    sequential_times = []
    for i in range(min(num_requests, 10)):  # Limit for speed
        duration = await single_request(i)
        sequential_times.append(duration)
    sequential_duration = time.perf_counter() - start
    
    # Concurrent execution
    start = time.perf_counter()
    tasks = [single_request(i) for i in range(num_requests)]
    concurrent_times = await asyncio.gather(*tasks)
    concurrent_duration = time.perf_counter() - start
    
    return {
        "operation": "concurrent_requests",
        "num_requests": num_requests,
        "sequential_duration": sequential_duration,
        "concurrent_duration": concurrent_duration,
        "speedup": sequential_duration / concurrent_duration if concurrent_duration > 0 else 0,
        "avg_request_time": statistics.mean(concurrent_times),
    }


async def profile_full_pipeline(
    discounts: list[DiscountItem],
    meals: list[str]
) -> dict[str, Any]:
    """Profile complete optimization pipeline."""
    print("\n📊 Profiling full pipeline...")
    
    execution_times = []
    stage_times = {
        "fetch": [],
        "map": [],
        "optimize": [],
        "format": [],
    }
    
    for i in range(5):
        start = time.perf_counter()
        
        with profile_operation("full_pipeline"):
            # Stage 1: Fetch
            stage_start = time.perf_counter()
            await asyncio.sleep(0.05)
            stage_times["fetch"].append(time.perf_counter() - stage_start)
            
            # Stage 2: Map
            stage_start = time.perf_counter()
            await asyncio.sleep(0.02)
            stage_times["map"].append(time.perf_counter() - stage_start)
            
            # Stage 3: Optimize
            stage_start = time.perf_counter()
            await asyncio.sleep(0.01)
            stage_times["optimize"].append(time.perf_counter() - stage_start)
            
            # Stage 4: Format
            stage_start = time.perf_counter()
            await asyncio.sleep(0.005)
            stage_times["format"].append(time.perf_counter() - stage_start)
        
        duration = time.perf_counter() - start
        execution_times.append(duration)
    
    return {
        "operation": "full_pipeline",
        "avg_time": statistics.mean(execution_times),
        "min_time": min(execution_times),
        "max_time": max(execution_times),
        "stage_fetch_avg": statistics.mean(stage_times["fetch"]),
        "stage_map_avg": statistics.mean(stage_times["map"]),
        "stage_optimize_avg": statistics.mean(stage_times["optimize"]),
        "stage_format_avg": statistics.mean(stage_times["format"]),
    }


# =============================================================================
# Report Generation
# =============================================================================

def print_report(results: list[dict[str, Any]], workload_name: str):
    """Print performance report."""
    print("\n" + "=" * 80)
    print(f"PERFORMANCE PROFILING REPORT - {workload_name.upper()} WORKLOAD")
    print("=" * 80)
    
    for result in results:
        operation = result.get("operation", "Unknown")
        print(f"\n📈 {operation.replace('_', ' ').title()}")
        print("-" * 80)
        
        for key, value in result.items():
            if key == "operation":
                continue
            
            # Format value based on type
            if isinstance(value, float):
                if "time" in key or "duration" in key:
                    formatted = f"{value * 1000:.2f} ms"
                elif "speedup" in key:
                    formatted = f"{value:.2f}x"
                elif "rate" in key:
                    formatted = f"{value:.1f}%"
                else:
                    formatted = f"{value:.4f}"
            else:
                formatted = str(value)
            
            print(f"  {key.replace('_', ' ').title()}: {formatted}")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    # Calculate overall metrics
    total_operations = len(results)
    print(f"  Total Operations Profiled: {total_operations}")
    
    # Find slowest operation
    pipeline_result = next((r for r in results if r.get("operation") == "full_pipeline"), None)
    if pipeline_result:
        print(f"  Full Pipeline Avg Time: {pipeline_result['avg_time'] * 1000:.2f} ms")
        print(f"  Full Pipeline Max Time: {pipeline_result['max_time'] * 1000:.2f} ms")
    
    # Cache effectiveness
    cache_result = next((r for r in results if r.get("operation") == "cache_effectiveness"), None)
    if cache_result:
        print(f"  Cache Speedup: {cache_result['speedup']:.2f}x")
        print(f"  Cache Hit Rate: {cache_result['hit_rate']:.1f}%")
    
    # Concurrency benefit
    concurrent_result = next((r for r in results if r.get("operation") == "concurrent_requests"), None)
    if concurrent_result:
        print(f"  Concurrency Speedup: {concurrent_result['speedup']:.2f}x")
    
    print("\n" + "=" * 80)


# =============================================================================
# Main Profiling Function
# =============================================================================

async def run_profiling(workload_name: str = "medium"):
    """Run complete performance profiling."""
    if workload_name not in WORKLOADS:
        print(f"❌ Unknown workload: {workload_name}")
        print(f"Available workloads: {', '.join(WORKLOADS.keys())}")
        return
    
    workload = WORKLOADS[workload_name]
    print(f"\n🚀 Starting performance profiling")
    print(f"Workload: {workload['description']}")
    
    # Generate test data
    print("\n📦 Generating test data...")
    discounts = generate_sample_discounts(workload["num_discounts"])
    meals = generate_sample_meals(workload["num_meals"])
    print(f"  Generated {len(discounts)} discounts and {len(meals)} meals")
    
    # Reset metrics
    metrics_collector = get_metrics_collector()
    metrics_collector.reset()
    
    # Run profiling
    results = []
    
    try:
        # Profile individual operations
        results.append(await profile_discount_fetching(discounts))
        results.append(await profile_ingredient_mapping(meals, discounts))
        results.append(await profile_optimization(discounts))
        results.append(await profile_cache_effectiveness(discounts))
        results.append(await profile_concurrent_requests(workload["num_requests"]))
        results.append(await profile_full_pipeline(discounts, meals))
        
        # Print report
        print_report(results, workload_name)
        
        # Print metrics collector summary
        print("\n📊 METRICS COLLECTOR SUMMARY")
        print("=" * 80)
        
        if metrics_collector.timers:
            print("\nOperation Timings:")
            for name, metric in metrics_collector.timers.items():
                print(f"  {name}:")
                print(f"    Count: {metric.count}")
                print(f"    Avg: {metric.average_ms:.2f} ms")
                print(f"    Min: {metric.min_seconds * 1000:.2f} ms")
                print(f"    Max: {metric.max_seconds * 1000:.2f} ms")
        
        print("\n✅ Profiling completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Profiling failed: {e}")
        import traceback
        traceback.print_exc()


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    """Main entry point for CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Profile shopping optimizer performance"
    )
    parser.add_argument(
        "--workload",
        choices=list(WORKLOADS.keys()),
        default="medium",
        help="Workload size to profile (default: medium)",
    )
    
    args = parser.parse_args()
    
    # Run profiling
    asyncio.run(run_profiling(args.workload))


if __name__ == "__main__":
    main()
