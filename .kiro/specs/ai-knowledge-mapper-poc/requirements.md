# Requirements Document

## Introduction

This POC/demo application will demonstrate an interactive AI-powered knowledge graph system that converts arbitrary text into structured knowledge representations. The system will extract entities and relationships from text using LLMs, canonicalize them through vector similarity, store them in graph and vector databases, and provide an interactive 3D visualization with question-answering capabilities. The focus is on demonstrating core functionality within a 15-minute demo timeframe, running in a Docker container on WSL.

## Requirements

### Requirement 1

**User Story:** As a demo presenter, I want to paste text and see it automatically converted into an interactive knowledge graph, so that I can demonstrate real-time knowledge extraction capabilities.

#### Acceptance Criteria

1. WHEN a user submits text via the `/ingest` API THEN the system SHALL chunk the text into segments of ≤1800 tokens while preserving paragraph boundaries
2. WHEN text chunks are processed THEN the system SHALL extract entities and relationships using LLM with strict JSON output format
3. WHEN entities are extracted THEN the system SHALL canonicalize them using vector similarity (cosine ≥ 0.86) or alias matching
4. WHEN new nodes and edges are created THEN the system SHALL broadcast updates via WebSocket to connected clients
5. WHEN the extraction process completes THEN the system SHALL return a success status with chunk count

### Requirement 2

**User Story:** As a demo viewer, I want to see an interactive 3D knowledge graph that updates in real-time, so that I can visualize how knowledge is being extracted and connected.

#### Acceptance Criteria

1. WHEN nodes are added to the graph THEN the system SHALL render them with size proportional to salience score (8 + 12*salience)
2. WHEN edges are added THEN the system SHALL render them with width proportional to confidence (0.5px to 3px range)
3. WHEN a user hovers over a node THEN the system SHALL display a tooltip with name, type, and top evidence quote
4. WHEN a user clicks on a node THEN the system SHALL select it and load its 1-hop neighborhood
5. WHEN WebSocket messages are received THEN the system SHALL update the graph visualization in real-time

### Requirement 3

**User Story:** As a demo presenter, I want to click on nodes to see detailed information with evidence quotes, so that I can show the system's transparency and grounding in source text.

#### Acceptance Criteria

1. WHEN a node is selected THEN the system SHALL display a side panel with node details
2. WHEN node details are shown THEN the system SHALL include name, type, 30-word summary, and evidence quotes
3. WHEN evidence quotes are displayed THEN each quote SHALL be ≤200 characters with source document reference
4. WHEN a user clicks "Expand 1-hop" THEN the system SHALL fetch and display neighboring nodes via `/neighbors` API
5. WHEN neighboring nodes are loaded THEN the system SHALL update the graph to include the expanded neighborhood

### Requirement 4

**User Story:** As a demo viewer, I want to search for specific entities in the knowledge graph, so that I can quickly navigate to relevant information.

#### Acceptance Criteria

1. WHEN a user enters a search query THEN the system SHALL perform vector similarity search via `/search` API
2. WHEN search results are returned THEN the system SHALL display up to 8 candidate nodes
3. WHEN a user selects a search result THEN the system SHALL center the graph view on that node
4. WHEN a node is centered THEN the system SHALL highlight it visually to draw attention
5. WHEN search is performed THEN the system SHALL return results within 2 seconds for responsive interaction

### Requirement 5

**User Story:** As a demo presenter, I want to ask questions about the knowledge graph and receive grounded answers with citations, so that I can demonstrate the system's question-answering capabilities.

#### Acceptance Criteria

1. WHEN a user submits a question via `/ask` API THEN the system SHALL embed the question and retrieve top-12 relevant nodes
2. WHEN relevant nodes are identified THEN the system SHALL expand their 1-hop neighborhood using SPARQL queries
3. WHEN context is gathered THEN the system SHALL generate a grounded answer using LLM with node summaries and evidence quotes
4. WHEN an answer is generated THEN the system SHALL return it with citations including node_id, quote, and doc_id
5. WHEN citations are displayed THEN the system SHALL allow users to click through to source nodes in the graph

### Requirement 6

**User Story:** As a demo presenter, I want the system to run reliably in a Docker container on WSL, so that I can demonstrate it consistently across different environments.

#### Acceptance Criteria

1. WHEN the application is containerized THEN it SHALL include all necessary dependencies for Python backend and React frontend
2. WHEN the container starts THEN it SHALL initialize Qdrant vector database and Oxigraph RDF store
3. WHEN the system runs in WSL THEN it SHALL be accessible via localhost ports for demo purposes
4. WHEN the container is restarted THEN it SHALL recover gracefully using in-memory storage for POC simplicity
5. WHEN environment variables are provided THEN the system SHALL configure OpenAI API access and model settings

### Requirement 7

**User Story:** As a demo presenter, I want to export and import graph data, so that I can have an offline backup if network connectivity fails during the demo.

#### Acceptance Criteria

1. WHEN `/graph/export` is called THEN the system SHALL return the current graph as JSON format
2. WHEN graph data is exported THEN it SHALL include all nodes with metadata, edges with confidence scores, and evidence quotes
3. WHEN exported data is available THEN the frontend SHALL be able to render it without backend connectivity
4. WHEN offline mode is activated THEN the system SHALL display a clear indication that it's running from cached data
5. WHEN graph import is needed THEN the system SHALL accept and load previously exported graph data

### Requirement 8

**User Story:** As a demo presenter, I want the system to handle multiple documents and show relationship merging, so that I can demonstrate cross-document knowledge integration.

#### Acceptance Criteria

1. WHEN multiple documents are ingested THEN the system SHALL merge entities across documents using canonicalization rules
2. WHEN entity merging occurs THEN the system SHALL combine aliases, update salience scores, and preserve all source spans
3. WHEN conflicting information is found THEN the system SHALL create `compares_with` relationships between entities
4. WHEN cross-document relationships are identified THEN the system SHALL highlight them visually in the graph
5. WHEN document sources are tracked THEN the system SHALL maintain provenance for all entities and relationships