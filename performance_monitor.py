#!/usr/bin/env python3
"""
Performance monitoring and optimization script for AI Knowledge Mapper demo.
Monitors system performance, provides optimization recommendations, and validates demo readiness.
"""

import asyncio
import aiohttp
import psutil
import time
import json
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot."""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_available_gb: float
    disk_usage_percent: float
    network_latency_ms: Optional[float]
    backend_response_time_ms: Optional[float]
    graph_node_count: int
    graph_edge_count: int
    
class PerformanceMonitor:
    """Monitors system and application performance for demo readiness."""
    
    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url
        self.session = None
        self.metrics_history: List[PerformanceMetrics] = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def measure_network_latency(self) -> Optional[float]:
        """Measure network latency to backend."""
        try:
            start_time = time.time()
            async with self.session.head(f"{self.backend_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                latency_ms = (time.time() - start_time) * 1000
                return latency_ms if response.status == 200 else None
        except Exception:
            return None
    
    async def measure_backend_response_time(self) -> Optional[float]:
        """Measure backend API response time."""
        try:
            start_time = time.time()
            async with self.session.get(f"{self.backend_url}/health", timeout=aiohttp.ClientTimeout(total=10)) as response:
                response_time_ms = (time.time() - start_time) * 1000
                return response_time_ms if response.status == 200 else None
        except Exception:
            return None
    
    async def get_graph_stats(self) -> tuple[int, int]:
        """Get current graph node and edge counts."""
        try:
            async with self.session.get(f"{self.backend_url}/graph/export", timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    data = await response.json()
                    return len(data.get('nodes', [])), len(data.get('edges', []))
        except Exception:
            pass
        return 0, 0
    
    async def collect_metrics(self) -> PerformanceMetrics:
        """Collect comprehensive performance metrics."""
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Network and backend metrics
        network_latency = await self.measure_network_latency()
        backend_response_time = await self.measure_backend_response_time()
        
        # Graph metrics
        node_count, edge_count = await self.get_graph_stats()
        
        metrics = PerformanceMetrics(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_available_gb=memory.available / (1024**3),
            disk_usage_percent=disk.percent,
            network_latency_ms=network_latency,
            backend_response_time_ms=backend_response_time,
            graph_node_count=node_count,
            graph_edge_count=edge_count
        )
        
        self.metrics_history.append(metrics)
        return metrics
    
    def analyze_performance(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """Analyze performance metrics and provide recommendations."""
        analysis = {
            "overall_status": "good",
            "issues": [],
            "recommendations": [],
            "demo_readiness": True
        }
        
        # CPU analysis
        if metrics.cpu_percent > 80:
            analysis["issues"].append(f"High CPU usage: {metrics.cpu_percent:.1f}%")
            analysis["recommendations"].append("Close unnecessary applications")
            analysis["overall_status"] = "warning"
        
        # Memory analysis
        if metrics.memory_percent > 85:
            analysis["issues"].append(f"High memory usage: {metrics.memory_percent:.1f}%")
            analysis["recommendations"].append("Free up memory or restart system")
            analysis["overall_status"] = "critical"
            analysis["demo_readiness"] = False
        elif metrics.memory_available_gb < 2:
            analysis["issues"].append(f"Low available memory: {metrics.memory_available_gb:.1f}GB")
            analysis["recommendations"].append("Close memory-intensive applications")
            analysis["overall_status"] = "warning"
        
        # Disk analysis
        if metrics.disk_usage_percent > 90:
            analysis["issues"].append(f"High disk usage: {metrics.disk_usage_percent:.1f}%")
            analysis["recommendations"].append("Free up disk space")
            analysis["overall_status"] = "warning"
        
        # Network analysis
        if metrics.network_latency_ms is None:
            analysis["issues"].append("Backend not accessible")
            analysis["recommendations"].append("Check if backend is running: docker-compose up -d")
            analysis["overall_status"] = "critical"
            analysis["demo_readiness"] = False
        elif metrics.network_latency_ms > 1000:
            analysis["issues"].append(f"High network latency: {metrics.network_latency_ms:.0f}ms")
            analysis["recommendations"].append("Check network connection or use offline mode")
            analysis["overall_status"] = "warning"
        
        # Backend response time analysis
        if metrics.backend_response_time_ms is None:
            analysis["issues"].append("Backend not responding")
            analysis["recommendations"].append("Restart backend services")
            analysis["overall_status"] = "critical"
            analysis["demo_readiness"] = False
        elif metrics.backend_response_time_ms > 5000:
            analysis["issues"].append(f"Slow backend response: {metrics.backend_response_time_ms:.0f}ms")
            analysis["recommendations"].append("Check backend logs for issues")
            analysis["overall_status"] = "warning"
        
        # Graph size analysis
        total_elements = metrics.graph_node_count + metrics.graph_edge_count
        if total_elements > 1000:
            analysis["issues"].append(f"Large graph may impact performance: {total_elements} elements")
            analysis["recommendations"].append("Consider using smaller demo dataset")
            analysis["overall_status"] = "warning"
        elif total_elements == 0:
            analysis["issues"].append("No graph data loaded")
            analysis["recommendations"].append("Load demo data: python demo_seed_data.py --scenario <name>")
            analysis["overall_status"] = "warning"
        
        return analysis
    
    def print_metrics(self, metrics: PerformanceMetrics, analysis: Dict[str, Any]):
        """Print formatted performance metrics and analysis."""
        print("\n" + "="*60)
        print("🔍 AI KNOWLEDGE MAPPER - PERFORMANCE REPORT")
        print("="*60)
        
        # System metrics
        print(f"\n💻 System Performance:")
        print(f"   CPU Usage:      {metrics.cpu_percent:6.1f}%")
        print(f"   Memory Usage:   {metrics.memory_percent:6.1f}% ({metrics.memory_available_gb:.1f}GB available)")
        print(f"   Disk Usage:     {metrics.disk_usage_percent:6.1f}%")
        
        # Network metrics
        print(f"\n🌐 Network Performance:")
        if metrics.network_latency_ms is not None:
            print(f"   Network Latency: {metrics.network_latency_ms:6.0f}ms")
        else:
            print(f"   Network Latency: {'N/A':>6}")
        
        if metrics.backend_response_time_ms is not None:
            print(f"   Backend Response: {metrics.backend_response_time_ms:5.0f}ms")
        else:
            print(f"   Backend Response: {'N/A':>5}")
        
        # Graph metrics
        print(f"\n📊 Graph Data:")
        print(f"   Nodes:          {metrics.graph_node_count:6d}")
        print(f"   Edges:          {metrics.graph_edge_count:6d}")
        print(f"   Total Elements: {metrics.graph_node_count + metrics.graph_edge_count:6d}")
        
        # Analysis
        status_emoji = {
            "good": "✅",
            "warning": "⚠️",
            "critical": "❌"
        }
        
        print(f"\n{status_emoji[analysis['overall_status']]} Overall Status: {analysis['overall_status'].upper()}")
        print(f"🎯 Demo Ready: {'YES' if analysis['demo_readiness'] else 'NO'}")
        
        if analysis["issues"]:
            print(f"\n⚠️  Issues Detected:")
            for issue in analysis["issues"]:
                print(f"   • {issue}")
        
        if analysis["recommendations"]:
            print(f"\n💡 Recommendations:")
            for rec in analysis["recommendations"]:
                print(f"   • {rec}")
        
        print("\n" + "="*60)
    
    async def continuous_monitoring(self, duration_minutes: int = 5, interval_seconds: int = 30):
        """Run continuous performance monitoring."""
        print(f"🔄 Starting continuous monitoring for {duration_minutes} minutes...")
        print(f"📊 Collecting metrics every {interval_seconds} seconds")
        
        end_time = time.time() + (duration_minutes * 60)
        
        while time.time() < end_time:
            metrics = await self.collect_metrics()
            analysis = self.analyze_performance(metrics)
            
            # Print abbreviated status
            status_emoji = {"good": "✅", "warning": "⚠️", "critical": "❌"}
            print(f"{status_emoji[analysis['overall_status']]} {time.strftime('%H:%M:%S')} - "
                  f"CPU: {metrics.cpu_percent:.1f}% | "
                  f"MEM: {metrics.memory_percent:.1f}% | "
                  f"NET: {metrics.network_latency_ms or 0:.0f}ms | "
                  f"GRAPH: {metrics.graph_node_count}N/{metrics.graph_edge_count}E")
            
            if analysis["overall_status"] == "critical":
                print("❌ CRITICAL ISSUES DETECTED - Demo not recommended!")
                break
            
            await asyncio.sleep(interval_seconds)
        
        # Final summary
        if self.metrics_history:
            await self.generate_summary_report()
    
    async def generate_summary_report(self):
        """Generate summary report from metrics history."""
        if not self.metrics_history:
            return
        
        print("\n" + "="*60)
        print("📈 MONITORING SUMMARY REPORT")
        print("="*60)
        
        # Calculate averages
        avg_cpu = sum(m.cpu_percent for m in self.metrics_history) / len(self.metrics_history)
        avg_memory = sum(m.memory_percent for m in self.metrics_history) / len(self.metrics_history)
        
        valid_latencies = [m.network_latency_ms for m in self.metrics_history if m.network_latency_ms is not None]
        avg_latency = sum(valid_latencies) / len(valid_latencies) if valid_latencies else 0
        
        print(f"\n📊 Average Performance:")
        print(f"   CPU Usage:      {avg_cpu:6.1f}%")
        print(f"   Memory Usage:   {avg_memory:6.1f}%")
        print(f"   Network Latency: {avg_latency:5.0f}ms")
        
        # Stability analysis
        cpu_variance = max(m.cpu_percent for m in self.metrics_history) - min(m.cpu_percent for m in self.metrics_history)
        memory_variance = max(m.memory_percent for m in self.metrics_history) - min(m.memory_percent for m in self.metrics_history)
        
        print(f"\n📈 Stability Analysis:")
        print(f"   CPU Variance:   {cpu_variance:6.1f}%")
        print(f"   Memory Variance: {memory_variance:5.1f}%")
        
        # Save detailed report
        report_file = Path(f"performance_report_{int(time.time())}.json")
        report_data = {
            "summary": {
                "avg_cpu": avg_cpu,
                "avg_memory": avg_memory,
                "avg_latency": avg_latency,
                "cpu_variance": cpu_variance,
                "memory_variance": memory_variance,
                "sample_count": len(self.metrics_history)
            },
            "metrics": [
                {
                    "timestamp": m.timestamp,
                    "cpu_percent": m.cpu_percent,
                    "memory_percent": m.memory_percent,
                    "network_latency_ms": m.network_latency_ms,
                    "graph_elements": m.graph_node_count + m.graph_edge_count
                }
                for m in self.metrics_history
            ]
        }
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n💾 Detailed report saved to: {report_file}")

async def run_demo_validation():
    """Run comprehensive demo validation checks."""
    print("🎯 AI KNOWLEDGE MAPPER - DEMO VALIDATION")
    print("="*50)
    
    async with PerformanceMonitor() as monitor:
        # Collect current metrics
        metrics = await monitor.collect_metrics()
        analysis = monitor.analyze_performance(metrics)
        
        # Print detailed report
        monitor.print_metrics(metrics, analysis)
        
        # Demo-specific checks
        print("\n🎬 Demo-Specific Validation:")
        
        # Check if demo data is loaded
        if metrics.graph_node_count == 0:
            print("   ❌ No demo data loaded")
            print("   💡 Run: python demo_seed_data.py --scenario ai_research")
        else:
            print(f"   ✅ Demo data loaded ({metrics.graph_node_count} nodes)")
        
        # Check browser requirements
        print("   ℹ️  Browser Requirements:")
        print("      • Chrome or Firefox (latest version)")
        print("      • JavaScript enabled")
        print("      • WebSocket support")
        print("      • Minimum 1920x1080 resolution")
        
        # Check network requirements
        if metrics.network_latency_ms and metrics.network_latency_ms < 100:
            print("   ✅ Network performance suitable for live demo")
        elif metrics.network_latency_ms and metrics.network_latency_ms < 500:
            print("   ⚠️  Network performance acceptable but consider offline backup")
        else:
            print("   ❌ Network performance poor - use offline mode")
        
        return analysis["demo_readiness"]

async def main():
    """Main performance monitoring function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor AI Knowledge Mapper performance")
    parser.add_argument("--validate", "-v", action="store_true", help="Run demo validation")
    parser.add_argument("--monitor", "-m", type=int, default=0, help="Continuous monitoring duration (minutes)")
    parser.add_argument("--interval", "-i", type=int, default=30, help="Monitoring interval (seconds)")
    parser.add_argument("--url", "-u", default="http://localhost:8000", help="Backend URL")
    
    args = parser.parse_args()
    
    if args.validate:
        demo_ready = await run_demo_validation()
        sys.exit(0 if demo_ready else 1)
    
    elif args.monitor > 0:
        async with PerformanceMonitor(args.url) as monitor:
            await monitor.continuous_monitoring(args.monitor, args.interval)
    
    else:
        # Single snapshot
        async with PerformanceMonitor(args.url) as monitor:
            metrics = await monitor.collect_metrics()
            analysis = monitor.analyze_performance(metrics)
            monitor.print_metrics(metrics, analysis)

if __name__ == "__main__":
    asyncio.run(main())