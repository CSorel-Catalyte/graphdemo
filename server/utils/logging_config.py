"""
Comprehensive logging configuration for the AI Knowledge Mapper backend.

This module provides:
- Structured logging with JSON formatting
- Multiple log levels and handlers
- Performance monitoring
- Error tracking and alerting
- Request/response logging
"""

import logging
import logging.handlers
import json
import time
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, 'error_id'):
            log_entry['error_id'] = record.error_id
        if hasattr(record, 'category'):
            log_entry['category'] = record.category
        if hasattr(record, 'severity'):
            log_entry['severity'] = record.severity
        if hasattr(record, 'retry_count'):
            log_entry['retry_count'] = record.retry_count
        if hasattr(record, 'processing_time'):
            log_entry['processing_time'] = record.processing_time
        if hasattr(record, 'client_id'):
            log_entry['client_id'] = record.client_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, default=str)


class PerformanceLogger:
    """Logger for performance monitoring"""
    
    def __init__(self, logger_name: str = "performance"):
        self.logger = logging.getLogger(logger_name)
        self.start_times: Dict[str, float] = {}
    
    def start_timer(self, operation_id: str):
        """Start timing an operation"""
        self.start_times[operation_id] = time.time()
    
    def end_timer(self, operation_id: str, context: Optional[Dict[str, Any]] = None):
        """End timing and log the duration"""
        if operation_id not in self.start_times:
            self.logger.warning(f"Timer {operation_id} was not started")
            return
        
        duration = time.time() - self.start_times[operation_id]
        del self.start_times[operation_id]
        
        log_context = context or {}
        log_context.update({
            "operation_id": operation_id,
            "duration_seconds": duration,
            "duration_ms": duration * 1000
        })
        
        # Log with appropriate level based on duration
        if duration > 10.0:  # > 10 seconds
            level = logging.WARNING
        elif duration > 5.0:  # > 5 seconds
            level = logging.INFO
        else:
            level = logging.DEBUG
        
        self.logger.log(
            level,
            f"Operation {operation_id} completed in {duration:.3f}s",
            extra=log_context
        )
    
    def log_metric(self, metric_name: str, value: float, context: Optional[Dict[str, Any]] = None):
        """Log a performance metric"""
        log_context = context or {}
        log_context.update({
            "metric_name": metric_name,
            "metric_value": value
        })
        
        self.logger.info(
            f"Metric {metric_name}: {value}",
            extra=log_context
        )


class ErrorTracker:
    """Tracks and aggregates errors for monitoring"""
    
    def __init__(self, logger_name: str = "error_tracker"):
        self.logger = logging.getLogger(logger_name)
        self.error_counts: Dict[str, int] = {}
        self.last_reset = time.time()
        self.reset_interval = 3600  # Reset counts every hour
    
    def track_error(self, error_type: str, error_message: str, context: Optional[Dict[str, Any]] = None):
        """Track an error occurrence"""
        # Reset counts if interval has passed
        if time.time() - self.last_reset > self.reset_interval:
            self.error_counts.clear()
            self.last_reset = time.time()
        
        # Increment error count
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        log_context = context or {}
        log_context.update({
            "error_type": error_type,
            "error_count": self.error_counts[error_type],
            "time_window": "1h"
        })
        
        # Log with escalating severity based on frequency
        count = self.error_counts[error_type]
        if count >= 10:
            level = logging.CRITICAL
        elif count >= 5:
            level = logging.ERROR
        elif count >= 2:
            level = logging.WARNING
        else:
            level = logging.INFO
        
        self.logger.log(
            level,
            f"Error {error_type} occurred (count: {count}): {error_message}",
            extra=log_context
        )
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of tracked errors"""
        return {
            "error_counts": dict(self.error_counts),
            "total_errors": sum(self.error_counts.values()),
            "unique_error_types": len(self.error_counts),
            "time_window_start": datetime.fromtimestamp(self.last_reset).isoformat(),
            "reset_interval_seconds": self.reset_interval
        }


def setup_logging(
    log_level: str = "INFO",
    log_dir: Optional[str] = None,
    enable_json_logging: bool = True,
    enable_file_logging: bool = True,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> Dict[str, logging.Logger]:
    """
    Set up comprehensive logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (None for current directory)
        enable_json_logging: Whether to use JSON formatting
        enable_file_logging: Whether to log to files
        max_file_size: Maximum size of log files before rotation
        backup_count: Number of backup files to keep
        
    Returns:
        Dictionary of configured loggers
    """
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create log directory if specified
    if log_dir:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
    else:
        log_dir = "logs"
        Path(log_dir).mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Choose formatter
    if enable_json_logging:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handlers
    if enable_file_logging:
        # Main application log
        app_handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(log_dir, "app.log"),
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        app_handler.setLevel(numeric_level)
        app_handler.setFormatter(formatter)
        root_logger.addHandler(app_handler)
        
        # Error log (ERROR and above only)
        error_handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(log_dir, "error.log"),
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)
        
        # Performance log
        perf_logger = logging.getLogger("performance")
        perf_handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(log_dir, "performance.log"),
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        perf_handler.setLevel(logging.DEBUG)
        perf_handler.setFormatter(formatter)
        perf_logger.addHandler(perf_handler)
        perf_logger.setLevel(logging.DEBUG)
        perf_logger.propagate = False  # Don't propagate to root logger
    
    # Create specialized loggers
    loggers = {
        "app": logging.getLogger("app"),
        "api": logging.getLogger("api"),
        "database": logging.getLogger("database"),
        "websocket": logging.getLogger("websocket"),
        "error_handler": logging.getLogger("error_handler"),
        "performance": PerformanceLogger(),
        "error_tracker": ErrorTracker()
    }
    
    # Set levels for specialized loggers
    for logger_name, logger in loggers.items():
        if hasattr(logger, 'logger'):  # For custom logger classes
            logger.logger.setLevel(numeric_level)
        elif isinstance(logger, logging.Logger):
            logger.setLevel(numeric_level)
    
    logging.info(f"Logging configured with level {log_level}, JSON: {enable_json_logging}, Files: {enable_file_logging}")
    
    return loggers


def get_request_logger() -> logging.Logger:
    """Get logger for HTTP requests"""
    return logging.getLogger("api.requests")


def get_database_logger() -> logging.Logger:
    """Get logger for database operations"""
    return logging.getLogger("database")


def get_websocket_logger() -> logging.Logger:
    """Get logger for WebSocket operations"""
    return logging.getLogger("websocket")


def log_function_call(logger: logging.Logger, func_name: str, args: tuple, kwargs: dict, duration: float):
    """Log a function call with parameters and duration"""
    logger.debug(
        f"Function {func_name} called",
        extra={
            "function_name": func_name,
            "args_count": len(args),
            "kwargs_keys": list(kwargs.keys()),
            "duration_seconds": duration
        }
    )


def log_api_request(logger: logging.Logger, method: str, path: str, status_code: int, duration: float, client_ip: str = None):
    """Log an API request"""
    logger.info(
        f"{method} {path} - {status_code}",
        extra={
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_seconds": duration,
            "client_ip": client_ip
        }
    )


def log_database_operation(logger: logging.Logger, operation: str, table: str, duration: float, success: bool):
    """Log a database operation"""
    level = logging.INFO if success else logging.ERROR
    logger.log(
        level,
        f"Database {operation} on {table} {'succeeded' if success else 'failed'}",
        extra={
            "operation": operation,
            "table": table,
            "duration_seconds": duration,
            "success": success
        }
    )


# Global instances
performance_logger = None
error_tracker = None


def initialize_global_loggers():
    """Initialize global logger instances"""
    global performance_logger, error_tracker
    performance_logger = PerformanceLogger()
    error_tracker = ErrorTracker()


# Initialize on import
initialize_global_loggers()