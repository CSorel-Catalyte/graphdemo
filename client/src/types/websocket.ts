/**
 * WebSocket message types for real-time communication.
 * These correspond to the backend WebSocket models.
 */

import { Entity, Relationship } from './core';

export interface UpsertNodesMessage {
  type: "upsert_nodes";
  nodes: Entity[];
}

export interface UpsertEdgesMessage {
  type: "upsert_edges";
  edges: Relationship[];
}

export interface StatusMessage {
  type: "status";
  stage: string;
  count: number;
  total?: number;
  message?: string;
}

export interface ErrorMessage {
  type: "error";
  error: string;
  message: string;
}

export interface ConnectionMessage {
  type: "connection";
  status: string;
  client_id: string;
}

export type WSMessage = 
  | UpsertNodesMessage
  | UpsertEdgesMessage
  | StatusMessage
  | ErrorMessage
  | ConnectionMessage;

export interface WSMessageWrapper {
  message: WSMessage;
  timestamp: string;
  client_id?: string;
}

// WebSocket connection states
export enum ConnectionState {
  CONNECTING = "connecting",
  CONNECTED = "connected",
  DISCONNECTED = "disconnected",
  RECONNECTING = "reconnecting",
  ERROR = "error"
}

// WebSocket hook interface
export interface UseWebSocketReturn {
  connectionState: ConnectionState;
  lastMessage: WSMessage | null;
  sendMessage: (message: any) => void;
  connect: () => void;
  disconnect: () => void;
}