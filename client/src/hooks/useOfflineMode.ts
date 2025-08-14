/**
 * Hook for managing offline mode detection and state.
 * Provides functionality to detect network connectivity and manage offline mode.
 */

import { useEffect, useCallback } from 'react';
import { useStore } from '../store/useStore';

export const useOfflineMode = () => {
  const { 
    isOfflineMode, 
    isConnected, 
    setOfflineMode, 
    setConnected 
  } = useStore();

  // Check if the browser supports online/offline detection
  const supportsOnlineDetection = typeof navigator !== 'undefined' && 'onLine' in navigator;

  // Handle online/offline events
  const handleOnline = useCallback(() => {
    if (!isOfflineMode) {
      setConnected(true);
    }
  }, [isOfflineMode, setConnected]);

  const handleOffline = useCallback(() => {
    if (!isOfflineMode) {
      setConnected(false, 'Network connection lost');
    }
  }, [isOfflineMode, setConnected]);

  // Test backend connectivity
  const testBackendConnectivity = useCallback(async (): Promise<boolean> => {
    try {
      const response = await fetch('/api/health', {
        method: 'GET',
        timeout: 5000, // 5 second timeout
      } as RequestInit);
      
      return response.ok;
    } catch (error) {
      console.warn('Backend connectivity test failed:', error);
      return false;
    }
  }, []);

  // Enter offline mode with optional data
  const enterOfflineMode = useCallback((data?: { nodes: any[]; edges: any[]; metadata?: any }) => {
    setOfflineMode(true, data);
  }, [setOfflineMode]);

  // Exit offline mode and attempt to reconnect
  const exitOfflineMode = useCallback(async () => {
    // Test if backend is available
    const isBackendAvailable = await testBackendConnectivity();
    
    if (isBackendAvailable) {
      setOfflineMode(false);
      setConnected(true);
    } else {
      setConnected(false, 'Backend not available');
    }
  }, [setOfflineMode, setConnected, testBackendConnectivity]);

  // Check connectivity status
  const checkConnectivity = useCallback(async () => {
    if (isOfflineMode) return false;
    
    // Check browser online status
    if (supportsOnlineDetection && !navigator.onLine) {
      setConnected(false, 'No network connection');
      return false;
    }
    
    // Test backend connectivity
    const isBackendAvailable = await testBackendConnectivity();
    setConnected(isBackendAvailable, isBackendAvailable ? null : 'Backend not available');
    
    return isBackendAvailable;
  }, [isOfflineMode, supportsOnlineDetection, setConnected, testBackendConnectivity]);

  // Set up event listeners for online/offline detection
  useEffect(() => {
    if (!supportsOnlineDetection) return;

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Initial connectivity check
    if (navigator.onLine && !isConnected && !isOfflineMode) {
      checkConnectivity();
    }

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [supportsOnlineDetection, handleOnline, handleOffline, isConnected, isOfflineMode, checkConnectivity]);

  // Periodic connectivity check (every 30 seconds when not connected)
  useEffect(() => {
    if (isConnected || isOfflineMode) return;

    const interval = setInterval(() => {
      checkConnectivity();
    }, 30000); // 30 seconds

    return () => clearInterval(interval);
  }, [isConnected, isOfflineMode, checkConnectivity]);

  return {
    isOfflineMode,
    isConnected,
    supportsOnlineDetection,
    enterOfflineMode,
    exitOfflineMode,
    checkConnectivity,
    testBackendConnectivity,
  };
};