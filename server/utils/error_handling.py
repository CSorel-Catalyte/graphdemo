"""
Comprehensive error handling utilities for the AI Knowledge Mapper backend.

This module provides:
- Exponential backoff with jitter for retry logic
- Circuit breaker pattern for external service failures
- Error classification and recovery strategies
- Comprehensive logging and monitoring
"""

import asyncio
import logging
import time
import random
from typing import Any, Callable, Dict, List, Optional, Type, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
import traceback

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""
    NETWORK = "network"
    DATABASE = "database"
    LLM_API = "llm_api"
    VALIDATION = "validation"
    PROCESSING = "processing"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """Structured error information"""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    traceback: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    recoverable: bool = True


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 3
    timeout: float = 30.0


class CircuitBreaker:
    """Circuit breaker implementation for external service calls"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.next_attempt_time = None
        
    def can_execute(self) -> bool:
        """Check if execution is allowed based on circuit breaker state"""
        now = time.time()
        
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if self.next_attempt_time and now >= self.next_attempt_time:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info(f"Circuit breaker {self.name} transitioning to HALF_OPEN")
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        
        return False
    
    def record_success(self):
        """Record a successful execution"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                logger.info(f"Circuit breaker {self.name} transitioning to CLOSED")
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """Record a failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                self.next_attempt_time = time.time() + self.config.recovery_timeout
                logger.warning(f"Circuit breaker {self.name} transitioning to OPEN")
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.next_attempt_time = time.time() + self.config.recovery_timeout
            logger.warning(f"Circuit breaker {self.name} transitioning back to OPEN")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "next_attempt_time": self.next_attempt_time
        }


class RetryConfig:
    """Configuration for retry logic with exponential backoff"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        backoff_factor: float = 1.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.backoff_factor = backoff_factor
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt number"""
        if attempt <= 0:
            return 0
        
        # Exponential backoff
        delay = self.base_delay * (self.exponential_base ** (attempt - 1)) * self.backoff_factor
        delay = min(delay, self.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            jitter_amount = delay * 0.1 * random.random()
            delay += jitter_amount
        
        return delay


class ErrorClassifier:
    """Classifies errors into categories and determines recovery strategies"""
    
    @staticmethod
    def classify_error(error: Exception) -> ErrorInfo:
        """Classify an error and return structured error information"""
        error_id = f"err_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        
        # Get error details
        error_type = type(error).__name__
        error_message = str(error)
        error_traceback = traceback.format_exc()
        
        # Classify by error type and message
        category = ErrorCategory.UNKNOWN
        severity = ErrorSeverity.MEDIUM
        recoverable = True
        
        # Network-related errors
        if any(keyword in error_type.lower() for keyword in ['connection', 'timeout', 'network', 'http']):
            category = ErrorCategory.NETWORK
            severity = ErrorSeverity.MEDIUM
            recoverable = True
        
        # Database-related errors
        elif any(keyword in error_type.lower() for keyword in ['database', 'qdrant', 'oxigraph', 'storage']):
            category = ErrorCategory.DATABASE
            severity = ErrorSeverity.HIGH
            recoverable = True
        
        # LLM API errors
        elif any(keyword in error_type.lower() for keyword in ['openai', 'api', 'rate', 'quota']):
            category = ErrorCategory.LLM_API
            if 'rate' in error_message.lower() or 'quota' in error_message.lower():
                severity = ErrorSeverity.MEDIUM
                recoverable = True
            else:
                severity = ErrorSeverity.HIGH
                recoverable = True
        
        # Validation errors
        elif any(keyword in error_type.lower() for keyword in ['validation', 'pydantic', 'json']):
            category = ErrorCategory.VALIDATION
            severity = ErrorSeverity.LOW
            recoverable = False
        
        # Processing errors
        elif any(keyword in error_type.lower() for keyword in ['processing', 'extraction', 'canonicalization']):
            category = ErrorCategory.PROCESSING
            severity = ErrorSeverity.MEDIUM
            recoverable = True
        
        # System errors
        elif any(keyword in error_type.lower() for keyword in ['memory', 'disk', 'permission', 'system']):
            category = ErrorCategory.SYSTEM
            severity = ErrorSeverity.CRITICAL
            recoverable = False
        
        return ErrorInfo(
            error_id=error_id,
            category=category,
            severity=severity,
            message=error_message,
            details={
                "error_type": error_type,
                "module": getattr(error, '__module__', 'unknown')
            },
            traceback=error_traceback,
            recoverable=recoverable
        )


class ErrorHandler:
    """Central error handler with retry logic and circuit breakers"""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_history: List[ErrorInfo] = []
        self.max_history_size = 1000
        
        # Default circuit breaker configs
        self.default_configs = {
            "llm_api": CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30.0),
            "database": CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60.0),
            "network": CircuitBreakerConfig(failure_threshold=3, recovery_timeout=15.0)
        }
    
    def get_circuit_breaker(self, name: str, category: ErrorCategory) -> CircuitBreaker:
        """Get or create a circuit breaker for the given service"""
        if name not in self.circuit_breakers:
            # Use category-specific config or default
            config_key = category.value if category.value in self.default_configs else "network"
            config = self.default_configs.get(config_key, CircuitBreakerConfig())
            self.circuit_breakers[name] = CircuitBreaker(name, config)
        
        return self.circuit_breakers[name]
    
    def record_error(self, error_info: ErrorInfo):
        """Record an error in the history"""
        self.error_history.append(error_info)
        
        # Limit history size
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size:]
        
        # Log the error
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(error_info.severity, logging.ERROR)
        
        logger.log(
            log_level,
            f"Error {error_info.error_id} [{error_info.category.value}]: {error_info.message}",
            extra={
                "error_id": error_info.error_id,
                "category": error_info.category.value,
                "severity": error_info.severity.value,
                "recoverable": error_info.recoverable,
                "retry_count": error_info.retry_count
            }
        )
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """
        Execute a function with retry logic and circuit breaker protection
        
        Args:
            func: Function to execute
            *args: Function arguments
            retry_config: Retry configuration
            circuit_breaker_name: Name for circuit breaker (optional)
            context: Additional context for error reporting
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retries fail
        """
        if retry_config is None:
            retry_config = RetryConfig()
        
        if context is None:
            context = {}
        
        last_error = None
        
        for attempt in range(retry_config.max_retries + 1):
            try:
                # Check circuit breaker if specified
                if circuit_breaker_name:
                    error_info = ErrorClassifier.classify_error(Exception("dummy"))
                    circuit_breaker = self.get_circuit_breaker(circuit_breaker_name, error_info.category)
                    
                    if not circuit_breaker.can_execute():
                        raise Exception(f"Circuit breaker {circuit_breaker_name} is OPEN")
                
                # Execute the function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Record success if using circuit breaker
                if circuit_breaker_name and circuit_breaker_name in self.circuit_breakers:
                    self.circuit_breakers[circuit_breaker_name].record_success()
                
                # Log successful retry if this wasn't the first attempt
                if attempt > 0:
                    logger.info(f"Function succeeded on attempt {attempt + 1}")
                
                return result
                
            except Exception as e:
                last_error = e
                error_info = ErrorClassifier.classify_error(e)
                error_info.retry_count = attempt
                error_info.context = context
                
                # Record error
                self.record_error(error_info)
                
                # Record failure in circuit breaker
                if circuit_breaker_name and circuit_breaker_name in self.circuit_breakers:
                    self.circuit_breakers[circuit_breaker_name].record_failure()
                
                # Don't retry if error is not recoverable
                if not error_info.recoverable:
                    logger.error(f"Non-recoverable error, not retrying: {error_info.message}")
                    raise
                
                # Don't retry on last attempt
                if attempt >= retry_config.max_retries:
                    break
                
                # Calculate delay and wait
                delay = retry_config.get_delay(attempt + 1)
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {error_info.message}"
                )
                await asyncio.sleep(delay)
        
        # All retries failed
        logger.error(f"All {retry_config.max_retries + 1} attempts failed")
        raise last_error
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics and health metrics"""
        if not self.error_history:
            return {
                "total_errors": 0,
                "by_category": {},
                "by_severity": {},
                "recent_errors": [],
                "circuit_breakers": {}
            }
        
        # Count by category
        by_category = {}
        by_severity = {}
        
        for error in self.error_history:
            category = error.category.value
            severity = error.severity.value
            
            by_category[category] = by_category.get(category, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        # Get recent errors (last 10)
        recent_errors = [
            {
                "error_id": error.error_id,
                "category": error.category.value,
                "severity": error.severity.value,
                "message": error.message,
                "timestamp": error.timestamp.isoformat(),
                "retry_count": error.retry_count
            }
            for error in self.error_history[-10:]
        ]
        
        # Get circuit breaker statuses
        circuit_breaker_statuses = {
            name: breaker.get_status()
            for name, breaker in self.circuit_breakers.items()
        }
        
        return {
            "total_errors": len(self.error_history),
            "by_category": by_category,
            "by_severity": by_severity,
            "recent_errors": recent_errors,
            "circuit_breakers": circuit_breaker_statuses
        }


# Global error handler instance
error_handler = ErrorHandler()


def with_retry(
    retry_config: Optional[RetryConfig] = None,
    circuit_breaker_name: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
):
    """
    Decorator for adding retry logic to functions
    
    Args:
        retry_config: Retry configuration
        circuit_breaker_name: Circuit breaker name
        context: Additional context
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await error_handler.execute_with_retry(
                func, *args,
                retry_config=retry_config,
                circuit_breaker_name=circuit_breaker_name,
                context=context,
                **kwargs
            )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(error_handler.execute_with_retry(
                func, *args,
                retry_config=retry_config,
                circuit_breaker_name=circuit_breaker_name,
                context=context,
                **kwargs
            ))
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def handle_graceful_degradation(
    fallback_func: Optional[Callable] = None,
    fallback_value: Any = None,
    log_fallback: bool = True
):
    """
    Decorator for graceful degradation with fallback behavior
    
    Args:
        fallback_func: Function to call as fallback
        fallback_value: Static value to return as fallback
        log_fallback: Whether to log fallback usage
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                error_info = ErrorClassifier.classify_error(e)
                error_handler.record_error(error_info)
                
                if log_fallback:
                    logger.warning(f"Function failed, using fallback: {error_info.message}")
                
                if fallback_func:
                    if asyncio.iscoroutinefunction(fallback_func):
                        return await fallback_func(*args, **kwargs)
                    else:
                        return fallback_func(*args, **kwargs)
                else:
                    return fallback_value
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_info = ErrorClassifier.classify_error(e)
                error_handler.record_error(error_info)
                
                if log_fallback:
                    logger.warning(f"Function failed, using fallback: {error_info.message}")
                
                if fallback_func:
                    return fallback_func(*args, **kwargs)
                else:
                    return fallback_value
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator