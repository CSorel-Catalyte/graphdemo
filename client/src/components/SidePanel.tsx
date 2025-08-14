/**
 * Side panel component for displaying node details, search results, and Q&A results.
 * Implements smooth animations with Framer Motion and provides detailed information
 * about selected entities including evidence quotes and neighborhood expansion.
 */

import React, { useState, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore, useSelectedNode } from '../store/useStore';
import { NeighborsResponse } from '../types/api';


interface SidePanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const SidePanel: React.FC<SidePanelProps> = ({ isOpen, onClose }) => {
  const {
    sidePanelContent,
    searchResults,
    currentQuestion,
    currentAnswer,
    currentCitations,
    upsertNodes,
    upsertEdges,
    edges,
  } = useStore();
  
  const selectedNode = useSelectedNode();
  const [isExpanding, setIsExpanding] = useState(false);
  const [expandError, setExpandError] = useState<string | null>(null);

  // Get evidence quotes from relationships involving the selected node
  const nodeEvidence = useMemo(() => {
    if (!selectedNode) return [];
    
    const evidence: Array<{ quote: string; doc_id: string; predicate: string; confidence: number }> = [];
    
    // Find all edges that involve this node and extract their evidence
    edges.forEach((edge) => {
      if (edge.source === selectedNode.id || edge.target === selectedNode.id) {
        // Add evidence from this relationship
        if (edge.evidence && edge.evidence.length > 0) {
          edge.evidence.forEach((evidenceItem) => {
            evidence.push({
              quote: evidenceItem.quote,
              doc_id: evidenceItem.doc_id,
              predicate: edge.predicate,
              confidence: edge.confidence
            });
          });
        }
      }
    });
    
    // Sort by confidence and limit to top 5
    return evidence
      .sort((a, b) => b.confidence - a.confidence)
      .slice(0, 5);
  }, [selectedNode, edges]);

  // Handle expanding node neighborhood
  const handleExpandNeighborhood = useCallback(async (nodeId: string) => {
    if (!nodeId || isExpanding) return;
    
    setIsExpanding(true);
    setExpandError(null);
    
    try {
      const response = await fetch(`/neighbors?node_id=${nodeId}&hops=1&limit=200`);
      
      if (!response.ok) {
        throw new Error(`Failed to expand neighborhood: ${response.statusText}`);
      }
      
      const data: NeighborsResponse = await response.json();
      
      // Update store with new nodes and edges
      upsertNodes(data.neighbors);
      upsertEdges(data.relationships);
      
    } catch (error) {
      console.error('Error expanding neighborhood:', error);
      setExpandError(error instanceof Error ? error.message : 'Failed to expand neighborhood');
    } finally {
      setIsExpanding(false);
    }
  }, [isExpanding, upsertNodes, upsertEdges]);

  // Render node details content
  const renderNodeDetails = () => {
    if (!selectedNode) return null;

    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        transition={{ duration: 0.3 }}
        className="space-y-6"
      >
        {/* Node header */}
        <div className="border-b border-gray-700 pb-4">
          <div className="flex items-start justify-between mb-2">
            <h3 className="text-xl font-bold text-white truncate pr-2">
              {selectedNode.name}
            </h3>
            <span className={`px-2 py-1 text-xs rounded-full font-medium ${getTypeColor(selectedNode.type)}`}>
              {selectedNode.type}
            </span>
          </div>
          
          {/* Aliases */}
          {selectedNode.aliases && selectedNode.aliases.length > 0 && (
            <div className="mb-2">
              <span className="text-sm text-gray-400">Also known as: </span>
              <span className="text-sm text-gray-300">
                {selectedNode.aliases.join(', ')}
              </span>
            </div>
          )}
          
          {/* Metrics */}
          <div className="flex items-center space-x-4 text-sm text-gray-400">
            <div>
              <span className="font-medium">Salience:</span>{' '}
              <span className="text-white">{(selectedNode.salience * 100).toFixed(1)}%</span>
            </div>
            <div>
              <span className="font-medium">Evidence:</span>{' '}
              <span className="text-white">{selectedNode.evidence_count}</span>
            </div>
          </div>
        </div>

        {/* Summary */}
        <div>
          <h4 className="text-sm font-semibold text-gray-300 mb-2">Summary</h4>
          <p className="text-gray-200 text-sm leading-relaxed">
            {selectedNode.summary || 'No summary available'}
          </p>
        </div>

        {/* Evidence quotes */}
        <div>
          <h4 className="text-sm font-semibold text-gray-300 mb-2">Evidence Quotes</h4>
          <div className="space-y-3">
            {nodeEvidence.length > 0 ? (
              nodeEvidence.map((evidence, index) => (
                <motion.div
                  key={`evidence-${index}`}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="bg-gray-800 rounded-lg p-3 border-l-4 border-blue-500"
                >
                  <p className="text-gray-200 text-sm italic mb-2">
                    "{evidence.quote.length > 200 ? evidence.quote.substring(0, 200) + '...' : evidence.quote}"
                  </p>
                  <div className="flex items-center justify-between text-xs text-gray-400">
                    <span>Source: {evidence.doc_id}</span>
                    <div className="flex items-center space-x-2">
                      <span className="px-2 py-1 bg-gray-700 rounded text-xs">
                        {evidence.predicate}
                      </span>
                      <span>Confidence: {(evidence.confidence * 100).toFixed(1)}%</span>
                    </div>
                  </div>
                </motion.div>
              ))
            ) : (
              <div className="bg-gray-800 rounded-lg p-3 border-l-4 border-gray-600">
                <p className="text-gray-400 text-sm italic">
                  No evidence quotes available. Expand the neighborhood to load relationships with evidence.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Expand neighborhood */}
        <div>
          <h4 className="text-sm font-semibold text-gray-300 mb-3">Neighborhood</h4>
          <button
            onClick={() => handleExpandNeighborhood(selectedNode.id)}
            disabled={isExpanding}
            className={`w-full px-4 py-2 rounded-lg font-medium text-sm transition-all ${
              isExpanding
                ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 text-white hover:shadow-lg'
            }`}
          >
            {isExpanding ? (
              <div className="flex items-center justify-center space-x-2">
                <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
                <span>Expanding...</span>
              </div>
            ) : (
              'Expand 1-hop Neighborhood'
            )}
          </button>
          
          {expandError && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="mt-2 p-2 bg-red-900/50 border border-red-700 rounded text-red-200 text-xs"
            >
              {expandError}
            </motion.div>
          )}
        </div>
      </motion.div>
    );
  };

  // Render search results content
  const renderSearchResults = () => {
    if (!searchResults || searchResults.length === 0) return null;

    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        transition={{ duration: 0.3 }}
        className="space-y-4"
      >
        <h3 className="text-lg font-semibold text-white">Search Results</h3>
        <div className="space-y-3">
          {searchResults.map((result, index) => (
            <motion.div
              key={result.entity.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="bg-gray-800 rounded-lg p-3 hover:bg-gray-750 transition-colors cursor-pointer"
              onClick={() => {
                // Select the node when clicked
                useStore.getState().selectNode(result.entity.id);
              }}
            >
              <div className="flex items-start justify-between mb-2">
                <h4 className="font-medium text-white truncate pr-2">
                  {result.entity.name}
                </h4>
                <span className={`px-2 py-1 text-xs rounded-full font-medium ${getTypeColor(result.entity.type)}`}>
                  {result.entity.type}
                </span>
              </div>
              <p className="text-sm text-gray-300 mb-2 line-clamp-2">
                {result.entity.summary}
              </p>
              <div className="flex items-center justify-between text-xs text-gray-400">
                <span>Score: {(result.score * 100).toFixed(1)}%</span>
                <span>Salience: {(result.entity.salience * 100).toFixed(1)}%</span>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>
    );
  };

  // Render Q&A results content
  const renderQAResults = () => {
    if (!currentAnswer) return null;

    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        transition={{ duration: 0.3 }}
        className="space-y-4"
      >
        <h3 className="text-lg font-semibold text-white">Answer</h3>
        
        {/* Question */}
        <div className="bg-gray-800 rounded-lg p-3 border-l-4 border-blue-500">
          <h4 className="text-sm font-semibold text-gray-300 mb-1">Question</h4>
          <p className="text-gray-200 text-sm">{currentQuestion}</p>
        </div>

        {/* Answer */}
        <div className="bg-gray-800 rounded-lg p-3 border-l-4 border-green-500">
          <h4 className="text-sm font-semibold text-gray-300 mb-2">Answer</h4>
          <p className="text-gray-200 text-sm leading-relaxed whitespace-pre-wrap">
            {currentAnswer}
          </p>
        </div>

        {/* Citations */}
        {currentCitations && currentCitations.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-gray-300 mb-3">Citations</h4>
            <div className="space-y-2">
              {currentCitations.map((citation, index) => (
                <motion.div
                  key={`${citation.node_id}-${index}`}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="bg-gray-800 rounded-lg p-3 hover:bg-gray-750 transition-colors cursor-pointer"
                  onClick={() => {
                    // Navigate to the cited node
                    useStore.getState().selectNode(citation.node_id);
                  }}
                >
                  <p className="text-sm text-gray-200 italic mb-2">
                    "{citation.quote}"
                  </p>
                  <div className="flex items-center justify-between text-xs text-gray-400">
                    <span>Source: {citation.doc_id}</span>
                    <span>Relevance: {(citation.relevance_score * 100).toFixed(1)}%</span>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}
      </motion.div>
    );
  };

  // Get content based on panel type
  const renderContent = () => {
    switch (sidePanelContent) {
      case 'node-details':
        return renderNodeDetails();
      case 'search-results':
        return renderSearchResults();
      case 'qa-results':
        return renderQAResults();
      default:
        return (
          <div className="text-center text-gray-400 py-8">
            <p>No content to display</p>
          </div>
        );
    }
  };

  // Get panel title based on content type
  const getPanelTitle = () => {
    switch (sidePanelContent) {
      case 'node-details':
        return selectedNode ? selectedNode.name : 'Node Details';
      case 'search-results':
        return 'Search Results';
      case 'qa-results':
        return 'Question & Answer';
      default:
        return 'Details';
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.aside
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ type: 'spring', damping: 25, stiffness: 200 }}
          className="absolute right-0 top-0 bottom-0 w-96 bg-gray-800 border-l border-gray-700 shadow-xl z-10"
        >
          <div className="h-full flex flex-col">
            {/* Panel header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-700 bg-gray-850">
              <h2 className="text-lg font-semibold text-white truncate pr-2">
                {getPanelTitle()}
              </h2>
              <button
                onClick={onClose}
                className="p-1 hover:bg-gray-700 rounded transition-colors flex-shrink-0"
                aria-label="Close panel"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            {/* Panel content */}
            <div className="flex-1 overflow-y-auto">
              <div className="p-4">
                <AnimatePresence mode="wait">
                  {renderContent()}
                </AnimatePresence>
              </div>
            </div>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
};

// Helper function to get type-specific colors
const getTypeColor = (type: string): string => {
  const colors: Record<string, string> = {
    'Concept': 'bg-blue-600 text-blue-100',
    'Library': 'bg-emerald-600 text-emerald-100',
    'Person': 'bg-amber-600 text-amber-100',
    'Organization': 'bg-violet-600 text-violet-100',
    'Paper': 'bg-red-600 text-red-100',
    'System': 'bg-cyan-600 text-cyan-100',
    'Metric': 'bg-lime-600 text-lime-100',
  };
  return colors[type] || 'bg-gray-600 text-gray-100';
};

export default SidePanel;