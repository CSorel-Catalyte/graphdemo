/**
 * Tests for useOfflineMode hook
 */

import { renderHook, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { useOfflineMode } from '../useOfflineMode';
import { useStore } from '../../store/useStore';

// Mock the store
vi.mock('../../store/useStore', () => ({
  useStore: vi.fn(),
}));

// Mock fetch
global.fetch = vi.fn();

describe('useOfflineMode', () => {
  const mockSetOfflineMode = vi.fn();
  const mockSetConnected = vi.fn();
  const mockUseStore = vi.mocked(useStore);
  const mockFetch = vi.mocked(fetch);

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseStore.mockReturnValue({
      isOfflineMode: false,
      isConnected: true,
      setOfflineMode: mockSetOfflineMode,
      setConnected: mockSetConnected,
    } as any);

    // Mock navigator.onLine
    Object.defineProperty(navigator, 'onLine', {
      writable: true,
      value: true,
    });
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  it('returns offline mode state and functions', () => {
    const { result } = renderHook(() => useOfflineMode());

    expect(result.current).toHaveProperty('isOfflineMode');
    expect(result.current).toHaveProperty('isConnected');
    expect(result.current).toHaveProperty('enterOfflineMode');
    expect(result.current).toHaveProperty('exitOfflineMode');
    expect(result.current).toHaveProperty('checkConnectivity');
    expect(result.current).toHaveProperty('testBackendConnectivity');
  });

  it('enters offline mode with data', () => {
    const { result } = renderHook(() => useOfflineMode());
    const testData = { nodes: [], edges: [], metadata: {} };

    act(() => {
      result.current.enterOfflineMode(testData);
    });

    expect(mockSetOfflineMode).toHaveBeenCalledWith(true, testData);
  });

  it('tests backend connectivity', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
    } as Response);

    const { result } = renderHook(() => useOfflineMode());

    const isConnected = await act(async () => {
      return result.current.testBackendConnectivity();
    });

    expect(isConnected).toBe(true);
    expect(mockFetch).toHaveBeenCalledWith('/api/health', expect.any(Object));
  });

  it('handles backend connectivity failure', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(() => useOfflineMode());

    const isConnected = await act(async () => {
      return result.current.testBackendConnectivity();
    });

    expect(isConnected).toBe(false);
  });
});