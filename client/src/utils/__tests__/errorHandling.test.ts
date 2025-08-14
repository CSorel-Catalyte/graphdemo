/**
 * Tests for error handling utilities
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { 
  ErrorClassifier, 
  RetryManager, 
  ErrorReporter, 
  handleError, 
  handleAsyncError,
  ErrorCategory,
  ErrorSeverity 
} from '../errorHandling';

// Mock toast notifications
vi.mock('react-hot-toast', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
    __esModule: true,
    default: vi.fn()
  }
}));

describe('ErrorClassifier', () => {
  it('classifies network errors correctly', () => {
    const networkError = new Error('Failed to fetch');
    const errorInfo = ErrorClassifier.classify(networkError);

    expect(errorInfo.category).toBe(ErrorCategory.NETWORK);
    expect(errorInfo.severity).toBe(ErrorSeverity.MEDIUM);
    expect(errorInfo.retryable).toBe(true);
    expect(errorInfo.userMessage).toContain('Network connection issue');
  });

  it('classifies API errors with status codes', () => {
    const apiError = new Error('API request failed');
    const errorInfo = ErrorClassifier.classify(apiError, { status: 500 });

    expect(errorInfo.category).toBe(ErrorCategory.API);
    expect(errorInfo.severity).toBe(ErrorSeverity.HIGH);
    expect(errorInfo.retryable).toBe(true);
    expect(errorInfo.userMessage).toContain('Server error');
  });

  it('classifies validation errors as non-retryable', () => {
    const validationError = new Error('Validation failed');
    validationError.name = 'ValidationError';
    const errorInfo = ErrorClassifier.classify(validationError);

    expect(errorInfo.category).toBe(ErrorCategory.VALIDATION);
    expect(errorInfo.severity).toBe(ErrorSeverity.LOW);
    expect(errorInfo.retryable).toBe(false);
    expect(errorInfo.recoverable).toBe(true);
  });

  it('handles unknown errors gracefully', () => {
    const unknownError = new Error('Something weird happened');
    const errorInfo = ErrorClassifier.classify(unknownError);

    expect(errorInfo.category).toBe(ErrorCategory.UNKNOWN);
    expect(errorInfo.severity).toBe(ErrorSeverity.MEDIUM);
    expect(errorInfo.id).toMatch(/^err_\d+_[a-z0-9]+$/);
    expect(errorInfo.timestamp).toBeInstanceOf(Date);
  });

  it('handles non-Error objects', () => {
    const stringError = 'String error message';
    const errorInfo = ErrorClassifier.classify(stringError);

    expect(errorInfo.message).toBe('String error message');
    expect(errorInfo.category).toBe(ErrorCategory.UNKNOWN);
  });
});

describe('RetryManager', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('calculates exponential backoff delays correctly', () => {
    const config = {
      maxRetries: 3,
      baseDelay: 1000,
      maxDelay: 10000,
      exponentialBase: 2,
      jitter: false
    };

    expect(RetryManager.calculateDelay(1, config)).toBe(1000);
    expect(RetryManager.calculateDelay(2, config)).toBe(2000);
    expect(RetryManager.calculateDelay(3, config)).toBe(4000);
  });

  it('respects maximum delay limit', () => {
    const config = {
      maxRetries: 10,
      baseDelay: 1000,
      maxDelay: 5000,
      exponentialBase: 2,
      jitter: false
    };

    expect(RetryManager.calculateDelay(10, config)).toBe(5000);
  });

  it('adds jitter when enabled', () => {
    const config = {
      maxRetries: 3,
      baseDelay: 1000,
      maxDelay: 10000,
      exponentialBase: 2,
      jitter: true
    };

    const delay1 = RetryManager.calculateDelay(1, config);
    const delay2 = RetryManager.calculateDelay(1, config);

    // With jitter, delays should be different
    expect(delay1).not.toBe(delay2);
    expect(delay1).toBeGreaterThanOrEqual(1000);
    expect(delay1).toBeLessThanOrEqual(1100); // 10% jitter
  });

  it('executes operation successfully on first try', async () => {
    const operation = vi.fn().mockResolvedValue('success');
    
    const result = await RetryManager.executeWithRetry(operation);
    
    expect(result).toBe('success');
    expect(operation).toHaveBeenCalledTimes(1);
  });

  it('retries on retryable errors', async () => {
    const operation = vi.fn()
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValue('success');

    // Mock the error classification to return retryable error
    vi.spyOn(ErrorClassifier, 'classify').mockReturnValue({
      id: 'test-id',
      category: ErrorCategory.NETWORK,
      severity: ErrorSeverity.MEDIUM,
      message: 'Network error',
      userMessage: 'Network issue',
      timestamp: new Date(),
      context: {},
      recoverable: true,
      retryable: true
    });

    const promise = RetryManager.executeWithRetry(operation, 'test');
    
    // Fast-forward through the delay
    await vi.runAllTimersAsync();
    
    const result = await promise;
    
    expect(result).toBe('success');
    expect(operation).toHaveBeenCalledTimes(2);
  });

  it('does not retry on non-retryable errors', async () => {
    const operation = vi.fn().mockRejectedValue(new Error('Validation error'));

    vi.spyOn(ErrorClassifier, 'classify').mockReturnValue({
      id: 'test-id',
      category: ErrorCategory.VALIDATION,
      severity: ErrorSeverity.LOW,
      message: 'Validation error',
      userMessage: 'Invalid input',
      timestamp: new Date(),
      context: {},
      recoverable: true,
      retryable: false
    });

    await expect(RetryManager.executeWithRetry(operation)).rejects.toThrow('Validation error');
    expect(operation).toHaveBeenCalledTimes(1);
  });

  it('gives up after max retries', async () => {
    const operation = vi.fn().mockRejectedValue(new Error('Persistent error'));

    vi.spyOn(ErrorClassifier, 'classify').mockReturnValue({
      id: 'test-id',
      category: ErrorCategory.NETWORK,
      severity: ErrorSeverity.MEDIUM,
      message: 'Persistent error',
      userMessage: 'Network issue',
      timestamp: new Date(),
      context: {},
      recoverable: true,
      retryable: true
    });

    RetryManager.setRetryConfig('test', {
      maxRetries: 2,
      baseDelay: 100,
      maxDelay: 1000,
      exponentialBase: 2,
      jitter: false
    });

    const promise = RetryManager.executeWithRetry(operation, 'test');
    
    // Fast-forward through all delays
    await vi.runAllTimersAsync();
    
    await expect(promise).rejects.toThrow('Persistent error');
    expect(operation).toHaveBeenCalledTimes(3); // Initial + 2 retries
  });
});

describe('ErrorReporter', () => {
  beforeEach(() => {
    ErrorReporter.clearErrorHistory();
    vi.clearAllMocks();
  });

  it('records errors in history', () => {
    const error = new Error('Test error');
    const errorInfo = ErrorClassifier.classify(error);
    
    ErrorReporter.reportError(errorInfo);
    
    const history = ErrorReporter.getErrorHistory();
    expect(history).toHaveLength(1);
    expect(history[0]).toEqual(errorInfo);
  });

  it('limits error history size', () => {
    // Add more errors than the max size
    for (let i = 0; i < 150; i++) {
      const error = new Error(`Test error ${i}`);
      const errorInfo = ErrorClassifier.classify(error);
      ErrorReporter.reportError(errorInfo);
    }
    
    const history = ErrorReporter.getErrorHistory();
    expect(history).toHaveLength(100); // Max size
  });

  it('generates error statistics correctly', () => {
    const networkError = ErrorClassifier.classify(new Error('Network error'), { type: 'network' });
    const validationError = ErrorClassifier.classify(new Error('Validation error'));
    validationError.category = ErrorCategory.VALIDATION;
    validationError.severity = ErrorSeverity.LOW;

    ErrorReporter.reportError(networkError);
    ErrorReporter.reportError(validationError);
    ErrorReporter.reportError(networkError);

    const stats = ErrorReporter.getErrorStatistics();
    
    expect(stats.total).toBe(3);
    expect(stats.byCategory[ErrorCategory.NETWORK]).toBe(2);
    expect(stats.byCategory[ErrorCategory.VALIDATION]).toBe(1);
    expect(stats.bySeverity[ErrorSeverity.MEDIUM]).toBe(2);
    expect(stats.bySeverity[ErrorSeverity.LOW]).toBe(1);
    expect(stats.recent).toHaveLength(3);
  });

  it('clears error history', () => {
    const error = new Error('Test error');
    const errorInfo = ErrorClassifier.classify(error);
    ErrorReporter.reportError(errorInfo);
    
    expect(ErrorReporter.getErrorHistory()).toHaveLength(1);
    
    ErrorReporter.clearErrorHistory();
    
    expect(ErrorReporter.getErrorHistory()).toHaveLength(0);
  });
});

describe('handleError', () => {
  beforeEach(() => {
    vi.spyOn(ErrorReporter, 'reportError').mockImplementation(() => {});
  });

  it('classifies and reports errors', () => {
    const error = new Error('Test error');
    const context = { component: 'TestComponent' };
    
    const errorInfo = handleError(error, context);
    
    expect(ErrorReporter.reportError).toHaveBeenCalledWith(errorInfo);
    expect(errorInfo.context).toEqual(context);
  });
});

describe('handleAsyncError', () => {
  beforeEach(() => {
    vi.spyOn(ErrorReporter, 'reportError').mockImplementation(() => {});
  });

  it('handles successful async operations', async () => {
    const operation = vi.fn().mockResolvedValue('success');
    
    const result = await handleAsyncError(operation);
    
    expect(result).toBe('success');
    expect(ErrorReporter.reportError).not.toHaveBeenCalled();
  });

  it('handles and reports async errors', async () => {
    const error = new Error('Async error');
    const operation = vi.fn().mockRejectedValue(error);
    
    await expect(handleAsyncError(operation)).rejects.toThrow('Async error');
    expect(ErrorReporter.reportError).toHaveBeenCalled();
  });

  it('uses retry logic when retry key is provided', async () => {
    const operation = vi.fn()
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValue('success');

    vi.spyOn(RetryManager, 'executeWithRetry').mockResolvedValue('success');
    
    const result = await handleAsyncError(operation, 'network');
    
    expect(result).toBe('success');
    expect(RetryManager.executeWithRetry).toHaveBeenCalledWith(
      operation,
      'network',
      undefined
    );
  });
});