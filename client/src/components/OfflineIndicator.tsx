/**
 * Offline indicator component that shows when the app is running in offline mode.
 * Displays a clear visual indicator that the app is using cached data.
 */

import React from 'react';
import { useStore } from '../store/useStore';

interface OfflineIndicatorProps {
  className?: string;
}

const OfflineIndicator: React.FC<OfflineIndicatorProps> = ({ className = '' }) => {
  const { isOfflineMode, offlineData, isConnected } = useStore();

  // Show indicator if in offline mode or if not connected
  const showIndicator = isOfflineMode || !isConnected;
  
  if (!showIndicator) return null;

  const nodeCount = offlineData?.nodes?.length || 0;
  const edgeCount = offlineData?.edges?.length || 0;

  return (
    <div className={`
      flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium
      ${isOfflineMode 
        ? 'bg-amber-600 text-white' 
        : 'bg-red-600 text-white'
      }
      ${className}
    `}>
      {/* Icon */}
      <svg className="h-4 w-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        {isOfflineMode ? (
          // Offline mode icon (cloud with slash)
          <path 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth={2} 
            d="M3 3l18 18M8.5 8.5A5.5 5.5 0 0118 13h1a3 3 0 01-1.5 2.6M12 12v6m0 0l-3-3m3 3l3-3" 
          />
        ) : (
          // Disconnected icon (wifi off)
          <path 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth={2} 
            d="M18.364 5.636l-12.728 12.728m0 0L12 12m-6.364 6.364a9 9 0 010-12.728m12.728 0a9 9 0 010 12.728" 
          />
        )}
      </svg>
      
      {/* Status text */}
      <span>
        {isOfflineMode 
          ? `Offline Mode (${nodeCount} nodes, ${edgeCount} edges)`
          : 'Disconnected'
        }
      </span>
      
      {/* Pulse indicator for disconnected state */}
      {!isConnected && !isOfflineMode && (
        <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
      )}
    </div>
  );
};

export default OfflineIndicator;