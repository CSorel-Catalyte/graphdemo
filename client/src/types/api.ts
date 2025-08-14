/**
 * API request and response types for the AI Knowledge Mapper frontend.
 * These correspond to the backend API models.
 */

import { Entity, Relationship } from './core';

// Request types
export interface IngestRequest {
  doc_id: string;
  text: string;
}

export interface SearchRequest {
  q: string;
  k?: number;
}

export interface NeighborsRequest {
  node_id: string;
  hops?: number;
  limit?: number;
}

export interface QuestionRequest {
  q: string;
}

// Response types
export interface IngestResponse {
  success: boolean;
  doc_id: string;
  chunks_processed: number;
  entities_extracted: number;
  relationships_extracted: number;
  processing_time: number;
  message?: string;
}

export interface SearchResult {
  entity: Entity;
  score: number;
}

export interface SearchResponse {
  results: SearchResult[];
  query: string;
  total_results: number;
  processing_time: number;
}

export interface NeighborsResponse {
  center_node: Entity;
  neighbors: Entity[];
  relationships: Relationship[];
  total_neighbors: number;
  processing_time: number;
}

export interface Citation {
  node_id: string;
  quote: string;
  doc_id: string;
  relevance_score: number;
}

export interface QuestionResponse {
  answer: string;
  citations: Citation[];
  question: string;
  confidence: number;
  processing_time: number;
}

export interface GraphExportResponse {
  nodes: Entity[];
  edges: Relationship[];
  metadata: Record<string, any>;
  export_timestamp: string;
  total_nodes: number;
  total_edges: number;
}

export interface StatusResponse {
  status: string;
  details?: Record<string, any>;
}

export interface ErrorResponse {
  error: string;
  message: string;
  details?: Record<string, any>;
  timestamp: string;
}

// API Client interface
export interface ApiClient {
  ingest(request: IngestRequest): Promise<IngestResponse>;
  search(request: SearchRequest): Promise<SearchResponse>;
  getNeighbors(request: NeighborsRequest): Promise<NeighborsResponse>;
  ask(request: QuestionRequest): Promise<QuestionResponse>;
  exportGraph(): Promise<GraphExportResponse>;
  getHealth(): Promise<StatusResponse>;
}