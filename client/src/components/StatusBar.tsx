/**
 * Status bar component showing processing status and graph statistics.
 * Displays connection status, processing progress, and node/edge counts.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { useStore, useConnectionStatus, useProcessingStatus } from '../store/useStore';

const StatusBar: React.FC = () => {
  const { nodes, edges } = useStore();
  const { isConnected } = useConnectionStatus();
  const { isProcessing, processingStage, processingProgress } = useProcessingStatus();
  
  const nodeCount = nodes.size;
  const edgeCount = edges.size;

  return (
    <footer className="bg-gray-800 border-t border-gray-700 px-4 py-2">
      <div className="flex items-center justify-between text-sm">
        {/* Left side - Processing status */}
        <div className="flex items-center space-x-4">
          {isProcessing ? (
            <motion.div 
              className="flex items-center space-x-2"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
              <span className="text-blue-400">
                {processingStage || 'Processing...'}
              </span>
              {processingProgress > 0 && (
                <div className="w-32 bg-gray-700 rounded-full h-2">
                  <motion.div 
                    className="bg-blue-500 h-2 rounded-full"
                    initial={{ width: 0 }}
                    animate={{ width: `${processingProgress}%` }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
              )}
            </motion.div>
          ) : (
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-green-500' : 'bg-red-500'
              }`}></div>
              <span className="text-gray-400">
                {isConnected ? 'Ready' : 'Disconnected'}
              </span>
            </div>
          )}
        </div>
        
        {/* Center - Graph statistics */}
        <div className="flex items-center space-x-6 text-gray-400">
          <div className="flex items-center space-x-1">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <circle cx="10" cy="10" r="3" />
            </svg>
            <span>{nodeCount} nodes</span>
          </div>
          <div className="flex items-center space-x-1">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
            <span>{edgeCount} edges</span>
          </div>
        </div>
        
        {/* Right side - Additional info */}
        <div className="text-gray-500 text-xs">
          AI Knowledge Mapper v0.1.0
        </div>
      </div>
    </footer>
  );
};

export default StatusBar;