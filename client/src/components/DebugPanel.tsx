/**
 * Debug panel component for testing WebSocket functionality.
 * This component provides controls to test real-time data synchronization.
 * Only shown in development mode.
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../store/useStore';
import { useKnowledgeMapperWebSocket } from '../hooks/useWebSocket';
import { testWebSocketConnection, simulateProcessingWorkflow, validateStoreState } from '../utils/testWebSocket';

const DebugPanel: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const { nodes, edges, clearGraph } = useStore();
  const { sendMessage, isConnected, connectionState, reconnectAttempts } = useKnowledgeMapperWebSocket();

  // Only show in development (for now, always show for demo purposes)
  // if (process.env.NODE_ENV === 'production') {
  //   return null;
  // }

  const handleTestConnection = () => {
    testWebSocketConnection(sendMessage);
  };

  const handleSimulateWorkflow = () => {
    simulateProcessingWorkflow(sendMessage);
  };

  const handleValidateState = () => {
    const result = validateStoreState(nodes, edges);
    alert(`Store validation:\nNodes: ${result.nodeCount}\nEdges: ${result.edgeCount}\nValid: ${result.isValid}`);
  };

  const handleClearGraph = () => {
    clearGraph();
    console.log('Graph cleared');
  };

  return (
    <>
      {/* Debug toggle button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-4 right-4 z-50 bg-purple-600 hover:bg-purple-700 text-white p-3 rounded-full shadow-lg transition-colors"
        title="Toggle Debug Panel"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </button>

      {/* Debug panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed top-0 right-0 bottom-0 w-80 bg-gray-800 border-l border-gray-700 shadow-xl z-40 overflow-y-auto"
          >
            <div className="p-4">
              {/* Header */}
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">Debug Panel</h3>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-1 hover:bg-gray-700 rounded transition-colors text-gray-400"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Connection Status */}
              <div className="mb-6">
                <h4 className="text-sm font-medium text-gray-300 mb-2">Connection Status</h4>
                <div className="bg-gray-700 rounded p-3 text-sm">
                  <div className="flex items-center space-x-2 mb-1">
                    <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                    <span className="text-white">State: {connectionState}</span>
                  </div>
                  <div className="text-gray-400">
                    Reconnect attempts: {reconnectAttempts}
                  </div>
                </div>
              </div>

              {/* Store State */}
              <div className="mb-6">
                <h4 className="text-sm font-medium text-gray-300 mb-2">Store State</h4>
                <div className="bg-gray-700 rounded p-3 text-sm">
                  <div className="text-white mb-1">Nodes: {nodes.size}</div>
                  <div className="text-white">Edges: {edges.size}</div>
                </div>
              </div>

              {/* Test Controls */}
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-gray-300">Test Controls</h4>
                
                <button
                  onClick={handleTestConnection}
                  disabled={!isConnected}
                  className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white py-2 px-3 rounded text-sm transition-colors"
                >
                  Test Connection
                </button>

                <button
                  onClick={handleSimulateWorkflow}
                  disabled={!isConnected}
                  className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white py-2 px-3 rounded text-sm transition-colors"
                >
                  Simulate Workflow
                </button>

                <button
                  onClick={handleValidateState}
                  className="w-full bg-yellow-600 hover:bg-yellow-700 text-white py-2 px-3 rounded text-sm transition-colors"
                >
                  Validate State
                </button>

                <button
                  onClick={handleClearGraph}
                  className="w-full bg-red-600 hover:bg-red-700 text-white py-2 px-3 rounded text-sm transition-colors"
                >
                  Clear Graph
                </button>
              </div>

              {/* Instructions */}
              <div className="mt-6 text-xs text-gray-400">
                <p className="mb-2">
                  <strong>Test Connection:</strong> Sends a ping message to verify WebSocket connectivity.
                </p>
                <p className="mb-2">
                  <strong>Simulate Workflow:</strong> Sends mock nodes, edges, and status updates to test real-time synchronization.
                </p>
                <p className="mb-2">
                  <strong>Validate State:</strong> Checks current store state and logs details to console.
                </p>
                <p>
                  <strong>Clear Graph:</strong> Removes all nodes and edges from the store.
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default DebugPanel;