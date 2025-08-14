/**
 * Utility functions for testing WebSocket integration.
 * These can be used to verify real-time data synchronization.
 */

import { Entity, Relationship, EntityType, RelationType } from '../types/core';
import { WSMessage } from '../types/websocket';

// Mock data generators for testing
export const createMockEntity = (id: string, name: string, type: EntityType = EntityType.CONCEPT): Entity => ({
  id,
  name,
  type,
  aliases: [name],
  embedding: new Array(3072).fill(0).map(() => Math.random()),
  salience: Math.random(),
  source_spans: [{
    doc_id: 'test-doc',
    start: 0,
    end: name.length,
  }],
  summary: `Test entity: ${name}`,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
});

export const createMockRelationship = (
  from: string, 
  to: string, 
  predicate: RelationType = RelationType.RELATES_TO
): Relationship => ({
  from,
  to,
  predicate,
  confidence: Math.random(),
  evidence: [{
    doc_id: 'test-doc',
    quote: `Test evidence for ${predicate} relationship`,
    offset: 0,
  }],
  directional: true,
  created_at: new Date().toISOString(),
});

// Mock WebSocket messages for testing
export const createMockMessages = (): WSMessage[] => [
  {
    type: 'upsert_nodes',
    nodes: [
      createMockEntity('node1', 'Test Node 1', EntityType.CONCEPT),
      createMockEntity('node2', 'Test Node 2', EntityType.LIBRARY),
    ],
  },
  {
    type: 'upsert_edges',
    edges: [
      createMockRelationship('node1', 'node2', RelationType.USES),
    ],
  },
  {
    type: 'status',
    stage: 'Processing text chunks',
    count: 5,
    total: 10,
    message: 'Extracting entities and relationships',
  },
  {
    type: 'status',
    stage: 'Processing complete',
    count: 10,
    total: 10,
    message: 'All chunks processed successfully',
  },
];

// Test WebSocket connection functionality
export const testWebSocketConnection = (sendMessage: (message: any) => void) => {
  console.log('Testing WebSocket connection...');
  
  // Send a test ping message
  sendMessage({
    type: 'ping',
    timestamp: new Date().toISOString(),
  });
  
  console.log('Test ping message sent');
};

// Simulate processing workflow
export const simulateProcessingWorkflow = (sendMessage: (message: any) => void) => {
  console.log('Simulating processing workflow...');
  
  const messages = createMockMessages();
  
  messages.forEach((message, index) => {
    setTimeout(() => {
      console.log(`Sending mock message ${index + 1}:`, message.type);
      sendMessage(message);
    }, index * 1000); // Send messages with 1 second intervals
  });
};

// Validate store state after WebSocket updates
export const validateStoreState = (nodes: Map<string, any>, edges: Map<string, any>) => {
  console.log('Validating store state...');
  console.log(`Nodes in store: ${nodes.size}`);
  console.log(`Edges in store: ${edges.size}`);
  
  // Log node details
  nodes.forEach((node, id) => {
    console.log(`Node ${id}:`, {
      name: node.name,
      type: node.type,
      salience: node.salience,
      size: node.size,
    });
  });
  
  // Log edge details
  edges.forEach((edge, id) => {
    console.log(`Edge ${id}:`, {
      source: edge.source,
      target: edge.target,
      predicate: edge.predicate,
      confidence: edge.confidence,
      width: edge.width,
    });
  });
  
  return {
    nodeCount: nodes.size,
    edgeCount: edges.size,
    isValid: nodes.size > 0 || edges.size > 0,
  };
};