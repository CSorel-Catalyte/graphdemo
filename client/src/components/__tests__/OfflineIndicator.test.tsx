/**
 * Tests for OfflineIndicator component
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import OfflineIndicator from '../OfflineIndicator';
import { useStore } from '../../store/useStore';

// Mock the store
vi.mock('../../store/useStore', () => ({
  useStore: vi.fn(),
}));

describe('OfflineIndicator', () => {
  const mockUseStore = vi.mocked(useStore);

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not render when connected and not in offline mode', () => {
    mockUseStore.mockReturnValue({
      isOfflineMode: false,
      isConnected: true,
      offlineData: null,
    } as any);

    const { container } = render(<OfflineIndicator />);
    expect(container.firstChild).toBeNull();
  });

  it('renders offline mode indicator when in offline mode', () => {
    mockUseStore.mockReturnValue({
      isOfflineMode: true,
      isConnected: false,
      offlineData: {
        nodes: [{ id: '1' }, { id: '2' }],
        edges: [{ id: 'edge1' }],
      },
    } as any);

    render(<OfflineIndicator />);
    
    expect(screen.getByText('Offline Mode (2 nodes, 1 edges)')).toBeInTheDocument();
  });

  it('renders disconnected indicator when not connected', () => {
    mockUseStore.mockReturnValue({
      isOfflineMode: false,
      isConnected: false,
      offlineData: null,
    } as any);

    render(<OfflineIndicator />);
    
    expect(screen.getByText('Disconnected')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    mockUseStore.mockReturnValue({
      isOfflineMode: true,
      isConnected: false,
      offlineData: { nodes: [], edges: [] },
    } as any);

    render(<OfflineIndicator className="custom-class" />);
    
    const indicator = screen.getByText(/offline mode/i).parentElement;
    expect(indicator).toHaveClass('custom-class');
  });
});