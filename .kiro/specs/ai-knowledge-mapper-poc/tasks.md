# Implementation Plan

- [x] 1. Set up project structure and development environment





  - Create Docker Compose configuration with backend, frontend, and Qdrant services
  - Set up Python FastAPI project with required dependencies
  - Initialize React TypeScript project with Vite
  - Configure environment variables and development scripts
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 2. Implement core data models and validation





  - [x] 2.1 Create Pydantic models for backend data structures


    - Define Entity, Relationship, Evidence, and SourceSpan models
    - Implement IngestRequest, SearchRequest, and API response models
    - Add validation rules and serialization methods
    - _Requirements: 1.1, 1.2_
  
  - [x] 2.2 Create TypeScript interfaces for frontend


    - Define UINode, UIEdge, and state management interfaces
    - Implement WebSocket message type definitions
    - Create API client interfaces and response types
    - _Requirements: 2.1, 2.2_

- [x] 3. Set up storage layer and database connections





  - [x] 3.1 Implement Qdrant vector database adapter


    - Create QdrantAdapter class with collection initialization
    - Implement vector storage, similarity search, and entity retrieval methods
    - Add error handling and connection management
    - _Requirements: 1.3, 4.1, 4.2_
  
  - [x] 3.2 Implement Oxigraph RDF store adapter


    - Create OxigraphAdapter class for triple storage
    - Implement SPARQL query methods for neighborhood expansion
    - Add RDF serialization and graph traversal utilities
    - _Requirements: 3.4, 5.2_

- [ ] 4. Build information extraction and LLM integration





  - [x] 4.1 Create text chunking utilities


    - Implement chunk_text function with paragraph boundary preservation
    - Add token counting and size validation (≤1800 tokens)
    - Create unit tests for various text formats
    - _Requirements: 1.1_
  
  - [x] 4.2 Implement LLM information extraction service







    - Create OpenAI API client with JSON mode configuration
    - Implement entity and relationship extraction with strict JSON parsing
    - Add prompt templates and response validation
    - Create retry logic and error handling for API failures
    - _Requirements: 1.2_
  
  - [x] 4.3 Build entity canonicalization engine





    - Implement vector similarity comparison (cosine ≥ 0.86)
    - Add alias matching and acronym detection algorithms
    - Create entity merging logic with salience score calculation
    - Write unit tests for merge decision logic
    - _Requirements: 1.3, 8.1, 8.2_

- [x] 5. Create FastAPI backend with core endpoints





  - [x] 5.1 Set up FastAPI application with basic routing


    - Initialize FastAPI app with CORS configuration
    - Create health check and status endpoints
    - Add request logging and error handling middleware
    - _Requirements: 6.1, 6.2_
  
  - [x] 5.2 Implement text ingestion endpoint


    - Create POST /ingest endpoint with request validation
    - Integrate text chunking, IE extraction, and canonicalization
    - Add progress tracking and error handling
    - Write integration tests for complete ingestion workflow
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  
  - [x] 5.3 Implement search and navigation endpoints

    - Create GET /search endpoint with vector similarity search
    - Implement GET /neighbors endpoint with SPARQL graph traversal
    - Add result filtering and pagination
    - Write unit tests for search accuracy and performance
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 3.4_

- [x] 6. Build WebSocket real-time communication





  - [x] 6.1 Implement WebSocket server and connection management


    - Create WebSocket endpoint with connection lifecycle handling
    - Implement client connection tracking and cleanup
    - Add message broadcasting utilities
    - _Requirements: 1.4, 2.5_
  
  - [x] 6.2 Create real-time update broadcasting system


    - Implement message serialization for node and edge updates
    - Add status update broadcasting during processing
    - Create message queuing for disconnected clients
    - Write tests for message delivery and connection handling
    - _Requirements: 1.4, 2.5_

- [x] 7. Implement question-answering system




  - [x] 7.1 Create question processing and context retrieval


    - Implement GET /ask endpoint with question embedding
    - Add top-k node retrieval and neighborhood expansion
    - Create context building from node summaries and evidence
    - _Requirements: 5.1, 5.2_
  
  - [x] 7.2 Build grounded answer generation


    - Implement LLM-based answer generation with citations
    - Add citation extraction and validation
    - Create response formatting with node references
    - Write tests for answer quality and citation accuracy
    - _Requirements: 5.3, 5.4, 5.5_

- [x] 8. Create React frontend foundation





  - [x] 8.1 Set up React application structure


    - Initialize Vite React TypeScript project
    - Configure Tailwind CSS and component structure
    - Set up Zustand state management store
    - Add routing and layout components
    - _Requirements: 2.1, 2.2_
  
  - [x] 8.2 Implement WebSocket client integration


    - Create WebSocket hook with automatic reconnection
    - Implement message handling and state updates
    - Add connection status indicators
    - Write tests for real-time data synchronization
    - _Requirements: 2.5_

- [-] 9. Build 3D graph visualization



  - [x] 9.1 Create Graph3D component with react-force-graph-3d




    - Set up 3D graph canvas with force simulation
    - Implement node rendering with size based on salience
    - Add edge rendering with width based on confidence
    - Configure graph physics and layout parameters
    - _Requirements: 2.1, 2.2_
  
  - [x] 9.2 Add interactive features to graph visualization





    - Implement hover tooltips with entity information
    - Add click selection and highlighting
    - Create graph navigation and zoom controls
    - Write tests for user interaction handling
    - _Requirements: 2.3, 2.4_

- [x] 10. Implement user interface components






  - [x] 10.1 Create search functionality


    - Build SearchBox component with autocomplete
    - Implement search result display and selection
    - Add graph centering and highlighting for selected nodes
    - Write tests for search interaction flow
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
  
  - [x] 10.2 Build side panel for node details













    - Create SidePanel component with node information display
    - Implement evidence quote rendering with source references
    - Add expand neighborhood functionality
    - Create smooth panel animations with Framer Motion
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  
  - [x] 10.3 Create question-answering interface





    - Build QuestionBox component with natural language input
    - Implement answer display with formatted citations
    - Add clickable citations linking to graph nodes
    - Write tests for Q&A user interaction flow
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 11. Add export/import functionality for offline demo





  - [x] 11.1 Implement graph data export


    - Create GET /graph/export endpoint with complete graph serialization
    - Add JSON formatting with all node and edge metadata
    - Implement frontend export trigger and file download
    - _Requirements: 7.1, 7.2_
  
  - [x] 11.2 Build offline mode support


    - Create graph import functionality for cached data
    - Add offline mode detection and UI indicators
    - Implement fallback rendering without backend connectivity
    - Write tests for offline functionality
    - _Requirements: 7.3, 7.4, 7.5_

- [x] 12. Implement multi-document processing and relationship merging





  - [x] 12.1 Add cross-document entity canonicalization


    - Enhance entity merging to handle multiple document sources
    - Implement alias combination and salience score updates
    - Add source span tracking across documents
    - _Requirements: 8.1, 8.2_
  
  - [x] 12.2 Create conflict detection and comparison relationships


    - Implement detection of conflicting information between documents
    - Add creation of "compares_with" relationship types
    - Create visual highlighting for cross-document relationships
    - Write tests for multi-document integration scenarios
    - _Requirements: 8.3, 8.4, 8.5_

- [x] 13. Add comprehensive error handling and resilience





  - [x] 13.1 Implement backend error handling


    - Add LLM API failure handling with exponential backoff
    - Implement database connection error recovery
    - Create graceful degradation for partial failures
    - Add comprehensive logging and monitoring
    - _Requirements: 6.4_
  
  - [x] 13.2 Build frontend error handling and user feedback


    - Create error boundaries for component isolation
    - Implement user-friendly error notifications
    - Add loading states and progress indicators
    - Write tests for error scenarios and recovery
    - _Requirements: 6.4_

- [x] 14. Create demo-ready deployment and testing





  - [x] 14.1 Finalize Docker containerization


    - Optimize Docker images for production builds
    - Add health checks and container orchestration
    - Configure WSL-specific networking and volume mounting
    - Test complete deployment workflow
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  
  - [x] 14.2 Implement demo scenario testing


    - Create smoke tests for all API endpoints
    - Add end-to-end tests for complete user workflows
    - Implement performance tests for demo load scenarios
    - Create seed data and demo script preparation
    - _Requirements: 1.5, 2.5, 3.5, 4.5, 5.5, 7.5, 8.5_

- [x] 15. Polish and optimize for demo presentation





  - [x] 15.1 Add visual polish and animations


    - Implement smooth transitions for graph updates
    - Add loading animations and progress indicators
    - Create polished UI styling with consistent design
    - Optimize rendering performance for smooth demo experience
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  
  - [x] 15.2 Create demo preparation utilities


    - Build seed data loading scripts
    - Create demo scenario documentation
    - Add performance monitoring and optimization
    - Implement final integration testing and validation
    - _Requirements: 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5_