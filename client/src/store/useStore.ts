/**
 * Zustand store for global application state management.
 * Implements the AppStore interface defined in types/ui.ts
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { Entity, Relationship } from '../types/core';
import { SearchResult, Citation } from '../types/api';
import { AppStore, UINode, UIEdge } from '../types/ui';

// Helper function to convert Entity to UINode
const entityToUINode = (entity: Entity): UINode => ({
  id: entity.id,
  name: entity.name,
  type: entity.type,
  salience: entity.salience,
  summary: entity.summary,
  aliases: entity.aliases,
  evidence_count: entity.source_spans.length,
  size: 8 + 12 * entity.salience, // Size based on salience
  color: getNodeColor(entity.type),
  selected: false,
  highlighted: false,
});

// Helper function to convert Relationship to UIEdge
const relationshipToUIEdge = (relationship: Relationship): UIEdge => {
  // Handle both aliased (from/to) and original (from_entity/to_entity) field names
  const fromId = relationship.from || (relationship as any).from_entity;
  const toId = relationship.to || (relationship as any).to_entity;
  
  return {
    id: `${fromId}-${toId}-${relationship.predicate}`,
    source: fromId,
    target: toId,
    predicate: relationship.predicate,
    confidence: relationship.confidence,
    evidence_count: relationship.evidence.length,
    evidence: relationship.evidence,
    width: 0.5 + 2.5 * relationship.confidence, // Width based on confidence
    color: getEdgeColor(relationship.confidence),
    opacity: 0.6 + 0.4 * relationship.confidence,
    selected: false,
  };
};

// Helper function to get node color based on type
const getNodeColor = (type: string): string => {
  const colors: Record<string, string> = {
    'Concept': '#3b82f6',      // blue
    'Library': '#10b981',      // emerald
    'Person': '#f59e0b',       // amber
    'Organization': '#8b5cf6', // violet
    'Paper': '#ef4444',        // red
    'System': '#06b6d4',       // cyan
    'Metric': '#84cc16',       // lime
  };
  return colors[type] || '#6b7280'; // gray fallback
};

// Helper function to get edge color based on confidence
const getEdgeColor = (confidence: number): string => {
  if (confidence >= 0.8) return '#10b981'; // high confidence - green
  if (confidence >= 0.6) return '#f59e0b'; // medium confidence - amber
  return '#6b7280'; // low confidence - gray
};

export const useStore = create<AppStore>()(
  devtools(
    (set, get) => ({
      // Initial state
      nodes: new Map(),
      edges: new Map(),
      selectedNode: null,
      highlightedNodes: new Set(),
      highlightedEdges: new Set(),
      searchQuery: '',
      searchResults: [],
      isSearching: false,
      currentQuestion: '',
      currentAnswer: '',
      currentCitations: [],
      isAnswering: false,
      isProcessing: false,
      processingStage: '',
      processingProgress: 0,
      isConnected: false,
      connectionError: null,
      isOfflineMode: false,
      offlineData: null,
      sidePanelOpen: false,
      sidePanelContent: null,
      cameraPosition: { x: 0, y: 0, z: 400 },
      cameraTarget: { x: 0, y: 0, z: 0 },

      // Graph actions
      upsertNodes: (entities: Entity[]) => {
        console.log('Store: upsertNodes called with', entities.length, 'entities');
        const { nodes } = get();
        const newNodes = new Map(nodes);
        
        entities.forEach(entity => {
          console.log('Processing entity:', entity);
          const uiNode = entityToUINode(entity);
          // Preserve existing position and selection state if node exists
          const existingNode = newNodes.get(entity.id);
          if (existingNode) {
            uiNode.x = existingNode.x;
            uiNode.y = existingNode.y;
            uiNode.z = existingNode.z;
            uiNode.vx = existingNode.vx;
            uiNode.vy = existingNode.vy;
            uiNode.vz = existingNode.vz;
            uiNode.selected = existingNode.selected;
            uiNode.highlighted = existingNode.highlighted;
          }
          newNodes.set(entity.id, uiNode);
        });
        
        set({ nodes: newNodes });
        
        // Clean up any orphaned edges after node updates
        get().cleanupOrphanedEdges();
      },

      upsertEdges: (relationships: Relationship[]) => {
        console.log('Store: upsertEdges called with', relationships.length, 'relationships');
        const { edges, nodes } = get();
        const newEdges = new Map(edges);
        
        relationships.forEach(relationship => {
          console.log('Processing relationship:', relationship);
          const uiEdge = relationshipToUIEdge(relationship);
          console.log('Created UIEdge:', uiEdge);
          
          // Only add edge if both source and target nodes exist
          const sourceExists = nodes.has(uiEdge.source);
          const targetExists = nodes.has(uiEdge.target);
          
          if (!sourceExists) {
            console.warn(`Edge source node not found: ${uiEdge.source}`);
            return;
          }
          
          if (!targetExists) {
            console.warn(`Edge target node not found: ${uiEdge.target}`);
            return;
          }
          
          // Preserve existing selection state if edge exists
          const existingEdge = newEdges.get(uiEdge.id);
          if (existingEdge) {
            uiEdge.selected = existingEdge.selected;
          }
          newEdges.set(uiEdge.id, uiEdge);
        });
        
        set({ edges: newEdges });
      },

      clearGraph: () => {
        set({
          nodes: new Map(),
          edges: new Map(),
          selectedNode: null,
          highlightedNodes: new Set(),
          highlightedEdges: new Set(),
        });
      },

      cleanupOrphanedEdges: () => {
        const { nodes, edges } = get();
        const newEdges = new Map();
        
        edges.forEach((edge, edgeId) => {
          const sourceExists = nodes.has(edge.source);
          const targetExists = nodes.has(edge.target);
          
          if (sourceExists && targetExists) {
            newEdges.set(edgeId, edge);
          } else {
            console.warn(`Removing orphaned edge: ${edgeId} (source: ${sourceExists}, target: ${targetExists})`);
          }
        });
        
        if (newEdges.size !== edges.size) {
          console.log(`Cleaned up ${edges.size - newEdges.size} orphaned edges`);
          set({ edges: newEdges });
        }
      },

      // Selection actions
      selectNode: (nodeId: string | null) => {
        const { nodes } = get();
        const newNodes = new Map(nodes);
        
        // Clear previous selection
        newNodes.forEach(node => {
          node.selected = false;
        });
        
        // Set new selection
        if (nodeId && newNodes.has(nodeId)) {
          const node = newNodes.get(nodeId)!;
          node.selected = true;
          newNodes.set(nodeId, node);
        }
        
        set({ 
          nodes: newNodes, 
          selectedNode: nodeId,
          sidePanelOpen: nodeId !== null,
          sidePanelContent: nodeId ? 'node-details' : null,
        });
      },

      highlightNodes: (nodeIds: string[]) => {
        const { nodes } = get();
        const newNodes = new Map(nodes);
        const highlightedNodes = new Set(nodeIds);
        
        newNodes.forEach((node, id) => {
          node.highlighted = highlightedNodes.has(id);
          newNodes.set(id, node);
        });
        
        set({ nodes: newNodes, highlightedNodes });
      },

      highlightEdges: (edgeIds: string[]) => {
        const { edges } = get();
        const newEdges = new Map(edges);
        const highlightedEdges = new Set(edgeIds);
        
        newEdges.forEach((edge, id) => {
          edge.selected = highlightedEdges.has(id);
          newEdges.set(id, edge);
        });
        
        set({ edges: newEdges, highlightedEdges });
      },

      clearHighlights: () => {
        const { nodes, edges } = get();
        const newNodes = new Map(nodes);
        const newEdges = new Map(edges);
        
        newNodes.forEach((node, id) => {
          node.highlighted = false;
          newNodes.set(id, node);
        });
        
        newEdges.forEach((edge, id) => {
          edge.selected = false;
          newEdges.set(id, edge);
        });
        
        set({
          nodes: newNodes,
          edges: newEdges,
          highlightedNodes: new Set(),
          highlightedEdges: new Set(),
        });
      },

      // Search actions
      setSearchQuery: (query: string) => set({ searchQuery: query }),
      
      setSearchResults: (results: SearchResult[]) => set({ 
        searchResults: results,
        sidePanelOpen: results.length > 0,
        sidePanelContent: results.length > 0 ? 'search-results' : null,
      }),
      
      setSearching: (isSearching: boolean) => set({ isSearching }),

      // Q&A actions
      setCurrentQuestion: (question: string) => set({ currentQuestion: question }),
      
      setCurrentAnswer: (answer: string, citations: Citation[]) => set({ 
        currentAnswer: answer,
        currentCitations: citations,
        sidePanelOpen: true,
        sidePanelContent: 'qa-results',
      }),
      
      setAnswering: (isAnswering: boolean) => set({ isAnswering }),

      // Processing actions
      setProcessing: (isProcessing: boolean, stage?: string, progress?: number) => set({
        isProcessing,
        processingStage: stage || '',
        processingProgress: progress || 0,
      }),

      // Connection actions
      setConnected: (isConnected: boolean, error?: string | null) => set({
        isConnected,
        connectionError: error || null,
      }),

      // Offline mode actions
      setOfflineMode: (isOffline: boolean, data?: { nodes: Entity[]; edges: Relationship[]; metadata?: any } | null) => {
        set({
          isOfflineMode: isOffline,
          offlineData: data || null,
          isConnected: !isOffline, // If offline, we're not connected
        });
        
        // If entering offline mode with data, load it into the graph
        if (isOffline && data) {
          get().upsertNodes(data.nodes);
          get().upsertEdges(data.edges);
        }
      },

      importGraphData: (data: { nodes: Entity[]; edges: Relationship[]; metadata?: any }) => {
        // Clear existing graph
        get().clearGraph();
        
        // Load new data
        get().upsertNodes(data.nodes);
        get().upsertEdges(data.edges);
        
        // Store as offline data
        set({
          offlineData: data,
          isOfflineMode: true,
          isConnected: false,
        });
      },

      // UI actions
      setSidePanelOpen: (open: boolean, content?: AppStore['sidePanelContent']) => set({
        sidePanelOpen: open,
        sidePanelContent: open ? (content || get().sidePanelContent) : null,
      }),

      setCameraPosition: (position: { x: number; y: number; z: number }) => set({
        cameraPosition: position,
      }),

      setCameraTarget: (target: { x: number; y: number; z: number }) => set({
        cameraTarget: target,
      }),
    }),
    {
      name: 'ai-knowledge-mapper-store',
    }
  )
);

// Selector hooks for common state access patterns
export const useGraphData = () => {
  const nodes = useStore(state => Array.from(state.nodes.values()));
  const edges = useStore(state => Array.from(state.edges.values()));
  return { nodes, links: edges };
};

export const useSelectedNode = () => {
  const selectedNodeId = useStore(state => state.selectedNode);
  const nodes = useStore(state => state.nodes);
  return selectedNodeId ? nodes.get(selectedNodeId) || null : null;
};

export const useConnectionStatus = () => useStore(state => ({
  isConnected: state.isConnected,
  connectionError: state.connectionError,
}));

export const useProcessingStatus = () => useStore(state => ({
  isProcessing: state.isProcessing,
  processingStage: state.processingStage,
  processingProgress: state.processingProgress,
}));