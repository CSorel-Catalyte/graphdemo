/**
 * Connection status indicator component.
 * Shows the current WebSocket connection state with visual indicators.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { useStore } from '../store/useStore';

const ConnectionStatus: React.FC = () => {
  const { isConnected, connectionError } = useStore();

  const getStatusColor = () => {
    if (isConnected) return 'bg-green-500';
    if (connectionError?.includes('Connecting') || connectionError?.includes('Reconnecting')) {
      return 'bg-yellow-500';
    }
    return 'bg-red-500';
  };

  const getStatusText = () => {
    if (isConnected) return 'Connected';
    if (connectionError?.includes('Connecting')) return 'Connecting...';
    if (connectionError?.includes('Reconnecting')) return 'Reconnecting...';
    return 'Disconnected';
  };

  const isPulsing = !isConnected && (
    connectionError?.includes('Connecting') || 
    connectionError?.includes('Reconnecting')
  );

  return (
    <div className="flex items-center space-x-2">
      <motion.div
        className={`w-3 h-3 rounded-full ${getStatusColor()}`}
        animate={isPulsing ? { scale: [1, 1.2, 1] } : {}}
        transition={isPulsing ? { repeat: Infinity, duration: 1.5 } : {}}
      />
      <span className="text-sm text-gray-300">
        {getStatusText()}
      </span>
      {connectionError && !isConnected && (
        <div 
          className="text-xs text-red-400 max-w-xs truncate cursor-help" 
          title={connectionError}
        >
          {connectionError}
        </div>
      )}
    </div>
  );
};

export default ConnectionStatus;