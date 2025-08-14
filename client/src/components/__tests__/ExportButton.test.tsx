/**
 * Tests for ExportButton component
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import ExportButton from '../ExportButton';
import * as apiUtils from '../../utils/api';

// Mock the API utilities
vi.mock('../../utils/api', () => ({
  exportGraph: vi.fn(),
  downloadAsJson: vi.fn(),
  generateExportFilename: vi.fn(() => 'test-export-2024-01-01T12-00-00.json'),
}));

describe('ExportButton', () => {
  const mockExportGraph = vi.mocked(apiUtils.exportGraph);
  const mockDownloadAsJson = vi.mocked(apiUtils.downloadAsJson);
  const mockGenerateExportFilename = vi.mocked(apiUtils.generateExportFilename);

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  it('renders export button with correct text and icon', () => {
    render(<ExportButton />);
    
    expect(screen.getByRole('button', { name: /export/i })).toBeInTheDocument();
    expect(screen.getByText('Export')).toBeInTheDocument();
  });

  it('shows loading state when exporting', async () => {
    // Mock a delayed response
    mockExportGraph.mockImplementation(() => 
      new Promise(resolve => setTimeout(() => resolve({
        nodes: [],
        edges: [],
        metadata: {},
        export_timestamp: '2024-01-01T12:00:00Z',
        total_nodes: 0,
        total_edges: 0,
      }), 100))
    );

    render(<ExportButton />);
    
    const button = screen.getByRole('button', { name: /export/i });
    fireEvent.click(button);

    // Should show loading state
    expect(screen.getByText('Exporting...')).toBeInTheDocument();
    expect(button).toBeDisabled();

    // Wait for export to complete
    await waitFor(() => {
      expect(screen.getByText('Export')).toBeInTheDocument();
    });
  });

  it('successfully exports graph data', async () => {
    const mockGraphData = {
      nodes: [
        {
          id: 'test-node-1',
          name: 'Test Node',
          type: 'Concept',
          aliases: [],
          embedding: [],
          salience: 0.8,
          source_spans: [],
          summary: 'Test summary',
          created_at: '2024-01-01T12:00:00Z',
          updated_at: '2024-01-01T12:00:00Z',
        }
      ],
      edges: [],
      metadata: { test: true },
      export_timestamp: '2024-01-01T12:00:00Z',
      total_nodes: 1,
      total_edges: 0,
    };

    mockExportGraph.mockResolvedValue(mockGraphData);

    render(<ExportButton />);
    
    const button = screen.getByRole('button', { name: /export/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(mockExportGraph).toHaveBeenCalledTimes(1);
      expect(mockGenerateExportFilename).toHaveBeenCalledTimes(1);
      expect(mockDownloadAsJson).toHaveBeenCalledWith(
        mockGraphData,
        'test-export-2024-01-01T12-00-00.json'
      );
    });

    // Should show success message
    await waitFor(() => {
      expect(screen.getByText('Exported 1 nodes and 0 edges')).toBeInTheDocument();
    });
  });

  it('handles export errors gracefully', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    mockExportGraph.mockRejectedValue(new Error('Network error'));

    render(<ExportButton />);
    
    const button = screen.getByRole('button', { name: /export/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText('Export failed. Please try again.')).toBeInTheDocument();
    });

    expect(consoleErrorSpy).toHaveBeenCalledWith('Export failed:', expect.any(Error));
    consoleErrorSpy.mockRestore();
  });

  it('prevents multiple simultaneous exports', async () => {
    mockExportGraph.mockImplementation(() => 
      new Promise(resolve => setTimeout(() => resolve({
        nodes: [],
        edges: [],
        metadata: {},
        export_timestamp: '2024-01-01T12:00:00Z',
        total_nodes: 0,
        total_edges: 0,
      }), 100))
    );

    render(<ExportButton />);
    
    const button = screen.getByRole('button', { name: /export/i });
    
    // Click multiple times
    fireEvent.click(button);
    fireEvent.click(button);
    fireEvent.click(button);

    // Should only call export once
    await waitFor(() => {
      expect(mockExportGraph).toHaveBeenCalledTimes(1);
    });
  });

  it('applies custom className', () => {
    render(<ExportButton className="custom-class" />);
    
    const container = screen.getByRole('button', { name: /export/i }).parentElement;
    expect(container).toHaveClass('custom-class');
  });

  it('has correct accessibility attributes', () => {
    render(<ExportButton />);
    
    const button = screen.getByRole('button', { name: /export/i });
    expect(button).toHaveAttribute('title', 'Export knowledge graph as JSON file');
  });
});