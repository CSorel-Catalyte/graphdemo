/**
 * Core data types for the AI Knowledge Mapper frontend.
 * These correspond to the backend Pydantic models.
 */

export enum EntityType {
  CONCEPT = "Concept",
  LIBRARY = "Library", 
  PERSON = "Person",
  ORGANIZATION = "Organization",
  PAPER = "Paper",
  SYSTEM = "System",
  METRIC = "Metric"
}

export enum RelationType {
  USES = "uses",
  IMPLEMENTS = "implements",
  EXTENDS = "extends",
  CONTAINS = "contains",
  RELATES_TO = "relates_to",
  AUTHORED_BY = "authored_by",
  PUBLISHED_BY = "published_by",
  COMPARES_WITH = "compares_with",
  DEPENDS_ON = "depends_on",
  INFLUENCES = "influences"
}

export interface SourceSpan {
  doc_id: string;
  start: number;
  end: number;
}

export interface Evidence {
  doc_id: string;
  quote: string;
  offset: number;
}

export interface Entity {
  id: string;
  name: string;
  type: EntityType;
  aliases: string[];
  embedding: number[];
  salience: number;
  source_spans: SourceSpan[];
  summary: string;
  created_at: string;
  updated_at: string;
}

export interface Relationship {
  from: string;
  to: string;
  predicate: RelationType;
  confidence: number;
  evidence: Evidence[];
  directional: boolean;
  created_at: string;
}

export interface IEResult {
  entities: Entity[];
  relationships: Relationship[];
  chunk_id: string;
  doc_id: string;
  processing_time: number;
}