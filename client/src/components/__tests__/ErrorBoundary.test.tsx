/**
 * Tests for Error Boundary components
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ErrorBoundary, GraphErrorBoundary, useErrorHandler } from '../ErrorBoundary';

// Mock the error handling utilities
vi.mock('../../utils/errorHandling', () => ({
  handleError: vi.fn().mockReturnValue({
    id: 'test-error-id',
    category: 'rendering',
    severity: 'high',
    message: 'Test error message',
    userMessage: 'Something went wrong',
    timestamp: new Date(),
    recoverable: true,
    retryable: false
  })
}));

// Component that throws an error for testing
const ThrowError: React.FC<{ shouldThrow?: boolean }> = ({ shouldThrow = true }) => {
  if (shouldThrow) {
    throw new Error('Test error');
  }
  return <div>No error</div>;
};

describe('ErrorBoundary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Suppress console.error for cleaner test output
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  it('renders children when there is no error', () => {
    render(
      <ErrorBoundary>
        <div>Test content</div>
      </ErrorBoundary>
    );

    expect(screen.getByText('Test content')).toBeInTheDocument();
  });

  it('renders error fallback when child component throws', () => {
    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText('Application Error')).toBeInTheDocument();
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText('Try Again')).toBeInTheDocument();
  });

  it('renders custom fallback when provided', () => {
    const customFallback = <div>Custom error message</div>;

    render(
      <ErrorBoundary fallback={customFallback}>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom error message')).toBeInTheDocument();
    expect(screen.queryByText('Application Error')).not.toBeInTheDocument();
  });

  it('calls onError callback when error occurs', () => {
    const onError = vi.fn();

    render(
      <ErrorBoundary onError={onError}>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(onError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({
        componentStack: expect.any(String)
      })
    );
  });

  it('recovers when retry button is clicked', () => {
    const { rerender } = render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Application Error')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Try Again'));

    rerender(
      <ErrorBoundary>
        <ThrowError shouldThrow={false} />
      </ErrorBoundary>
    );

    expect(screen.getByText('No error')).toBeInTheDocument();
    expect(screen.queryByText('Application Error')).not.toBeInTheDocument();
  });

  it('shows technical details in development mode', () => {
    const originalEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = 'development';

    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText('Show Technical Details')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Show Technical Details'));

    expect(screen.getByText('Technical Details')).toBeInTheDocument();
    expect(screen.getByText('Category:')).toBeInTheDocument();
    expect(screen.getByText('Hide Technical Details')).toBeInTheDocument();

    process.env.NODE_ENV = originalEnv;
  });

  it('isolates error when isolate prop is true', () => {
    render(
      <ErrorBoundary isolate={true}>
        <ThrowError />
      </ErrorBoundary>
    );

    // Should not show "Go Home" button in isolated mode
    expect(screen.queryByText('Go Home')).not.toBeInTheDocument();
    expect(screen.queryByText('Reload Page')).not.toBeInTheDocument();
    expect(screen.getByText('Try Again')).toBeInTheDocument();
  });
});

describe('GraphErrorBoundary', () => {
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  it('renders specialized error message for graph errors', () => {
    render(
      <GraphErrorBoundary>
        <ThrowError />
      </GraphErrorBoundary>
    );

    expect(screen.getByText('Graph visualization error')).toBeInTheDocument();
    expect(screen.getByText('The 3D graph could not be rendered')).toBeInTheDocument();
  });
});

describe('useErrorHandler', () => {
  const TestComponent: React.FC = () => {
    const { captureError, resetError } = useErrorHandler();

    return (
      <div>
        <button onClick={() => captureError(new Error('Manual error'))}>
          Trigger Error
        </button>
        <button onClick={resetError}>Reset</button>
        <div>Component content</div>
      </div>
    );
  };

  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  it('captures and throws errors to trigger error boundary', () => {
    render(
      <ErrorBoundary>
        <TestComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText('Component content')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Trigger Error'));

    expect(screen.getByText('Application Error')).toBeInTheDocument();
    expect(screen.queryByText('Component content')).not.toBeInTheDocument();
  });
});