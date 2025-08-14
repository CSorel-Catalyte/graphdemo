/**
 * Enhanced API utility functions for the AI Knowledge Mapper frontend.
 * Provides centralized API calls with comprehensive error handling, retry logic, and monitoring.
 */

import { GraphExportResponse, IngestRequest, IngestResponse, SearchRequest, SearchResponse, NeighborsRequest, NeighborsResponse, QuestionRequest, QuestionResponse } from '../types/api';
import { handleAsyncError, RetryManager } from './errorHandling';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

// Request timeout configuration
const DEFAULT_TIMEOUT = 30000; // 30 seconds
const LONG_TIMEOUT = 120000; // 2 minutes for long operations

interface RequestOptions {
  timeout?: number;
  retryKey?: string;
  signal?: AbortSignal;
}

/**
 * Enhanced fetch wrapper with error handling and timeout
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit & RequestOptions = {}
): Promise<T> {
  const { timeout = DEFAULT_TIMEOUT, retryKey, signal, ...fetchOptions } = options;
  
  // Create abort controller for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  // Combine signals if provided
  const combinedSignal = signal ? 
    AbortSignal.any([signal, controller.signal]) : 
    controller.signal;

  const requestOptions: RequestInit = {
    ...fetchOptions,
    signal: combinedSignal,
    headers: {
      'Content-Type': 'application/json',
      ...fetchOptions.headers,
    },
  };

  const operation = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, requestOptions);
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new APIError(
          errorData.message || `Request failed: ${response.status} ${response.statusText}`,
          response.status,
          errorData
        );
      }

      const data = await response.json();
      return data as T;
    } catch (error) {
      clearTimeout(timeoutId);
      
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new APIError('Request timeout', 408, { timeout: true });
      }
      
      throw error;
    }
  };

  if (retryKey) {
    return handleAsyncError(
      operation,
      retryKey,
      { endpoint, method: requestOptions.method || 'GET' }
    );
  } else {
    return handleAsyncError(
      operation,
      undefined,
      { endpoint, method: requestOptions.method || 'GET' }
    );
  }
}

/**
 * Custom API Error class
 */
export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

/**
 * Health check endpoint
 */
export async function checkHealth(): Promise<any> {
  return apiRequest('/health', {
    timeout: 5000,
    retryKey: 'health'
  });
}

/**
 * Get health metrics
 */
export async function getHealthMetrics(hours: number = 1): Promise<any> {
  return apiRequest(`/health/metrics?hours=${hours}`, {
    timeout: 10000
  });
}

/**
 * Get error statistics
 */
export async function getErrorStatistics(): Promise<any> {
  return apiRequest('/health/errors', {
    timeout: 10000
  });
}

/**
 * Ingest text and extract knowledge graph
 */
export async function ingestText(request: IngestRequest, signal?: AbortSignal): Promise<IngestResponse> {
  return apiRequest<IngestResponse>('/ingest', {
    method: 'POST',
    body: JSON.stringify(request),
    timeout: LONG_TIMEOUT,
    retryKey: 'api',
    signal
  });
}

/**
 * Search for entities using vector similarity
 */
export async function searchEntities(request: SearchRequest, signal?: AbortSignal): Promise<SearchResponse> {
  const params = new URLSearchParams({
    q: request.q,
    k: request.k?.toString() || '8'
  });
  
  return apiRequest<SearchResponse>(`/search?${params}`, {
    timeout: 10000,
    retryKey: 'api',
    signal
  });
}

/**
 * Get neighboring entities using graph traversal
 */
export async function getNeighbors(request: NeighborsRequest, signal?: AbortSignal): Promise<NeighborsResponse> {
  const params = new URLSearchParams({
    node_id: request.node_id,
    hops: request.hops?.toString() || '1',
    limit: request.limit?.toString() || '200'
  });
  
  return apiRequest<NeighborsResponse>(`/neighbors?${params}`, {
    timeout: 15000,
    retryKey: 'api',
    signal
  });
}

/**
 * Ask a question and get a grounded answer
 */
export async function askQuestion(request: QuestionRequest, signal?: AbortSignal): Promise<QuestionResponse> {
  const params = new URLSearchParams({
    q: request.q
  });
  
  return apiRequest<QuestionResponse>(`/ask?${params}`, {
    timeout: 30000,
    retryKey: 'api',
    signal
  });
}

/**
 * Export the complete knowledge graph as structured data
 */
export async function exportGraph(signal?: AbortSignal): Promise<GraphExportResponse> {
  return apiRequest<GraphExportResponse>('/graph/export', {
    timeout: 30000,
    retryKey: 'api',
    signal
  });
}

/**
 * Download data as a JSON file
 */
export function downloadAsJson(data: any, filename: string): void {
  try {
    const jsonString = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    
    // Cleanup
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } catch (error) {
    console.error('Error downloading file:', error);
    throw error;
  }
}

/**
 * Generate a filename for graph export with timestamp
 */
export function generateExportFilename(): string {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
  return `knowledge-graph-export-${timestamp}.json`;
}