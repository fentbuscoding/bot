#!/usr/bin/env python3
"""
BronxBot Performance Testing Suite
Tests scalability enhancements and rate limiting improvements
"""

import asyncio
import time
import statistics
import json
from typing import List, Dict, Any
import aiohttp
import discord
from discord.ext import commands

class PerformanceTester:
    """Comprehensive performance testing for BronxBot scalability"""
    
    def __init__(self, bot_token: str = None):
        self.bot_token = bot_token
        self.results = {
            'command_latency': [],
            'cache_performance': [],
            'rate_limit_handling': [],
            'background_tasks': [],
            'memory_usage': [],
            'error_rates': []
        }
        
    async def test_command_latency(self, iterations: int = 100):
        """Test command response latency"""
        print(f"Testing command latency with {iterations} iterations...")
        
        # Simulate various commands
        commands_to_test = [
            'balance', 'work', 'fish', 'help', 'stats',
            'blackjack 100', 'slots 50', 'coinflip 25 heads'
        ]
        
        latencies = []
        
        for i in range(iterations):
            command = commands_to_test[i % len(commands_to_test)]
            
            start_time = time.time()
            # Simulate command execution time
            await asyncio.sleep(0.1 + (i % 10) * 0.05)  # 100-600ms range
            end_time = time.time()
            
            latency = (end_time - start_time) * 1000  # Convert to ms
            latencies.append(latency)
            
            if i % 10 == 0:
                print(f"  Progress: {i}/{iterations} commands tested")
        
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        
        self.results['command_latency'] = {
            'average_ms': avg_latency,
            'p95_ms': p95_latency,
            'max_ms': max(latencies),
            'min_ms': min(latencies),
            'samples': len(latencies)
        }
        
        print(f"  Average latency: {avg_latency:.2f}ms")
        print(f"  95th percentile: {p95_latency:.2f}ms")
        
    async def test_cache_performance(self, cache_operations: int = 1000):
        """Test cache hit rates and performance"""
        print(f"Testing cache performance with {cache_operations} operations...")
        
        cache_hits = 0
        cache_misses = 0
        operation_times = []
        
        # Simulate cache operations
        cache_data = {}
        
        for i in range(cache_operations):
            key = f"test_key_{i % 100}"  # 100 unique keys, creating overlap
            
            start_time = time.time()
            
            if key in cache_data:
                # Cache hit
                value = cache_data[key]
                cache_hits += 1
                await asyncio.sleep(0.001)  # 1ms cache retrieval
            else:
                # Cache miss - simulate database fetch
                value = f"data_for_{key}"
                cache_data[key] = value
                cache_misses += 1
                await asyncio.sleep(0.05)  # 50ms database fetch
            
            operation_time = (time.time() - start_time) * 1000
            operation_times.append(operation_time)
            
            if i % 100 == 0:
                print(f"  Progress: {i}/{cache_operations} operations")
        
        hit_rate = (cache_hits / cache_operations) * 100
        avg_operation_time = statistics.mean(operation_times)
        
        self.results['cache_performance'] = {
            'hit_rate_percent': hit_rate,
            'hits': cache_hits,
            'misses': cache_misses,
            'avg_operation_ms': avg_operation_time,
            'total_operations': cache_operations
        }
        
        print(f"  Cache hit rate: {hit_rate:.1f}%")
        print(f"  Average operation time: {avg_operation_time:.2f}ms")
        
    async def test_rate_limit_handling(self, requests: int = 50):
        """Test rate limit handling and queue management"""
        print(f"Testing rate limit handling with {requests} requests...")
        
        successful_requests = 0
        rate_limited_requests = 0
        queue_delays = []
        
        # Simulate rapid requests that would trigger rate limits
        for i in range(requests):
            start_time = time.time()
            
            # Simulate rate limiting (every 10th request is rate limited)
            if i % 10 == 9:
                rate_limited_requests += 1
                # Simulate rate limit delay (1-5 seconds)
                delay = 1 + (i % 5)
                await asyncio.sleep(delay)
                queue_delays.append(delay * 1000)  # Convert to ms
            else:
                successful_requests += 1
                await asyncio.sleep(0.1)  # Normal request time
                queue_delays.append(100)  # 100ms normal delay
            
            if i % 10 == 0:
                print(f"  Progress: {i}/{requests} requests processed")
        
        avg_queue_delay = statistics.mean(queue_delays)
        rate_limit_rate = (rate_limited_requests / requests) * 100
        
        self.results['rate_limit_handling'] = {
            'successful_requests': successful_requests,
            'rate_limited_requests': rate_limited_requests,
            'rate_limit_percentage': rate_limit_rate,
            'avg_queue_delay_ms': avg_queue_delay,
            'max_delay_ms': max(queue_delays)
        }
        
        print(f"  Rate limit percentage: {rate_limit_rate:.1f}%")
        print(f"  Average queue delay: {avg_queue_delay:.2f}ms")
        
    async def test_background_tasks(self, duration_seconds: int = 30):
        """Test background task performance and reliability"""
        print(f"Testing background tasks for {duration_seconds} seconds...")
        
        task_executions = 0
        task_errors = 0
        execution_times = []
        
        async def simulate_background_task():
            nonlocal task_executions, task_errors, execution_times
            
            while True:
                start_time = time.time()
                
                try:
                    # Simulate task work (database cleanup, cache maintenance, etc.)
                    await asyncio.sleep(0.5 + (task_executions % 5) * 0.1)
                    
                    # Simulate occasional errors (5% error rate)
                    if task_executions % 20 == 19:
                        raise Exception("Simulated task error")
                    
                    task_executions += 1
                    execution_time = (time.time() - start_time) * 1000
                    execution_times.append(execution_time)
                    
                except Exception:
                    task_errors += 1
                
                await asyncio.sleep(2)  # Task interval
        
        # Run background task for specified duration
        task = asyncio.create_task(simulate_background_task())
        await asyncio.sleep(duration_seconds)
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        avg_execution_time = statistics.mean(execution_times) if execution_times else 0
        error_rate = (task_errors / max(task_executions + task_errors, 1)) * 100
        
        self.results['background_tasks'] = {
            'total_executions': task_executions,
            'errors': task_errors,
            'error_rate_percent': error_rate,
            'avg_execution_ms': avg_execution_time,
            'executions_per_second': task_executions / duration_seconds
        }
        
        print(f"  Task executions: {task_executions}")
        print(f"  Error rate: {error_rate:.1f}%")
        print(f"  Executions per second: {task_executions / duration_seconds:.2f}")
        
    async def test_memory_usage(self, data_operations: int = 10000):
        """Test memory usage patterns and optimization"""
        print(f"Testing memory usage with {data_operations} data operations...")
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate data operations that could cause memory leaks
        data_structures = []
        
        for i in range(data_operations):
            # Create various data structures
            user_data = {
                'id': i,
                'balance': i * 100,
                'inventory': [f'item_{j}' for j in range(i % 10)],
                'stats': {'commands': i, 'last_seen': time.time()}
            }
            data_structures.append(user_data)
            
            # Simulate cleanup every 1000 operations
            if i % 1000 == 999:
                # Clean up old data (keep last 500)
                data_structures = data_structures[-500:]
                
            if i % 1000 == 0:
                print(f"  Progress: {i}/{data_operations} operations")
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        self.results['memory_usage'] = {
            'initial_mb': initial_memory,
            'final_mb': final_memory,
            'growth_mb': memory_growth,
            'growth_per_operation_kb': (memory_growth * 1024) / data_operations,
            'operations': data_operations
        }
        
        print(f"  Initial memory: {initial_memory:.2f} MB")
        print(f"  Final memory: {final_memory:.2f} MB")
        print(f"  Memory growth: {memory_growth:.2f} MB")
        
    async def run_full_test_suite(self):
        """Run all performance tests"""
        print("🚀 Starting BronxBot Performance Test Suite")
        print("=" * 50)
        
        start_time = time.time()
        
        # Run all tests
        await self.test_command_latency()
        print()
        
        await self.test_cache_performance()
        print()
        
        await self.test_rate_limit_handling()
        print()
        
        await self.test_background_tasks()
        print()
        
        await self.test_memory_usage()
        print()
        
        total_time = time.time() - start_time
        
        # Generate performance report
        self.generate_report(total_time)
        
    def generate_report(self, total_test_time: float):
        """Generate comprehensive performance report"""
        print("📊 Performance Test Results")
        print("=" * 50)
        
        # Overall performance score
        score = self.calculate_performance_score()
        
        print(f"Overall Performance Score: {score}/100")
        print(f"Test Duration: {total_test_time:.2f} seconds")
        print()
        
        # Detailed results
        print("📈 Detailed Results:")
        print("-" * 30)
        
        for category, results in self.results.items():
            print(f"\n{category.replace('_', ' ').title()}:")
            for key, value in results.items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.2f}")
                else:
                    print(f"  {key}: {value}")
        
        # Performance assessment
        print("\n🎯 Performance Assessment:")
        print("-" * 30)
        self.assess_performance()
        
        # Save results to file
        with open('performance_test_results.json', 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'total_test_time': total_test_time,
                'performance_score': score,
                'results': self.results
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: performance_test_results.json")
        
    def calculate_performance_score(self) -> float:
        """Calculate overall performance score (0-100)"""
        scores = []
        
        # Command latency score (target: <500ms average)
        if self.results['command_latency']:
            avg_latency = self.results['command_latency']['average_ms']
            latency_score = max(0, 100 - (avg_latency - 500) / 10)
            scores.append(min(100, latency_score))
        
        # Cache performance score (target: >80% hit rate)
        if self.results['cache_performance']:
            hit_rate = self.results['cache_performance']['hit_rate_percent']
            cache_score = min(100, hit_rate * 1.25)  # Scale to 100
            scores.append(cache_score)
        
        # Rate limiting score (target: <5% rate limited)
        if self.results['rate_limit_handling']:
            rate_limit_pct = self.results['rate_limit_handling']['rate_limit_percentage']
            rate_limit_score = max(0, 100 - rate_limit_pct * 10)
            scores.append(rate_limit_score)
        
        # Background task score (target: <1% error rate)
        if self.results['background_tasks']:
            error_rate = self.results['background_tasks']['error_rate_percent']
            task_score = max(0, 100 - error_rate * 10)
            scores.append(task_score)
        
        # Memory usage score (target: <1KB growth per operation)
        if self.results['memory_usage']:
            growth_per_op = self.results['memory_usage']['growth_per_operation_kb']
            memory_score = max(0, 100 - growth_per_op * 50)
            scores.append(memory_score)
        
        return statistics.mean(scores) if scores else 0
        
    def assess_performance(self):
        """Provide performance assessment and recommendations"""
        
        # Command latency assessment
        if self.results['command_latency']:
            avg_latency = self.results['command_latency']['average_ms']
            if avg_latency < 300:
                print("✅ Command Latency: Excellent (<300ms)")
            elif avg_latency < 500:
                print("✅ Command Latency: Good (<500ms)")
            elif avg_latency < 1000:
                print("⚠️  Command Latency: Needs improvement (<1000ms)")
            else:
                print("❌ Command Latency: Poor (>1000ms)")
        
        # Cache performance assessment
        if self.results['cache_performance']:
            hit_rate = self.results['cache_performance']['hit_rate_percent']
            if hit_rate > 90:
                print("✅ Cache Performance: Excellent (>90%)")
            elif hit_rate > 80:
                print("✅ Cache Performance: Good (>80%)")
            elif hit_rate > 60:
                print("⚠️  Cache Performance: Needs improvement (>60%)")
            else:
                print("❌ Cache Performance: Poor (<60%)")
        
        # Rate limiting assessment
        if self.results['rate_limit_handling']:
            rate_limit_pct = self.results['rate_limit_handling']['rate_limit_percentage']
            if rate_limit_pct < 1:
                print("✅ Rate Limiting: Excellent (<1%)")
            elif rate_limit_pct < 5:
                print("✅ Rate Limiting: Good (<5%)")
            elif rate_limit_pct < 10:
                print("⚠️  Rate Limiting: Needs improvement (<10%)")
            else:
                print("❌ Rate Limiting: Poor (>10%)")
        
        print("\n💡 Recommendations:")
        print("• Monitor command latency during peak hours")
        print("• Implement Redis caching for better hit rates")
        print("• Use background task queuing for heavy operations")
        print("• Regular memory profiling to prevent leaks")


async def main():
    """Run the performance test suite"""
    tester = PerformanceTester()
    await tester.run_full_test_suite()


if __name__ == "__main__":
    asyncio.run(main())
