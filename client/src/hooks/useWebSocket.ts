/**
 * Enhanced WebSocket hook with comprehensive error handling and user notifications.
 * Integrates with the Zustand store for state updates and notification system for user feedback.
 */

import { useEffect, useRef, useCallback } from 'react';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import { useStore } from '../store/useStore';
import { WSMessage, ConnectionState } from '../types/websocket';
import { handleError } from '../utils/errorHandling';
import { useNotifications, useConnectionNotifications } from '../components/NotificationSystem';

const WS_URL = 'ws://localhost:8000/stream';
const RECONNECT_INTERVAL = 3000; // 3 seconds
const MAX_RECONNECT_ATTEMPTS = 10;

export const useKnowledgeMapperWebSocket = () => {
  const {
    upsertNodes,
    upsertEdges,
    setProcessing,
    setConnected,
  } = useStore();

  const { error, warning, info } = useNotifications();
  const { showConnectionLost, showConnectionRestored, showReconnecting } = useConnectionNotifications();

  const reconnectAttempts = useRef(0);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const hasShownConnectionLost = useRef(false);

  // WebSocket connection with automatic reconnection
  const {
    sendMessage,
    lastMessage,
    readyState,
    getWebSocket,
  } = useWebSocket(
    WS_URL,
    {
      onOpen: () => {
        console.log('WebSocket connected');
        reconnectAttempts.current = 0;
        setConnected(true);

        // Show connection restored notification if we were previously disconnected
        if (hasShownConnectionLost.current) {
          showConnectionRestored();
          hasShownConnectionLost.current = false;
        }

        // Clear any pending reconnection timeout
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      },
      onClose: (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        const reason = event.reason || 'Unknown reason';
        setConnected(false, `Connection closed: ${reason}`);

        // Show connection lost notification for unexpected disconnections
        if (event.code !== 1000 && !hasShownConnectionLost.current) {
          showConnectionLost();
          hasShownConnectionLost.current = true;
        }

        // Attempt to reconnect if not manually closed
        if (event.code !== 1000 && reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          scheduleReconnect();
        }
      },
      onError: (event) => {
        console.error('WebSocket error:', event);
        const errorInfo = handleError(new Error('WebSocket connection error'), {
          type: 'websocket',
          event: event
        });

        setConnected(false, 'Connection error occurred');

        if (!hasShownConnectionLost.current) {
          showConnectionLost();
          hasShownConnectionLost.current = true;
        }
      },
      onMessage: (event) => {
        try {
          const data = JSON.parse(event.data) as WSMessage;
          handleMessage(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
          handleError(error, {
            type: 'websocket',
            operation: 'message_parsing',
            rawData: event.data
          });
          warning('Message Error', 'Received invalid message from server');
        }
      },
      shouldReconnect: () => true,
      reconnectInterval: RECONNECT_INTERVAL,
      reconnectAttempts: MAX_RECONNECT_ATTEMPTS,
    }
  );

  // Schedule reconnection with exponential backoff
  const scheduleReconnect = useCallback(() => {
    if (reconnectAttempts.current >= MAX_RECONNECT_ATTEMPTS) {
      console.log('Max reconnection attempts reached');
      setConnected(false, 'Max reconnection attempts reached');
      error('Connection Failed', 'Unable to reconnect to the server. Please refresh the page.', {
        persistent: true,
        actions: [
          {
            label: 'Refresh Page',
            action: () => window.location.reload(),
            style: 'primary'
          }
        ]
      });
      return;
    }

    const delay = Math.min(RECONNECT_INTERVAL * Math.pow(2, reconnectAttempts.current), 30000);
    reconnectAttempts.current += 1;

    console.log(`Scheduling reconnection attempt ${reconnectAttempts.current} in ${delay}ms`);

    // Show reconnecting notification
    if (reconnectAttempts.current === 1) {
      showReconnecting();
    }

    reconnectTimeoutRef.current = setTimeout(() => {
      console.log(`Reconnection attempt ${reconnectAttempts.current}`);
      // The useWebSocket hook handles the actual reconnection
    }, delay);
  }, [setConnected, error, showReconnecting]);

  // Handle incoming WebSocket messages
  const handleMessage = useCallback((message: WSMessage) => {
    console.log('Received WebSocket message:', message);

    switch (message.type) {
      case 'upsert_nodes':
        console.log('Processing nodes:', message.nodes);
        upsertNodes(message.nodes);
        break;

      case 'upsert_edges':
        console.log('Processing edges:', message.edges);
        // Add a small delay to ensure nodes are processed first
        setTimeout(() => {
          upsertEdges(message.edges);
        }, 100);
        break;

      case 'status':
        setProcessing(
          true,
          message.stage,
          message.total ? (message.count / message.total) * 100 : 0
        );

        // If processing is complete, clear the processing state after a short delay
        if (message.stage.toLowerCase().includes('complete') ||
          message.stage.toLowerCase().includes('finished')) {
          setTimeout(() => {
            setProcessing(false);
          }, 2000);
        }
        break;

      case 'error':
        console.error('WebSocket error message:', message.error, message.message);
        setConnected(false, `Server error: ${message.message}`);
        break;

      case 'connection':
        console.log('Connection status:', message.status);
        if (message.status === 'connected') {
          setConnected(true);
        }
        break;

      default:
        console.warn('Unknown WebSocket message type:', message);
    }
  }, [upsertNodes, upsertEdges, setProcessing, setConnected]);

  // Get connection state
  const getConnectionState = useCallback((): ConnectionState => {
    switch (readyState) {
      case ReadyState.CONNECTING:
        return ConnectionState.CONNECTING;
      case ReadyState.OPEN:
        return ConnectionState.CONNECTED;
      case ReadyState.CLOSING:
      case ReadyState.CLOSED:
        return reconnectAttempts.current > 0 && reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS
          ? ConnectionState.RECONNECTING
          : ConnectionState.DISCONNECTED;
      default:
        return ConnectionState.ERROR;
    }
  }, [readyState]);

  // Manual connection control
  const connect = useCallback(() => {
    reconnectAttempts.current = 0;
    const ws = getWebSocket();
    if (ws && ws.readyState === WebSocket.CLOSED) {
      // Force reconnection by creating a new WebSocket instance
      window.location.reload(); // Simple approach for demo
    }
  }, [getWebSocket]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    reconnectAttempts.current = MAX_RECONNECT_ATTEMPTS; // Prevent auto-reconnection
    const ws = getWebSocket();
    if (ws) {
      ws.close(1000, 'Manual disconnect');
    }
    setConnected(false);
  }, [getWebSocket, setConnected]);

  // Send message helper
  const sendWSMessage = useCallback((message: any) => {
    if (readyState === ReadyState.OPEN) {
      sendMessage(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, cannot send message:', message);
    }
  }, [sendMessage, readyState]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  return {
    connectionState: getConnectionState(),
    lastMessage: lastMessage ? JSON.parse(lastMessage.data) as WSMessage : null,
    sendMessage: sendWSMessage,
    connect,
    disconnect,
    isConnected: readyState === ReadyState.OPEN,
    isConnecting: readyState === ReadyState.CONNECTING,
    reconnectAttempts: reconnectAttempts.current,
  };
};