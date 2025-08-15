/**
 * Tests for LoadTextButton component
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import LoadTextButton from '../LoadTextButton';
import * as apiUtils from '../../utils/api';

// Mock the API utils
vi.mock('../../utils/api', () => ({
  ingestText: vi.fn(),
}));

describe('LoadTextButton', () => {
  const mockIngestText = vi.mocked(apiUtils.ingestText);

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders load text button with correct text and icon', () => {
    render(<LoadTextButton />);
    
    expect(screen.getByRole('button', { name: /load text/i })).toBeInTheDocument();
    expect(screen.getByText('Load Text')).toBeInTheDocument();
  });

  it('opens file dialog when clicked', () => {
    render(<LoadTextButton />);
    
    const button = screen.getByRole('button', { name: /load text/i });
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    const clickSpy = vi.spyOn(fileInput, 'click').mockImplementation(() => {});
    
    fireEvent.click(button);
    
    expect(clickSpy).toHaveBeenCalled();
  });

  it('accepts only text files', () => {
    render(<LoadTextButton />);
    
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    expect(fileInput).toHaveAttribute('accept', '.txt,.md,.text');
  });

  it('has correct accessibility attributes', () => {
    render(<LoadTextButton />);
    
    const button = screen.getByRole('button', { name: /load text/i });
    
    expect(button).toHaveAttribute('title', 'Load text file and extract knowledge graph');
  });

  it('shows processing state when loading', async () => {
    mockIngestText.mockImplementation(() => new Promise(() => {})); // Never resolves
    
    render(<LoadTextButton />);
    
    const button = screen.getByRole('button');
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    // Create a mock file
    const file = new File(['test content'], 'test.txt', { type: 'text/plain' });
    
    // Mock FileReader
    const mockFileReader = {
      readAsText: vi.fn(),
      onload: null as any,
      onerror: null as any,
      result: 'test content'
    };
    
    vi.spyOn(window, 'FileReader').mockImplementation(() => mockFileReader as any);
    
    // Simulate file selection
    Object.defineProperty(fileInput, 'files', {
      value: [file],
      writable: false,
    });
    
    fireEvent.change(fileInput);
    
    // Simulate FileReader onload
    if (mockFileReader.onload) {
      mockFileReader.onload({ target: { result: 'test content' } } as any);
    }
    
    await waitFor(() => {
      expect(screen.getByText('Processing...')).toBeInTheDocument();
      expect(button).toBeDisabled();
    });
  });

  it('shows success message after successful processing', async () => {
    const mockResponse = {
      success: true,
      doc_id: 'test',
      chunks_processed: 2,
      entities_extracted: 5,
      relationships_extracted: 3,
      processing_time: 1.5,
      message: 'Success'
    };
    
    mockIngestText.mockResolvedValue(mockResponse);
    
    render(<LoadTextButton />);
    
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    // Create a mock file
    const file = new File(['test content'], 'test.txt', { type: 'text/plain' });
    
    // Mock FileReader
    const mockFileReader = {
      readAsText: vi.fn(),
      onload: null as any,
      onerror: null as any,
      result: 'test content'
    };
    
    vi.spyOn(window, 'FileReader').mockImplementation(() => mockFileReader as any);
    
    // Simulate file selection
    Object.defineProperty(fileInput, 'files', {
      value: [file],
      writable: false,
    });
    
    fireEvent.change(fileInput);
    
    // Simulate FileReader onload
    if (mockFileReader.onload) {
      mockFileReader.onload({ target: { result: 'test content' } } as any);
    }
    
    await waitFor(() => {
      expect(screen.getByText(/Processed 2 chunks, extracted 5 entities and 3 relationships/)).toBeInTheDocument();
    });
    
    expect(mockIngestText).toHaveBeenCalledWith({
      doc_id: 'test',
      text: 'test content'
    });
  });

  it('shows error message when processing fails', async () => {
    mockIngestText.mockRejectedValue(new Error('API Error'));
    
    render(<LoadTextButton />);
    
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    // Create a mock file
    const file = new File(['test content'], 'test.txt', { type: 'text/plain' });
    
    // Mock FileReader
    const mockFileReader = {
      readAsText: vi.fn(),
      onload: null as any,
      onerror: null as any,
      result: 'test content'
    };
    
    vi.spyOn(window, 'FileReader').mockImplementation(() => mockFileReader as any);
    
    // Simulate file selection
    Object.defineProperty(fileInput, 'files', {
      value: [file],
      writable: false,
    });
    
    fireEvent.change(fileInput);
    
    // Simulate FileReader onload
    if (mockFileReader.onload) {
      mockFileReader.onload({ target: { result: 'test content' } } as any);
    }
    
    await waitFor(() => {
      expect(screen.getByText(/Loading failed: API Error/)).toBeInTheDocument();
    });
  });
});