"""
Health monitoring system for the AI Knowledge Mapper backend.

This module provides:
- Service health checks
- System resource monitoring
- Performance metrics collection
- Alert generation for critical issues
"""

import asyncio
import logging
import time
import psutil
import os
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from utils.error_handling import error_handler, ErrorSeverity

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class HealthCheck:
    """Individual health check configuration"""
    name: str
    check_function: Callable
    interval_seconds: float = 60.0
    timeout_seconds: float = 10.0
    critical: bool = False
    enabled: bool = True
    last_check: Optional[datetime] = None
    last_status: HealthStatus = HealthStatus.HEALTHY
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    max_failures: int = 3


@dataclass
class SystemMetrics:
    """System resource metrics"""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_available_mb: float = 0.0
    disk_usage_percent: float = 0.0
    disk_free_gb: float = 0.0
    process_count: int = 0
    open_files: int = 0
    network_connections: int = 0


@dataclass
class ServiceHealth:
    """Health status for a service"""
    name: str
    status: HealthStatus
    last_check: datetime
    response_time_ms: float = 0.0
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


class HealthMonitor:
    """Comprehensive health monitoring system"""
    
    def __init__(self):
        self.health_checks: Dict[str, HealthCheck] = {}
        self.system_metrics_history: List[SystemMetrics] = []
        self.service_health: Dict[str, ServiceHealth] = {}
        self.max_history_size = 1440  # 24 hours of minute-by-minute data
        self.monitoring_task: Optional[asyncio.Task] = None
        self.running = False
        
        # Thresholds for alerts
        self.cpu_threshold = 80.0
        self.memory_threshold = 85.0
        self.disk_threshold = 90.0
        self.response_time_threshold = 5000.0  # 5 seconds
        
    def register_health_check(
        self,
        name: str,
        check_function: Callable,
        interval_seconds: float = 60.0,
        timeout_seconds: float = 10.0,
        critical: bool = False
    ):
        """Register a new health check"""
        self.health_checks[name] = HealthCheck(
            name=name,
            check_function=check_function,
            interval_seconds=interval_seconds,
            timeout_seconds=timeout_seconds,
            critical=critical
        )
        logger.info(f"Registered health check: {name}")
    
    async def run_health_check(self, check: HealthCheck) -> ServiceHealth:
        """Run a single health check"""
        start_time = time.time()
        
        try:
            # Run the check with timeout
            result = await asyncio.wait_for(
                check.check_function(),
                timeout=check.timeout_seconds
            )
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Determine status based on result
            if isinstance(result, dict):
                status = HealthStatus(result.get("status", "healthy"))
                details = result.get("details", {})
                error_message = result.get("error")
            elif isinstance(result, bool):
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                details = {}
                error_message = None if result else "Health check returned False"
            else:
                status = HealthStatus.HEALTHY
                details = {"result": str(result)}
                error_message = None
            
            # Update check status
            check.last_check = datetime.utcnow()
            check.last_status = status
            check.last_error = error_message
            
            if status == HealthStatus.HEALTHY:
                check.consecutive_failures = 0
            else:
                check.consecutive_failures += 1
            
            # Create service health record
            service_health = ServiceHealth(
                name=check.name,
                status=status,
                last_check=check.last_check,
                response_time_ms=response_time,
                error_message=error_message,
                details=details
            )
            
            # Log slow responses
            if response_time > self.response_time_threshold:
                logger.warning(
                    f"Health check {check.name} took {response_time:.1f}ms",
                    extra={"health_check": check.name, "response_time_ms": response_time}
                )
            
            return service_health
            
        except asyncio.TimeoutError:
            check.consecutive_failures += 1
            check.last_error = f"Health check timed out after {check.timeout_seconds}s"
            check.last_status = HealthStatus.UNHEALTHY
            
            logger.error(f"Health check {check.name} timed out")
            
            return ServiceHealth(
                name=check.name,
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.utcnow(),
                error_message=check.last_error
            )
            
        except Exception as e:
            check.consecutive_failures += 1
            check.last_error = str(e)
            check.last_status = HealthStatus.UNHEALTHY
            
            logger.error(f"Health check {check.name} failed: {e}")
            
            return ServiceHealth(
                name=check.name,
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.utcnow(),
                error_message=str(e)
            )
    
    def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_mb = memory.available / (1024 * 1024)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / (1024 * 1024 * 1024)
            
            # Process information
            process_count = len(psutil.pids())
            
            # Current process info
            current_process = psutil.Process()
            open_files = len(current_process.open_files())
            network_connections = len(current_process.connections())
            
            return SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_available_mb=memory_available_mb,
                disk_usage_percent=disk_usage_percent,
                disk_free_gb=disk_free_gb,
                process_count=process_count,
                open_files=open_files,
                network_connections=network_connections
            )
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return SystemMetrics()  # Return empty metrics
    
    def check_system_alerts(self, metrics: SystemMetrics):
        """Check system metrics against thresholds and generate alerts"""
        alerts = []
        
        # CPU alert
        if metrics.cpu_percent > self.cpu_threshold:
            alerts.append({
                "type": "high_cpu",
                "severity": "warning" if metrics.cpu_percent < 95 else "critical",
                "message": f"High CPU usage: {metrics.cpu_percent:.1f}%",
                "value": metrics.cpu_percent,
                "threshold": self.cpu_threshold
            })
        
        # Memory alert
        if metrics.memory_percent > self.memory_threshold:
            alerts.append({
                "type": "high_memory",
                "severity": "warning" if metrics.memory_percent < 95 else "critical",
                "message": f"High memory usage: {metrics.memory_percent:.1f}%",
                "value": metrics.memory_percent,
                "threshold": self.memory_threshold
            })
        
        # Disk alert
        if metrics.disk_usage_percent > self.disk_threshold:
            alerts.append({
                "type": "high_disk",
                "severity": "warning" if metrics.disk_usage_percent < 98 else "critical",
                "message": f"High disk usage: {metrics.disk_usage_percent:.1f}%",
                "value": metrics.disk_usage_percent,
                "threshold": self.disk_threshold
            })
        
        # Log alerts
        for alert in alerts:
            level = logging.CRITICAL if alert["severity"] == "critical" else logging.WARNING
            logger.log(level, alert["message"], extra=alert)
    
    async def monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("Health monitoring started")
        
        while self.running:
            try:
                # Collect system metrics
                metrics = self.collect_system_metrics()
                self.system_metrics_history.append(metrics)
                
                # Limit history size
                if len(self.system_metrics_history) > self.max_history_size:
                    self.system_metrics_history = self.system_metrics_history[-self.max_history_size:]
                
                # Check for system alerts
                self.check_system_alerts(metrics)
                
                # Run health checks
                current_time = datetime.utcnow()
                for check in self.health_checks.values():
                    if not check.enabled:
                        continue
                    
                    # Check if it's time to run this check
                    if (check.last_check is None or 
                        (current_time - check.last_check).total_seconds() >= check.interval_seconds):
                        
                        service_health = await self.run_health_check(check)
                        self.service_health[check.name] = service_health
                        
                        # Generate alerts for critical services
                        if (check.critical and 
                            check.consecutive_failures >= check.max_failures and
                            service_health.status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]):
                            
                            logger.critical(
                                f"Critical service {check.name} is unhealthy",
                                extra={
                                    "service": check.name,
                                    "consecutive_failures": check.consecutive_failures,
                                    "error": check.last_error
                                }
                            )
                
                # Sleep for a short interval before next check
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)  # Wait longer on error
    
    async def start_monitoring(self):
        """Start the health monitoring system"""
        if self.running:
            logger.warning("Health monitoring is already running")
            return
        
        self.running = True
        self.monitoring_task = asyncio.create_task(self.monitoring_loop())
        logger.info("Health monitoring system started")
    
    async def stop_monitoring(self):
        """Stop the health monitoring system"""
        if not self.running:
            return
        
        self.running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Health monitoring system stopped")
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        if not self.service_health:
            return {
                "status": "unknown",
                "message": "No health checks have been run yet"
            }
        
        # Determine overall status
        statuses = [service.status for service in self.service_health.values()]
        
        if any(status == HealthStatus.CRITICAL for status in statuses):
            overall_status = HealthStatus.CRITICAL
        elif any(status == HealthStatus.UNHEALTHY for status in statuses):
            overall_status = HealthStatus.UNHEALTHY
        elif any(status == HealthStatus.DEGRADED for status in statuses):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        # Get latest system metrics
        latest_metrics = self.system_metrics_history[-1] if self.system_metrics_history else None
        
        # Count services by status
        status_counts = {}
        for service in self.service_health.values():
            status_counts[service.status.value] = status_counts.get(service.status.value, 0) + 1
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                name: {
                    "status": service.status.value,
                    "last_check": service.last_check.isoformat(),
                    "response_time_ms": service.response_time_ms,
                    "error": service.error_message
                }
                for name, service in self.service_health.items()
            },
            "service_counts": status_counts,
            "system_metrics": {
                "cpu_percent": latest_metrics.cpu_percent if latest_metrics else 0,
                "memory_percent": latest_metrics.memory_percent if latest_metrics else 0,
                "disk_usage_percent": latest_metrics.disk_usage_percent if latest_metrics else 0,
                "timestamp": latest_metrics.timestamp.isoformat() if latest_metrics else None
            },
            "error_statistics": error_handler.get_error_statistics()
        }
    
    def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get system metrics summary for the specified time period"""
        if not self.system_metrics_history:
            return {"error": "No metrics data available"}
        
        # Filter metrics for the specified time period
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_metrics = [
            m for m in self.system_metrics_history
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_metrics:
            return {"error": f"No metrics data available for the last {hours} hours"}
        
        # Calculate statistics
        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_percent for m in recent_metrics]
        disk_values = [m.disk_usage_percent for m in recent_metrics]
        
        return {
            "time_period_hours": hours,
            "data_points": len(recent_metrics),
            "cpu": {
                "current": cpu_values[-1],
                "average": sum(cpu_values) / len(cpu_values),
                "max": max(cpu_values),
                "min": min(cpu_values)
            },
            "memory": {
                "current": memory_values[-1],
                "average": sum(memory_values) / len(memory_values),
                "max": max(memory_values),
                "min": min(memory_values)
            },
            "disk": {
                "current": disk_values[-1],
                "average": sum(disk_values) / len(disk_values),
                "max": max(disk_values),
                "min": min(disk_values)
            }
        }


# Global health monitor instance
health_monitor = HealthMonitor()


# Default health check functions
async def check_memory_usage() -> Dict[str, Any]:
    """Check system memory usage"""
    memory = psutil.virtual_memory()
    status = "healthy"
    
    if memory.percent > 90:
        status = "critical"
    elif memory.percent > 80:
        status = "degraded"
    
    return {
        "status": status,
        "details": {
            "memory_percent": memory.percent,
            "available_mb": memory.available / (1024 * 1024)
        }
    }


async def check_disk_space() -> Dict[str, Any]:
    """Check disk space usage"""
    disk = psutil.disk_usage('/')
    usage_percent = (disk.used / disk.total) * 100
    
    status = "healthy"
    if usage_percent > 95:
        status = "critical"
    elif usage_percent > 85:
        status = "degraded"
    
    return {
        "status": status,
        "details": {
            "usage_percent": usage_percent,
            "free_gb": disk.free / (1024 * 1024 * 1024)
        }
    }


def register_default_health_checks():
    """Register default system health checks"""
    health_monitor.register_health_check(
        "memory_usage",
        check_memory_usage,
        interval_seconds=60,
        critical=True
    )
    
    health_monitor.register_health_check(
        "disk_space",
        check_disk_space,
        interval_seconds=300,  # Check every 5 minutes
        critical=True
    )