/**
 * Utility functions for converting between backend and frontend types.
 */

import { Entity, Relationship } from './core';
import { UINode, UIEdge, GraphConfig } from './ui';

// Default graph configuration
export const DEFAULT_GRAPH_CONFIG: GraphConfig = {
  nodeSize: {
    min: 8,
    max: 20,
    salienceMultiplier: 12
  },
  edgeWidth: {
    min: 0.5,
    max: 3,
    confidenceMultiplier: 2.5
  },
  colors: {
    nodes: {
      Concept: '#3B82F6',      // Blue
      Library: '#10B981',      // Green
      Person: '#F59E0B',       // Amber
      Organization: '#8B5CF6', // Purple
      Paper: '#EF4444',        // Red
      System: '#06B6D4',       // Cyan
      Metric: '#84CC16'        // Lime
    },
    edges: {
      default: '#6B7280',      // Gray
      selected: '#F59E0B',     // Amber
      highlighted: '#EF4444'   // Red
    }
  },
  physics: {
    forceStrength: -300,
    linkDistance: 100,
    chargeStrength: -100,
    centerStrength: 0.1
  },
  animation: {
    duration: 1000,
    easing: 'cubic-bezier(0.4, 0, 0.2, 1)'
  }
};

/**
 * Convert backend Entity to frontend UINode
 */
export function entityToUINode(entity: Entity, config: GraphConfig = DEFAULT_GRAPH_CONFIG): UINode {
  const size = config.nodeSize.min + (entity.salience * config.nodeSize.salienceMultiplier);
  const color = config.colors.nodes[entity.type] || config.colors.nodes.Concept;
  
  return {
    id: entity.id,
    name: entity.name,
    type: entity.type,
    salience: entity.salience,
    summary: entity.summary,
    aliases: entity.aliases,
    evidence_count: entity.source_spans.length,
    size,
    color,
    selected: false,
    highlighted: false
  };
}

/**
 * Convert backend Relationship to frontend UIEdge
 */
export function relationshipToUIEdge(relationship: Relationship, config: GraphConfig = DEFAULT_GRAPH_CONFIG): UIEdge {
  const width = config.edgeWidth.min + (relationship.confidence * config.edgeWidth.confidenceMultiplier);
  const opacity = 0.3 + (relationship.confidence * 0.7); // 0.3 to 1.0 based on confidence
  
  return {
    id: `${relationship.from}-${relationship.to}-${relationship.predicate}`,
    source: relationship.from,
    target: relationship.to,
    predicate: relationship.predicate,
    confidence: relationship.confidence,
    evidence_count: relationship.evidence.length,
    width,
    color: config.colors.edges.default,
    opacity,
    selected: false
  };
}

/**
 * Convert arrays of entities and relationships to graph data
 */
export function toGraphData(
  entities: Entity[], 
  relationships: Relationship[], 
  config: GraphConfig = DEFAULT_GRAPH_CONFIG
) {
  const nodes = entities.map(entity => entityToUINode(entity, config));
  const links = relationships.map(rel => relationshipToUIEdge(rel, config));
  
  return { nodes, links };
}

/**
 * Calculate node size based on salience
 */
export function calculateNodeSize(salience: number, config: GraphConfig = DEFAULT_GRAPH_CONFIG): number {
  return config.nodeSize.min + (salience * config.nodeSize.salienceMultiplier);
}

/**
 * Calculate edge width based on confidence
 */
export function calculateEdgeWidth(confidence: number, config: GraphConfig = DEFAULT_GRAPH_CONFIG): number {
  return config.edgeWidth.min + (confidence * config.edgeWidth.confidenceMultiplier);
}

/**
 * Get color for entity type
 */
export function getEntityColor(entityType: string, config: GraphConfig = DEFAULT_GRAPH_CONFIG): string {
  return config.colors.nodes[entityType] || config.colors.nodes.Concept;
}

/**
 * Format timestamp for display
 */
export function formatTimestamp(timestamp: string): string {
  return new Date(timestamp).toLocaleString();
}

/**
 * Truncate text to specified length
 */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
}

/**
 * Generate a unique ID for UI elements
 */
export function generateUIId(prefix: string = 'ui'): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Debounce function for search inputs
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

/**
 * Check if a point is within a bounding box
 */
export function isPointInBounds(
  point: { x: number; y: number },
  bounds: { x: number; y: number; width: number; height: number }
): boolean {
  return (
    point.x >= bounds.x &&
    point.x <= bounds.x + bounds.width &&
    point.y >= bounds.y &&
    point.y <= bounds.y + bounds.height
  );
}

/**
 * Calculate distance between two 3D points
 */
export function distance3D(
  p1: { x: number; y: number; z: number },
  p2: { x: number; y: number; z: number }
): number {
  const dx = p2.x - p1.x;
  const dy = p2.y - p1.y;
  const dz = p2.z - p1.z;
  return Math.sqrt(dx * dx + dy * dy + dz * dz);
}