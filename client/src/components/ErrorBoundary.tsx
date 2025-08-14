/**
 * Error Boundary components for React error handling and recovery.
 * 
 * This module provides:
 * - Global error boundary for the entire application
 * - Component-specific error boundaries
 * - Error fallback UI components
 * - Error recovery mechanisms
 */

import React, { Component, ReactNode, ErrorInfo as ReactErrorInfo } from 'react';
import { AlertTriangle, RefreshCw, Home, Bug } from 'lucide-react';
import { handleError, ErrorInfo } from '../utils/errorHandling';

interface ErrorBoundaryState {
  hasError: boolean;
  errorInfo: ErrorInfo | null;
  errorId: string | null;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ReactErrorInfo) => void;
  isolate?: boolean; // If true, only affects this component, not the whole app
  showDetails?: boolean; // Show technical error details
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      errorInfo: null,
      errorId: null
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    // Update state so the next render will show the fallback UI
    const errorInfo = handleError(error, { type: 'rendering', boundary: true });
    
    return {
      hasError: true,
      errorInfo,
      errorId: errorInfo.id
    };
  }

  componentDidCatch(error: Error, errorInfo: ReactErrorInfo) {
    // Log the error with React-specific context
    const enhancedError = handleError(error, {
      type: 'rendering',
      boundary: true,
      componentStack: errorInfo.componentStack,
      errorBoundary: this.constructor.name
    });

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    console.error('Error Boundary caught an error:', {
      error,
      errorInfo,
      enhancedError
    });
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
      errorInfo: null,
      errorId: null
    });
  };

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default fallback UI
      return (
        <ErrorFallback
          errorInfo={this.state.errorInfo}
          onRetry={this.handleRetry}
          onReload={this.handleReload}
          onGoHome={this.handleGoHome}
          isolate={this.props.isolate}
          showDetails={this.props.showDetails}
        />
      );
    }

    return this.props.children;
  }
}

interface ErrorFallbackProps {
  errorInfo: ErrorInfo | null;
  onRetry: () => void;
  onReload: () => void;
  onGoHome: () => void;
  isolate?: boolean;
  showDetails?: boolean;
}

const ErrorFallback: React.FC<ErrorFallbackProps> = ({
  errorInfo,
  onRetry,
  onReload,
  onGoHome,
  isolate = false,
  showDetails = false
}) => {
  const [showTechnicalDetails, setShowTechnicalDetails] = React.useState(false);

  const getErrorIcon = () => {
    if (!errorInfo) return <AlertTriangle className="w-12 h-12 text-red-500" />;
    
    switch (errorInfo.severity) {
      case 'critical':
        return <AlertTriangle className="w-12 h-12 text-red-600" />;
      case 'high':
        return <AlertTriangle className="w-12 h-12 text-red-500" />;
      case 'medium':
        return <AlertTriangle className="w-12 h-12 text-orange-500" />;
      case 'low':
      default:
        return <AlertTriangle className="w-12 h-12 text-yellow-500" />;
    }
  };

  const getErrorTitle = () => {
    if (!errorInfo) return 'Something went wrong';
    
    switch (errorInfo.severity) {
      case 'critical':
        return 'Critical Error';
      case 'high':
        return 'Application Error';
      case 'medium':
        return 'Component Error';
      case 'low':
      default:
        return 'Minor Error';
    }
  };

  const containerClass = isolate 
    ? 'p-6 bg-red-50 border border-red-200 rounded-lg'
    : 'min-h-screen flex items-center justify-center bg-gray-50 px-4';

  const contentClass = isolate
    ? 'text-center'
    : 'max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center';

  return (
    <div className={containerClass}>
      <div className={contentClass}>
        <div className="flex justify-center mb-4">
          {getErrorIcon()}
        </div>
        
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          {getErrorTitle()}
        </h1>
        
        <p className="text-gray-600 mb-6">
          {errorInfo?.userMessage || 'An unexpected error occurred. Please try again.'}
        </p>

        {errorInfo?.id && (
          <p className="text-sm text-gray-500 mb-4">
            Error ID: <code className="bg-gray-100 px-2 py-1 rounded">{errorInfo.id}</code>
          </p>
        )}

        <div className="space-y-3">
          <button
            onClick={onRetry}
            className="w-full flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Try Again
          </button>

          {!isolate && (
            <>
              <button
                onClick={onReload}
                className="w-full flex items-center justify-center px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Reload Page
              </button>

              <button
                onClick={onGoHome}
                className="w-full flex items-center justify-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                <Home className="w-4 h-4 mr-2" />
                Go Home
              </button>
            </>
          )}

          {(showDetails || process.env.NODE_ENV === 'development') && errorInfo && (
            <button
              onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
              className="w-full flex items-center justify-center px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
            >
              <Bug className="w-4 h-4 mr-2" />
              {showTechnicalDetails ? 'Hide' : 'Show'} Technical Details
            </button>
          )}
        </div>

        {showTechnicalDetails && errorInfo && (
          <div className="mt-6 p-4 bg-gray-100 rounded-lg text-left">
            <h3 className="font-semibold text-gray-900 mb-2">Technical Details</h3>
            <div className="space-y-2 text-sm text-gray-700">
              <div>
                <strong>Category:</strong> {errorInfo.category}
              </div>
              <div>
                <strong>Severity:</strong> {errorInfo.severity}
              </div>
              <div>
                <strong>Time:</strong> {errorInfo.timestamp.toLocaleString()}
              </div>
              <div>
                <strong>Message:</strong> {errorInfo.message}
              </div>
              {errorInfo.details?.stack && (
                <div>
                  <strong>Stack Trace:</strong>
                  <pre className="mt-1 p-2 bg-gray-200 rounded text-xs overflow-auto max-h-32">
                    {errorInfo.details.stack}
                  </pre>
                </div>
              )}
              {errorInfo.context && (
                <div>
                  <strong>Context:</strong>
                  <pre className="mt-1 p-2 bg-gray-200 rounded text-xs overflow-auto max-h-32">
                    {JSON.stringify(errorInfo.context, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Specialized error boundaries for different parts of the application

export const GraphErrorBoundary: React.FC<{ children: ReactNode }> = ({ children }) => (
  <ErrorBoundary
    isolate={true}
    fallback={
      <div className="flex items-center justify-center h-64 bg-gray-50 border border-gray-200 rounded-lg">
        <div className="text-center">
          <AlertTriangle className="w-8 h-8 text-orange-500 mx-auto mb-2" />
          <p className="text-gray-600">Graph visualization error</p>
          <p className="text-sm text-gray-500">The 3D graph could not be rendered</p>
        </div>
      </div>
    }
  >
    {children}
  </ErrorBoundary>
);

export const SidePanelErrorBoundary: React.FC<{ children: ReactNode }> = ({ children }) => (
  <ErrorBoundary
    isolate={true}
    fallback={
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <div className="flex items-center">
          <AlertTriangle className="w-5 h-5 text-red-500 mr-2" />
          <div>
            <p className="text-red-800 font-medium">Panel Error</p>
            <p className="text-red-600 text-sm">Unable to display panel content</p>
          </div>
        </div>
      </div>
    }
  >
    {children}
  </ErrorBoundary>
);

export const SearchErrorBoundary: React.FC<{ children: ReactNode }> = ({ children }) => (
  <ErrorBoundary
    isolate={true}
    fallback={
      <div className="p-2 bg-yellow-50 border border-yellow-200 rounded">
        <p className="text-yellow-800 text-sm">Search temporarily unavailable</p>
      </div>
    }
  >
    {children}
  </ErrorBoundary>
);

// Hook for using error boundaries programmatically
export const useErrorHandler = () => {
  const [error, setError] = React.useState<Error | null>(null);

  const resetError = React.useCallback(() => {
    setError(null);
  }, []);

  const captureError = React.useCallback((error: Error | unknown) => {
    const errorObj = error instanceof Error ? error : new Error(String(error));
    setError(errorObj);
    handleError(errorObj);
  }, []);

  // Throw error to trigger error boundary
  if (error) {
    throw error;
  }

  return { captureError, resetError };
};