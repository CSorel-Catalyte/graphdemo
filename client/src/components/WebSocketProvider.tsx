/**
 * WebSocket provider component that manages the global WebSocket connection.
 * This component should wrap the entire application to provide WebSocket functionality.
 */

import React, { useEffect } from 'react';
import { useKnowledgeMapperWebSocket } from '../hooks/useWebSocket';
import { useStore } from '../store/useStore';
import { useOfflineMode } from '../hooks/useOfflineMode';
import { ConnectionState } from '../types/websocket';

interface WebSocketProviderProps {
  children: React.ReactNode;
}

const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const { connectionState, isConnected, reconnectAttempts } = useKnowledgeMapperWebSocket();
  const { setConnected, isOfflineMode } = useStore();
  const { checkConnectivity } = useOfflineMode();

  // Update store connection state based on WebSocket state, but respect offline mode
  useEffect(() => {
    // Don't update connection state if in offline mode
    if (isOfflineMode) return;
    
    let errorMessage: string | null = null;
    
    switch (connectionState) {
      case ConnectionState.CONNECTED:
        setConnected(true);
        break;
      case ConnectionState.CONNECTING:
        setConnected(false, 'Connecting to server...');
        break;
      case ConnectionState.RECONNECTING:
        setConnected(false, `Reconnecting... (attempt ${reconnectAttempts})`);
        break;
      case ConnectionState.DISCONNECTED:
        errorMessage = reconnectAttempts > 0 
          ? 'Connection lost - unable to reconnect' 
          : 'Disconnected from server';
        setConnected(false, errorMessage);
        break;
      case ConnectionState.ERROR:
        setConnected(false, 'Connection error');
        break;
    }
  }, [connectionState, reconnectAttempts, setConnected, isOfflineMode]);

  // Log connection state changes for debugging
  useEffect(() => {
    console.log(`WebSocket connection state: ${connectionState}`, {
      isConnected,
      reconnectAttempts,
    });
  }, [connectionState, isConnected, reconnectAttempts]);

  return <>{children}</>;
};

export default WebSocketProvider;