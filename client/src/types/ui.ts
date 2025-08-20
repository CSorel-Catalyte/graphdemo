/**
 * UI-specific types for the AI Knowledge Mapper frontend.
 * These define the interfaces for graph visualization and state management.
 */

import { Entity, Relationship, Evidence } from './core';
import { SearchResult, Citation } from './api';

// Graph visualization types
export interface UINode {
  id: string;
  name: string;
  type: string;
  salience: number;
  summary: string;
  aliases: string[];
  evidence_count: number;
  x?: number;
  y?: number;
  z?: number;
  vx?: number;
  vy?: number;
  vz?: number;
  fx?: number;
  fy?: number;
  fz?: number;
  color?: string;
  size?: number;
  selected?: boolean;
  highlighted?: boolean;
}

export interface UIEdge {
  id: string;
  source: string;
  target: string;
  predicate: string;
  confidence: number;
  evidence_count: number;
  evidence?: Evidence[];
  width?: number;
  color?: string;
  opacity?: number;
  selected?: boolean;
}

// Graph data structure
export interface GraphData {
  nodes: UINode[];
  links: UIEdge[];
}

// State management interfaces
export interface AppState {
  // Graph data
  nodes: Map<string, UINode>;
  edges: Map<string, UIEdge>;
  
  // UI state
  selectedNode: string | null;
  highlightedNodes: Set<string>;
  highlightedEdges: Set<string>;
  
  // Search state
  searchQuery: string;
  searchResults: SearchResult[];
  isSearching: boolean;
  
  // Q&A state
  currentQuestion: string;
  currentAnswer: string;
  currentCitations: Citation[];
  isAnswering: boolean;
  
  // Processing state
  isProcessing: boolean;
  processingStage: string;
  processingProgress: number;
  
  // Connection state
  isConnected: boolean;
  connectionError: string | null;
  
  // Offline mode state
  isOfflineMode: boolean;
  offlineData: { nodes: Entity[]; edges: Relationship[]; metadata?: any } | null;
  
  // Side panel state
  sidePanelOpen: boolean;
  sidePanelContent: 'node-details' | 'search-results' | 'qa-results' | null;
  
  // Graph view state
  cameraPosition: { x: number; y: number; z: number };
  cameraTarget: { x: number; y: number; z: number };
}

// Action types for state management
export interface AppActions {
  // Graph actions
  upsertNodes: (nodes: Entity[]) => void;
  upsertEdges: (edges: Relationship[]) => void;
  clearGraph: () => void;
  cleanupOrphanedEdges: () => void;
  
  // Selection actions
  selectNode: (nodeId: string | null) => void;
  highlightNodes: (nodeIds: string[]) => void;
  highlightEdges: (edgeIds: string[]) => void;
  clearHighlights: () => void;
  
  // Search actions
  setSearchQuery: (query: string) => void;
  setSearchResults: (results: SearchResult[]) => void;
  setSearching: (isSearching: boolean) => void;
  
  // Q&A actions
  setCurrentQuestion: (question: string) => void;
  setCurrentAnswer: (answer: string, citations: Citation[]) => void;
  setAnswering: (isAnswering: boolean) => void;
  
  // Processing actions
  setProcessing: (isProcessing: boolean, stage?: string, progress?: number) => void;
  
  // Connection actions
  setConnected: (isConnected: boolean, error?: string | null) => void;
  
  // Offline mode actions
  setOfflineMode: (isOffline: boolean, data?: { nodes: Entity[]; edges: Relationship[]; metadata?: any } | null) => void;
  importGraphData: (data: { nodes: Entity[]; edges: Relationship[]; metadata?: any }) => void;
  
  // UI actions
  setSidePanelOpen: (open: boolean, content?: AppState['sidePanelContent']) => void;
  setCameraPosition: (position: { x: number; y: number; z: number }) => void;
  setCameraTarget: (target: { x: number; y: number; z: number }) => void;
}

// Combined store interface
export interface AppStore extends AppState, AppActions {}

// Component prop interfaces
export interface Graph3DProps {
  graphData: GraphData;
  onNodeClick: (node: UINode) => void;
  onNodeHover: (node: UINode | null) => void;
  selectedNodeId: string | null;
  highlightedNodeIds: Set<string>;
  highlightedEdgeIds: Set<string>;
  width?: number;
  height?: number;
}

export interface SidePanelProps {
  isOpen: boolean;
  onClose: () => void;
  content: AppState['sidePanelContent'];
  selectedNode: UINode | null;
  searchResults: SearchResult[];
  qaResults: {
    question: string;
    answer: string;
    citations: Citation[];
  } | null;
}

export interface SearchBoxProps {
  query: string;
  onQueryChange: (query: string) => void;
  onSearch: (query: string) => void;
  isSearching: boolean;
  placeholder?: string;
}

export interface QuestionBoxProps {
  question: string;
  onQuestionChange: (question: string) => void;
  onAsk: (question: string) => void;
  isAnswering: boolean;
  placeholder?: string;
}

export interface StatusBarProps {
  isConnected: boolean;
  isProcessing: boolean;
  processingStage: string;
  processingProgress: number;
  nodeCount: number;
  edgeCount: number;
}

// Graph layout and physics configuration
export interface GraphConfig {
  nodeSize: {
    min: number;
    max: number;
    salienceMultiplier: number;
  };
  edgeWidth: {
    min: number;
    max: number;
    confidenceMultiplier: number;
  };
  colors: {
    nodes: Record<string, string>;
    edges: {
      default: string;
      selected: string;
      highlighted: string;
    };
  };
  physics: {
    forceStrength: number;
    linkDistance: number;
    chargeStrength: number;
    centerStrength: number;
  };
  animation: {
    duration: number;
    easing: string;
  };
}

// Utility types
export type NodeId = string;
export type EdgeId = string;
export type Position3D = { x: number; y: number; z: number };
export type Color = string;
export type Size = number;