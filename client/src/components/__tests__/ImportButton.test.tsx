/**
 * Tests for ImportButton component
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import ImportButton from '../ImportButton';
import { useStore } from '../../store/useStore';

// Mock the store
vi.mock('../../store/useStore', () => ({
  useStore: vi.fn(),
}));

describe('ImportButton', () => {
  const mockImportGraphData = vi.fn();
  const mockUseStore = vi.mocked(useStore);

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseStore.mockReturnValue({
      importGraphData: mockImportGraphData,
    } as any);
  });

  it('renders import button with correct text and icon', () => {
    render(<ImportButton />);
    
    expect(screen.getByRole('button', { name: /import/i })).toBeInTheDocument();
    expect(screen.getByText('Import')).toBeInTheDocument();
  });

  it('opens file dialog when clicked', () => {
    render(<ImportButton />);
    
    const button = screen.getByRole('button', { name: /import/i });
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    const clickSpy = vi.spyOn(fileInput, 'click').mockImplementation(() => {});
    
    fireEvent.click(button);
    
    expect(clickSpy).toHaveBeenCalledTimes(1);
    clickSpy.mockRestore();
  });

  it('accepts only JSON files', () => {
    render(<ImportButton />);
    
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).toHaveAttribute('accept', '.json');
  });

  it('has correct accessibility attributes', () => {
    render(<ImportButton />);
    
    const button = screen.getByRole('button', { name: /import/i });
    expect(button).toHaveAttribute('title', 'Import knowledge graph from JSON file');
  });
});