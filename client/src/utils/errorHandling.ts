/**
 * Comprehensive error handling utilities for the frontend.
 * 
 * This module provides:
 * - Error classification and recovery strategies
 * - User-friendly error messages
 * - Error boundaries and fallback components
 * - Retry logic with exponential backoff
 * - Error reporting and logging
 */

import { toast } from 'react-hot-toast';

export enum ErrorSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical'
}

export enum ErrorCategory {
  NETWORK = 'network',
  API = 'api',
  WEBSOCKET = 'websocket',
  VALIDATION = 'validation',
  RENDERING = 'rendering',
  STORAGE = 'storage',
  UNKNOWN = 'unknown'
}

export interface ErrorInfo {
  id: string;
  category: ErrorCategory;
  severity: ErrorSeverity;
  message: string;
  userMessage: string;
  details?: Record<string, any>;
  timestamp: Date;
  context?: Record<string, any>;
  recoverable: boolean;
  retryable: boolean;
}

export interface RetryConfig {
  maxRetries: number;
  baseDelay: number;
  maxDelay: number;
  exponentialBase: number;
  jitter: boolean;
}

export class ErrorClassifier {
  static classify(error: Error | unknown, context?: Record<string, any>): ErrorInfo {
    const errorId = `err_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const timestamp = new Date();
    
    let category = ErrorCategory.UNKNOWN;
    let severity = ErrorSeverity.MEDIUM;
    let userMessage = 'An unexpected error occurred';
    let recoverable = true;
    let retryable = false;
    
    const errorMessage = error instanceof Error ? error.message : String(error);
    const errorName = error instanceof Error ? error.name : 'UnknownError';
    
    // Network errors
    if (errorMessage.includes('fetch') || 
        errorMessage.includes('network') ||
        errorMessage.includes('NetworkError') ||
        errorName === 'TypeError' && errorMessage.includes('Failed to fetch')) {
      category = ErrorCategory.NETWORK;
      severity = ErrorSeverity.MEDIUM;
      userMessage = 'Network connection issue. Please check your internet connection.';
      recoverable = true;
      retryable = true;
    }
    
    // API errors
    else if (errorMessage.includes('API') ||
             errorMessage.includes('HTTP') ||
             errorMessage.includes('status') ||
             context?.status) {
      category = ErrorCategory.API;
      const status = context?.status || 0;
      
      if (status >= 500) {
        severity = ErrorSeverity.HIGH;
        userMessage = 'Server error. Please try again in a few moments.';
        retryable = true;
      } else if (status >= 400) {
        severity = ErrorSeverity.MEDIUM;
        userMessage = 'Request failed. Please check your input and try again.';
        retryable = false;
      } else {
        severity = ErrorSeverity.MEDIUM;
        userMessage = 'API request failed. Please try again.';
        retryable = true;
      }
      recoverable = true;
    }
    
    // WebSocket errors
    else if (errorMessage.includes('WebSocket') ||
             errorMessage.includes('websocket') ||
             context?.type === 'websocket') {
      category = ErrorCategory.WEBSOCKET;
      severity = ErrorSeverity.MEDIUM;
      userMessage = 'Real-time connection lost. Attempting to reconnect...';
      recoverable = true;
      retryable = true;
    }
    
    // Validation errors
    else if (errorMessage.includes('validation') ||
             errorMessage.includes('invalid') ||
             errorName === 'ValidationError') {
      category = ErrorCategory.VALIDATION;
      severity = ErrorSeverity.LOW;
      userMessage = 'Invalid input. Please check your data and try again.';
      recoverable = true;
      retryable = false;
    }
    
    // Rendering errors
    else if (errorMessage.includes('render') ||
             errorMessage.includes('component') ||
             context?.type === 'rendering') {
      category = ErrorCategory.RENDERING;
      severity = ErrorSeverity.HIGH;
      userMessage = 'Display error occurred. The page will reload automatically.';
      recoverable = true;
      retryable = false;
    }
    
    // Storage errors
    else if (errorMessage.includes('localStorage') ||
             errorMessage.includes('sessionStorage') ||
             errorMessage.includes('storage')) {
      category = ErrorCategory.STORAGE;
      severity = ErrorSeverity.LOW;
      userMessage = 'Local storage error. Some features may not work properly.';
      recoverable = true;
      retryable = false;
    }
    
    return {
      id: errorId,
      category,
      severity,
      message: errorMessage,
      userMessage,
      details: {
        name: errorName,
        stack: error instanceof Error ? error.stack : undefined
      },
      timestamp,
      context,
      recoverable,
      retryable
    };
  }
}

export class RetryManager {
  private static retryConfigs: Map<string, RetryConfig> = new Map();
  
  static setRetryConfig(key: string, config: RetryConfig) {
    this.retryConfigs.set(key, config);
  }
  
  static getRetryConfig(key: string): RetryConfig {
    return this.retryConfigs.get(key) || {
      maxRetries: 3,
      baseDelay: 1000,
      maxDelay: 30000,
      exponentialBase: 2,
      jitter: true
    };
  }
  
  static calculateDelay(attempt: number, config: RetryConfig): number {
    if (attempt <= 0) return 0;
    
    let delay = config.baseDelay * Math.pow(config.exponentialBase, attempt - 1);
    delay = Math.min(delay, config.maxDelay);
    
    if (config.jitter) {
      const jitterAmount = delay * 0.1 * Math.random();
      delay += jitterAmount;
    }
    
    return delay;
  }
  
  static async executeWithRetry<T>(
    operation: () => Promise<T>,
    retryKey: string = 'default',
    context?: Record<string, any>
  ): Promise<T> {
    const config = this.getRetryConfig(retryKey);
    let lastError: Error | unknown;
    
    for (let attempt = 0; attempt <= config.maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error;
        const errorInfo = ErrorClassifier.classify(error, context);
        
        // Don't retry if error is not retryable
        if (!errorInfo.retryable) {
          throw error;
        }
        
        // Don't retry on last attempt
        if (attempt >= config.maxRetries) {
          break;
        }
        
        const delay = this.calculateDelay(attempt + 1, config);
        console.warn(`Attempt ${attempt + 1} failed, retrying in ${delay}ms:`, errorInfo.message);
        
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
    
    throw lastError;
  }
}

export class ErrorReporter {
  private static errorHistory: ErrorInfo[] = [];
  private static maxHistorySize = 100;
  
  static reportError(errorInfo: ErrorInfo) {
    // Add to history
    this.errorHistory.push(errorInfo);
    
    // Limit history size
    if (this.errorHistory.length > this.maxHistorySize) {
      this.errorHistory = this.errorHistory.slice(-this.maxHistorySize);
    }
    
    // Log to console
    const logLevel = this.getLogLevel(errorInfo.severity);
    console[logLevel](`[${errorInfo.category}] ${errorInfo.message}`, {
      id: errorInfo.id,
      severity: errorInfo.severity,
      context: errorInfo.context,
      details: errorInfo.details
    });
    
    // Show user notification based on severity
    this.showUserNotification(errorInfo);
    
    // Send to monitoring service (if configured)
    this.sendToMonitoring(errorInfo);
  }
  
  private static getLogLevel(severity: ErrorSeverity): 'error' | 'warn' | 'info' {
    switch (severity) {
      case ErrorSeverity.CRITICAL:
      case ErrorSeverity.HIGH:
        return 'error';
      case ErrorSeverity.MEDIUM:
        return 'warn';
      case ErrorSeverity.LOW:
      default:
        return 'info';
    }
  }
  
  private static showUserNotification(errorInfo: ErrorInfo) {
    const options = {
      duration: this.getNotificationDuration(errorInfo.severity),
      position: 'top-right' as const,
      style: this.getNotificationStyle(errorInfo.severity)
    };
    
    switch (errorInfo.severity) {
      case ErrorSeverity.CRITICAL:
        toast.error(errorInfo.userMessage, options);
        break;
      case ErrorSeverity.HIGH:
        toast.error(errorInfo.userMessage, options);
        break;
      case ErrorSeverity.MEDIUM:
        toast(errorInfo.userMessage, { ...options, icon: '⚠️' });
        break;
      case ErrorSeverity.LOW:
        toast(errorInfo.userMessage, { ...options, icon: 'ℹ️' });
        break;
    }
  }
  
  private static getNotificationDuration(severity: ErrorSeverity): number {
    switch (severity) {
      case ErrorSeverity.CRITICAL:
        return 8000;
      case ErrorSeverity.HIGH:
        return 6000;
      case ErrorSeverity.MEDIUM:
        return 4000;
      case ErrorSeverity.LOW:
      default:
        return 3000;
    }
  }
  
  private static getNotificationStyle(severity: ErrorSeverity) {
    const baseStyle = {
      borderRadius: '8px',
      fontSize: '14px',
      fontWeight: '500'
    };
    
    switch (severity) {
      case ErrorSeverity.CRITICAL:
        return {
          ...baseStyle,
          background: '#dc2626',
          color: 'white',
          border: '2px solid #b91c1c'
        };
      case ErrorSeverity.HIGH:
        return {
          ...baseStyle,
          background: '#ea580c',
          color: 'white',
          border: '2px solid #c2410c'
        };
      case ErrorSeverity.MEDIUM:
        return {
          ...baseStyle,
          background: '#f59e0b',
          color: 'white',
          border: '2px solid #d97706'
        };
      case ErrorSeverity.LOW:
      default:
        return {
          ...baseStyle,
          background: '#3b82f6',
          color: 'white',
          border: '2px solid #2563eb'
        };
    }
  }
  
  private static sendToMonitoring(errorInfo: ErrorInfo) {
    // In a production environment, you would send errors to a monitoring service
    // like Sentry, LogRocket, or a custom analytics endpoint
    
    // For now, we'll just store it locally for debugging
    try {
      const monitoringData = {
        ...errorInfo,
        userAgent: navigator.userAgent,
        url: window.location.href,
        timestamp: errorInfo.timestamp.toISOString()
      };
      
      // Store in localStorage for debugging (with size limit)
      const storageKey = 'error_monitoring';
      const existingData = JSON.parse(localStorage.getItem(storageKey) || '[]');
      existingData.push(monitoringData);
      
      // Keep only last 50 errors
      const limitedData = existingData.slice(-50);
      localStorage.setItem(storageKey, JSON.stringify(limitedData));
      
    } catch (storageError) {
      console.warn('Failed to store error for monitoring:', storageError);
    }
  }
  
  static getErrorHistory(): ErrorInfo[] {
    return [...this.errorHistory];
  }
  
  static getErrorStatistics() {
    const stats = {
      total: this.errorHistory.length,
      byCategory: {} as Record<string, number>,
      bySeverity: {} as Record<string, number>,
      recent: this.errorHistory.slice(-10)
    };
    
    this.errorHistory.forEach(error => {
      stats.byCategory[error.category] = (stats.byCategory[error.category] || 0) + 1;
      stats.bySeverity[error.severity] = (stats.bySeverity[error.severity] || 0) + 1;
    });
    
    return stats;
  }
  
  static clearErrorHistory() {
    this.errorHistory = [];
    localStorage.removeItem('error_monitoring');
  }
}

// Global error handler function
export function handleError(error: Error | unknown, context?: Record<string, any>) {
  const errorInfo = ErrorClassifier.classify(error, context);
  ErrorReporter.reportError(errorInfo);
  return errorInfo;
}

// Async error handler with retry capability
export async function handleAsyncError<T>(
  operation: () => Promise<T>,
  retryKey?: string,
  context?: Record<string, any>
): Promise<T> {
  try {
    if (retryKey) {
      return await RetryManager.executeWithRetry(operation, retryKey, context);
    } else {
      return await operation();
    }
  } catch (error) {
    handleError(error, context);
    throw error;
  }
}

// Set up default retry configurations
RetryManager.setRetryConfig('api', {
  maxRetries: 3,
  baseDelay: 1000,
  maxDelay: 10000,
  exponentialBase: 2,
  jitter: true
});

RetryManager.setRetryConfig('websocket', {
  maxRetries: 5,
  baseDelay: 2000,
  maxDelay: 30000,
  exponentialBase: 1.5,
  jitter: true
});

RetryManager.setRetryConfig('network', {
  maxRetries: 2,
  baseDelay: 500,
  maxDelay: 5000,
  exponentialBase: 2,
  jitter: true
});