/**
 * 3D Graph visualization component using react-force-graph-3d.
 * Implements interactive 3D graph with force simulation, node sizing based on salience,
 * and edge width based on confidence scores.
 */

import React, { useRef, useEffect, useCallback, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ForceGraph3D from 'react-force-graph-3d';
import { useGraphData, useStore } from '../store/useStore';
import { UINode, UIEdge } from '../types/ui';

const Graph3D: React.FC = () => {
  const graphRef = useRef<any>();
  const graphData = useGraphData();
  const { 
    selectNode, 
    isConnected,
    highlightNodes,
    clearHighlights,
    setCameraPosition,
    setCameraTarget
  } = useStore();

  // State for hover tooltip
  const [hoveredNode, setHoveredNode] = useState<UINode | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState<{ x: number; y: number } | null>(null);
  
  // State for camera controls
  const [isUserInteracting, setIsUserInteracting] = useState(false);

  // Memoize graph data to prevent unnecessary re-renders
  const memoizedGraphData = useMemo(() => ({
    nodes: graphData.nodes,
    links: graphData.links
  }), [graphData.nodes, graphData.links]);

  // API call to expand node neighborhood
  const expandNodeNeighborhood = useCallback(async (nodeId: string) => {
    try {
      const { getNeighbors } = await import('../utils/api');
      const data = await getNeighbors({ node_id: nodeId, hops: 1, limit: 200 });
      // The backend should broadcast the new nodes/edges via WebSocket
      // so we don't need to manually update the store here
      console.log(`Expanded neighborhood for node ${nodeId}:`, data);
    } catch (error) {
      console.error('Failed to expand node neighborhood:', error);
    }
  }, []);

  // Handle node click events with neighborhood expansion
  const handleNodeClick = useCallback(async (node: UINode, event?: MouseEvent) => {
    // Clear any existing highlights
    clearHighlights();
    
    // Select the node
    selectNode(node.id);
    
    // Expand 1-hop neighborhood as per requirement 2.4
    await expandNodeNeighborhood(node.id);
    
    // Center camera on selected node with smooth animation
    if (graphRef.current && node.x !== undefined && node.y !== undefined && node.z !== undefined) {
      const distance = 200;
      const newCameraPos = { 
        x: node.x + distance, 
        y: node.y + distance, 
        z: node.z + distance 
      };
      const newTarget = { x: node.x, y: node.y, z: node.z };
      
      graphRef.current.cameraPosition(
        newCameraPos,
        newTarget,
        1000 // Animation duration
      );
      
      // Update store with new camera position
      setCameraPosition(newCameraPos);
      setCameraTarget(newTarget);
    }
  }, [selectNode, clearHighlights, expandNodeNeighborhood, setCameraPosition, setCameraTarget]);

  // Handle node hover events with tooltip positioning
  const handleNodeHover = useCallback((node: UINode | null, prevNode?: UINode) => {
    // Update cursor
    document.body.style.cursor = node ? 'pointer' : 'default';
    
    // Update hover state
    setHoveredNode(node);
    
    if (node && graphRef.current) {
      // Get screen coordinates for tooltip positioning
      const coords = graphRef.current.graph2ScreenCoords(node.x, node.y, node.z);
      if (coords) {
        setTooltipPosition({ x: coords.x, y: coords.y });
      }
    } else {
      setTooltipPosition(null);
    }
  }, []);

  // Node rendering configuration - remove for now to use default spheres
  // const nodeThreeObject = useCallback((node: UINode) => {
  //   // This will create a sphere geometry for each node
  //   // Size is already calculated in the store based on salience
  //   return null; // Use default sphere rendering for now
  // }, []);

  // Node color configuration
  const nodeColor = useCallback((node: UINode) => {
    if (node.selected) {
      return '#ffffff'; // White for selected nodes
    }
    if (node.highlighted) {
      return '#fbbf24'; // Amber for highlighted nodes
    }
    return node.color || '#6b7280'; // Default or type-based color
  }, []);

  // Node size configuration based on salience
  const nodeVal = useCallback((node: UINode) => {
    return node.size || (8 + 12 * node.salience);
  }, []);

  // Edge color configuration with cross-document highlighting
  const linkColor = useCallback((edge: UIEdge) => {
    if (edge.selected) {
      return '#fbbf24'; // Amber for selected edges
    }
    // Highlight comparison relationships (cross-document conflicts)
    if (edge.predicate === 'compares_with') {
      return '#ef4444'; // Red for comparison/conflict relationships
    }
    return edge.color || '#6b7280'; // Default or confidence-based color
  }, []);

  // Edge width configuration based on confidence with special handling for comparisons
  const linkWidth = useCallback((edge: UIEdge) => {
    // Make comparison relationships thicker to draw attention
    if (edge.predicate === 'compares_with') {
      return 4; // Fixed thick width for comparison relationships
    }
    return edge.width || (0.5 + 2.5 * edge.confidence);
  }, []);

  // Edge opacity configuration - using a fixed value for now
  // Individual edge opacity will be handled through linkColor alpha channel
  const linkOpacity = 0.8;

  // Node label configuration
  const nodeLabel = useCallback((node: UINode) => {
    return `
      <div style="
        background: rgba(0, 0, 0, 0.8); 
        color: white; 
        padding: 8px 12px; 
        border-radius: 4px; 
        font-size: 12px;
        max-width: 200px;
        text-align: center;
      ">
        <strong>${node.name}</strong><br/>
        Type: ${node.type}<br/>
        Salience: ${(node.salience * 100).toFixed(1)}%<br/>
        Evidence: ${node.evidence_count} sources
      </div>
    `;
  }, []);

  // Graph navigation controls
  const handleResetView = useCallback(() => {
    if (graphRef.current) {
      graphRef.current.cameraPosition(
        { x: 0, y: 0, z: 400 },
        { x: 0, y: 0, z: 0 },
        1000
      );
      setCameraPosition({ x: 0, y: 0, z: 400 });
      setCameraTarget({ x: 0, y: 0, z: 0 });
    }
  }, [setCameraPosition, setCameraTarget]);

  const handleZoomIn = useCallback(() => {
    if (graphRef.current) {
      const currentPos = graphRef.current.cameraPosition();
      const distance = Math.sqrt(currentPos.x ** 2 + currentPos.y ** 2 + currentPos.z ** 2);
      const newDistance = Math.max(distance * 0.8, 50); // Minimum zoom distance
      const factor = newDistance / distance;
      
      const newPos = {
        x: currentPos.x * factor,
        y: currentPos.y * factor,
        z: currentPos.z * factor
      };
      
      graphRef.current.cameraPosition(newPos, undefined, 300);
      setCameraPosition(newPos);
    }
  }, [setCameraPosition]);

  const handleZoomOut = useCallback(() => {
    if (graphRef.current) {
      const currentPos = graphRef.current.cameraPosition();
      const distance = Math.sqrt(currentPos.x ** 2 + currentPos.y ** 2 + currentPos.z ** 2);
      const newDistance = Math.min(distance * 1.25, 2000); // Maximum zoom distance
      const factor = newDistance / distance;
      
      const newPos = {
        x: currentPos.x * factor,
        y: currentPos.y * factor,
        z: currentPos.z * factor
      };
      
      graphRef.current.cameraPosition(newPos, undefined, 300);
      setCameraPosition(newPos);
    }
  }, [setCameraPosition]);

  // Initialize graph physics and layout
  useEffect(() => {
    if (graphRef.current) {
      const graph = graphRef.current;
      
      // Configure force simulation parameters
      graph
        .d3Force('link')
        ?.distance((link: UIEdge) => {
          // Link distance based on confidence - higher confidence = shorter distance
          return 50 + (1 - link.confidence) * 100;
        });
      
      graph
        .d3Force('charge')
        ?.strength(-200); // Repulsion between nodes
      
      graph
        .d3Force('center')
        ?.strength(0.1); // Centering force
      
      // Set initial camera position if no nodes exist yet
      if (memoizedGraphData.nodes.length === 0) {
        graph.cameraPosition(
          { x: 0, y: 0, z: 400 },
          { x: 0, y: 0, z: 0 }
        );
      }
    }
  }, [memoizedGraphData.nodes.length]);

  // Handle camera position updates
  // const handleCameraPositionUpdate = useCallback((position: any, lookAt: any) => {
  //   setCameraPosition(position);
  //   setCameraTarget(lookAt);
  // }, [setCameraPosition, setCameraTarget]);

  // Show loading state when not connected or no data
  if (!isConnected && memoizedGraphData.nodes.length === 0) {
    return (
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="w-full h-full bg-gray-900 flex items-center justify-center"
      >
        <motion.div 
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          className="text-center"
        >
          <motion.div 
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            className="rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent mx-auto mb-4"
          />
          <motion.p 
            initial={{ y: 10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="text-gray-400"
          >
            Connecting to knowledge graph...
          </motion.p>
        </motion.div>
      </motion.div>
    );
  }

  // Show empty state when connected but no data
  if (memoizedGraphData.nodes.length === 0) {
    return (
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="w-full h-full bg-gray-900 flex items-center justify-center"
      >
        <motion.div 
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          className="text-center"
        >
          <motion.div 
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.3, type: "spring", stiffness: 200 }}
            className="mb-4"
          >
            <svg 
              className="w-16 h-16 mx-auto text-gray-600" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={1} 
                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" 
              />
            </svg>
          </motion.div>
          <motion.h3 
            initial={{ y: 10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="text-lg font-medium text-gray-300 mb-2"
          >
            No Knowledge Graph Data
          </motion.h3>
          <motion.p 
            initial={{ y: 10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="text-gray-500"
          >
            Ingest some text to start building your knowledge graph
          </motion.p>
        </motion.div>
      </motion.div>
    );
  }

  return (
    <div className="w-full h-full bg-gray-900 relative">
      <ForceGraph3D
        ref={graphRef}
        graphData={memoizedGraphData}
        width={window.innerWidth}
        height={window.innerHeight}
        backgroundColor="rgba(17, 24, 39, 1)" // gray-900
        
        // Node configuration
        nodeVal={nodeVal}
        nodeColor={nodeColor}
        nodeLabel={nodeLabel}
        onNodeClick={handleNodeClick}
        onNodeHover={handleNodeHover}
        
        // Edge configuration
        linkColor={linkColor}
        linkWidth={linkWidth}
        linkOpacity={linkOpacity}
        linkDirectionalArrowLength={3}
        linkDirectionalArrowRelPos={1}
        linkCurvature={0.1}
        
        // Physics configuration
        numDimensions={3}
        cooldownTicks={100}
        cooldownTime={15000}
        
        // Camera configuration
        showNavInfo={false}
        controlType="orbit"
        
        // Performance optimizations
        enableNodeDrag={true}
        enableNavigationControls={true}
        enablePointerInteraction={true}
      />
      
      {/* Hover Tooltip - Requirement 2.3 */}
      <AnimatePresence>
        {hoveredNode && tooltipPosition && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.8, y: 10 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className="absolute pointer-events-none z-50 bg-gray-800/95 backdrop-blur-sm text-white px-3 py-2 rounded-lg shadow-xl border border-gray-600/50 max-w-xs"
            style={{
              left: tooltipPosition.x + 10,
              top: tooltipPosition.y - 10,
              transform: 'translate(0, -100%)'
            }}
          >
            <div className="font-semibold text-sm mb-1">{hoveredNode.name}</div>
            <div className="text-xs text-gray-300 mb-1">
              Type: {hoveredNode.type} | Salience: {(hoveredNode.salience * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-gray-400">
              {hoveredNode.summary || 'No summary available'}
            </div>
            {hoveredNode.evidence_count > 0 && (
              <div className="text-xs text-blue-300 mt-1">
                {hoveredNode.evidence_count} evidence source{hoveredNode.evidence_count !== 1 ? 's' : ''}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* Graph Navigation Controls */}
      <motion.div 
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.5 }}
        className="absolute top-4 right-4 flex flex-col gap-2"
      >
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={handleZoomIn}
          className="bg-gray-800/90 backdrop-blur-sm hover:bg-gray-700/90 text-white p-2 rounded-lg shadow-lg transition-all duration-200 border border-gray-600/50"
          title="Zoom In"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
        </motion.button>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={handleZoomOut}
          className="bg-gray-800/90 backdrop-blur-sm hover:bg-gray-700/90 text-white p-2 rounded-lg shadow-lg transition-all duration-200 border border-gray-600/50"
          title="Zoom Out"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 12H6" />
          </svg>
        </motion.button>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={handleResetView}
          className="bg-gray-800/90 backdrop-blur-sm hover:bg-gray-700/90 text-white p-2 rounded-lg shadow-lg transition-all duration-200 border border-gray-600/50"
          title="Reset View"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </motion.button>
      </motion.div>
      
      {/* Graph statistics overlay */}
      <motion.div 
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.3 }}
        className="absolute top-4 left-4 bg-black/60 backdrop-blur-sm text-white px-3 py-2 rounded-lg text-sm border border-gray-600/50"
      >
        <motion.div
          key={memoizedGraphData.nodes.length}
          initial={{ scale: 1.1 }}
          animate={{ scale: 1 }}
          transition={{ duration: 0.2 }}
        >
          Nodes: {memoizedGraphData.nodes.length}
        </motion.div>
        <motion.div
          key={memoizedGraphData.links.length}
          initial={{ scale: 1.1 }}
          animate={{ scale: 1 }}
          transition={{ duration: 0.2 }}
        >
          Edges: {memoizedGraphData.links.length}
        </motion.div>
        <div className={`flex items-center gap-2 ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
          <motion.div 
            animate={{ scale: isConnected ? [1, 1.2, 1] : 1 }}
            transition={{ duration: 2, repeat: isConnected ? Infinity : 0 }}
            className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}
          />
          {isConnected ? 'Connected' : 'Disconnected'}
        </div>
      </motion.div>
    </div>
  );
};

export default Graph3D;