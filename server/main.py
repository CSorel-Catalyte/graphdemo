from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import os
import sys
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
from typing import Callable
import uuid

# Load environment variables
load_dotenv()

# Import enhanced error handling and monitoring
from utils.error_handling import error_handler, handle_graceful_degradation, with_retry, RetryConfig, ErrorClassifier
from utils.logging_config import setup_logging, get_request_logger, performance_logger
from utils.health_monitor import health_monitor, register_default_health_checks

# Set up comprehensive logging
loggers = setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    enable_json_logging=os.getenv("JSON_LOGGING", "true").lower() == "true",
    enable_file_logging=os.getenv("FILE_LOGGING", "true").lower() == "true"
)

logger = logging.getLogger(__name__)
request_logger = get_request_logger()

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Enhanced middleware for logging HTTP requests and responses with performance tracking"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        
        # Add request ID to request state for tracking
        request.state.request_id = request_id
        
        # Log request with structured data
        request_logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": str(request.url.path),
                "query_params": str(request.query_params),
                "client_ip": request.client.host if request.client else "unknown"
            }
        )
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log response with performance metrics
            request_logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": str(request.url.path),
                    "status_code": response.status_code,
                    "processing_time": process_time,
                    "client_ip": request.client.host if request.client else "unknown"
                }
            )
            
            # Add headers for debugging and monitoring
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.3f}"
            
            # Track performance metrics
            if hasattr(performance_logger, 'log_metric'):
                performance_logger.log_metric(
                    f"api_response_time_{request.method.lower()}",
                    process_time,
                    {"endpoint": str(request.url.path), "status_code": response.status_code}
                )
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            
            # Log error with context
            request_logger.error(
                f"Request failed: {request.method} {request.url.path} - {str(e)}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": str(request.url.path),
                    "processing_time": process_time,
                    "error": str(e),
                    "client_ip": request.client.host if request.client else "unknown"
                },
                exc_info=True
            )
            
            # Record error in error handler
            error_info = ErrorClassifier.classify_error(e)
            error_info.context = {
                "request_id": request_id,
                "method": request.method,
                "path": str(request.url.path),
                "processing_time": process_time
            }
            error_handler.record_error(error_info)
            
            raise

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Enhanced middleware for global error handling with graceful degradation"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except HTTPException:
            # Re-raise HTTP exceptions (they're handled by FastAPI)
            raise
        except Exception as e:
            # Get request ID if available
            request_id = getattr(request.state, 'request_id', 'unknown')
            
            # Classify the error
            from utils.error_handling import ErrorClassifier
            error_info = ErrorClassifier.classify_error(e)
            error_info.context = {
                "request_id": request_id,
                "method": request.method,
                "path": str(request.url.path)
            }
            error_handler.record_error(error_info)
            
            # Log with structured data
            logger.error(
                f"Unhandled exception in request {request_id}: {str(e)}",
                extra={
                    "request_id": request_id,
                    "error_id": error_info.error_id,
                    "error_category": error_info.category.value,
                    "error_severity": error_info.severity.value
                },
                exc_info=True
            )
            
            # Return appropriate error response based on severity
            if error_info.severity.value == "critical":
                status_code = 503
                message = "Service temporarily unavailable"
            else:
                status_code = 500
                message = "An unexpected error occurred"
            
            return JSONResponse(
                status_code=status_code,
                content={
                    "error": "Internal server error",
                    "message": message,
                    "request_id": request_id,
                    "error_id": error_info.error_id
                }
            )

app = FastAPI(
    title="AI Knowledge Mapper API",
    description="Backend API for AI-powered knowledge graph extraction and visualization",
    version="1.0.0"
)

# Add middleware (order matters - last added is executed first)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Basic health check endpoint"""
    return {"message": "AI Knowledge Mapper API is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Enhanced health check with comprehensive service monitoring"""
    try:
        # Get overall health from health monitor
        overall_health = health_monitor.get_overall_health()
        
        # Determine HTTP status code based on health
        status_code = 200
        if overall_health["status"] in ["unhealthy", "critical"]:
            status_code = 503
        elif overall_health["status"] == "degraded":
            status_code = 200  # Still operational but degraded
        
        # Add basic environment info
        from services.ai_provider import AIProviderFactory
        provider_info = AIProviderFactory.get_provider_info()
        
        overall_health["environment"] = {
            "ai_provider": provider_info,
            "python_version": sys.version.split()[0],
            "log_level": os.getenv("LOG_LEVEL", "INFO")
        }
        
        return JSONResponse(
            status_code=status_code,
            content=overall_health
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        error_handler.record_error(ErrorClassifier.classify_error(e))
        
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "message": "Health check system failure"
            }
        )

@app.get("/health/metrics")
async def get_health_metrics(hours: int = 1):
    """Get system performance metrics for the specified time period"""
    try:
        if hours < 1 or hours > 24:
            raise HTTPException(status_code=400, detail="Hours must be between 1 and 24")
        
        metrics = health_monitor.get_metrics_summary(hours=hours)
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting health metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get health metrics: {str(e)}"
        )

@app.get("/health/errors")
async def get_error_statistics():
    """Get error statistics and monitoring data"""
    try:
        error_stats = error_handler.get_error_statistics()
        return error_stats
        
    except Exception as e:
        logger.error(f"Error getting error statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get error statistics: {str(e)}"
        )

@app.get("/status")
async def get_status():
    """API status and configuration information"""
    return {
        "api_name": "AI Knowledge Mapper",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "ingest": "/ingest (POST)",
            "search": "/search (GET)",
            "neighbors": "/neighbors (GET)",
            "ask": "/ask (GET)",
            "export": "/graph/export (GET)"
        },
        "features": {
            "websocket_support": True,
            "real_time_updates": True,
            "vector_search": True,
            "graph_traversal": True,
            "question_answering": True
        }
    }

# Global service instances (will be initialized on startup)
qdrant_adapter = None
oxigraph_adapter = None
ie_service = None
canonicalizer = None

# Import WebSocket manager
from services.websocket_manager import connection_manager

@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup with enhanced error handling"""
    global qdrant_adapter, oxigraph_adapter, ie_service, canonicalizer
    
    try:
        logger.info("Starting application initialization...")
        
        # Register default health checks
        register_default_health_checks()
        
        # Start health monitoring
        await health_monitor.start_monitoring()
        
        # Initialize storage adapters with error handling
        from storage.qdrant_adapter import QdrantAdapter
        from storage.oxigraph_adapter import OxigraphAdapter
        
        qdrant_adapter = QdrantAdapter(url=os.getenv("QDRANT_URL", "http://localhost:6333"))
        oxigraph_adapter = OxigraphAdapter()  # In-memory for POC
        
        # Try to connect to storage services with graceful degradation
        qdrant_connected = False
        oxigraph_connected = False
        
        try:
            qdrant_connected = await qdrant_adapter.connect()
            if qdrant_connected:
                logger.info("Qdrant connection established successfully")
                
                # Register Qdrant health check
                async def check_qdrant_health():
                    health_info = await qdrant_adapter.health_check()
                    return {
                        "status": "healthy" if health_info.get("connected") else "unhealthy",
                        "details": health_info
                    }
                
                health_monitor.register_health_check(
                    "qdrant",
                    check_qdrant_health,
                    interval_seconds=60,
                    critical=True
                )
            else:
                logger.warning("Qdrant connection failed - vector search will be limited")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant: {e}")
            error_handler.record_error(ErrorClassifier.classify_error(e))
        
        try:
            oxigraph_connected = await oxigraph_adapter.connect()
            if oxigraph_connected:
                logger.info("Oxigraph connection established successfully")
                
                # Register Oxigraph health check
                async def check_oxigraph_health():
                    health_info = await oxigraph_adapter.health_check()
                    return {
                        "status": "healthy" if health_info.get("initialized") else "unhealthy",
                        "details": health_info
                    }
                
                health_monitor.register_health_check(
                    "oxigraph",
                    check_oxigraph_health,
                    interval_seconds=60,
                    critical=True
                )
            else:
                logger.warning("Oxigraph connection failed - graph traversal will be limited")
        except Exception as e:
            logger.error(f"Failed to initialize Oxigraph: {e}")
            error_handler.record_error(ErrorClassifier.classify_error(e))
        
        # Initialize AI provider and IE service
        try:
            from services.ai_provider import initialize_ai_provider, get_ai_provider, AIProviderFactory
            from services.ie_service import InformationExtractionService
            
            # Initialize AI provider
            ai_provider = initialize_ai_provider()
            provider_info = AIProviderFactory.get_provider_info()
            logger.info(f"AI provider initialized: {provider_info['provider']} ({provider_info['type']})")
            
            # Initialize IE service
            ie_service = InformationExtractionService()
            logger.info("Information extraction service initialized")
            
            # Register AI provider health check
            async def check_ai_provider_health():
                try:
                    # Simple test call to check API availability
                    response = await ai_provider.create_embedding(
                        input_text="test",
                        encoding_format="float"
                    )
                    return {"status": "healthy", "details": {"api_accessible": True, "provider": provider_info}}
                except Exception as e:
                    return {
                        "status": "unhealthy",
                        "details": {"api_accessible": False, "error": str(e), "provider": provider_info}
                    }
            
            health_monitor.register_health_check(
                "ai_provider",
                check_ai_provider_health,
                interval_seconds=300,  # Check every 5 minutes
                critical=True
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize AI provider or IE service: {e}")
            error_handler.record_error(ErrorClassifier.classify_error(e))
            logger.warning("AI services will be disabled - information extraction will not be available")
        
        # Initialize canonicalizer
        if qdrant_adapter and qdrant_connected:
            try:
                from services.canonicalization import EntityCanonicalizer
                canonicalizer = EntityCanonicalizer(qdrant_adapter)
                logger.info("Entity canonicalizer initialized")
            except Exception as e:
                logger.error(f"Failed to initialize canonicalizer: {e}")
                error_handler.record_error(ErrorClassifier.classify_error(e))
        
        # Log startup summary
        services_status = {
            "qdrant": "connected" if qdrant_connected else "failed",
            "oxigraph": "connected" if oxigraph_connected else "failed",
            "ie_service": "initialized" if ie_service else "not_available",
            "canonicalizer": "initialized" if canonicalizer else "not_available"
        }
        
        logger.info(f"Service initialization complete: {services_status}")
        
        # Start performance monitoring
        if hasattr(performance_logger, 'start_timer'):
            performance_logger.start_timer("application_startup")
            performance_logger.end_timer("application_startup", {"services": services_status})
        
    except Exception as e:
        logger.critical(f"Critical error during startup: {e}", exc_info=True)
        error_handler.record_error(ErrorClassifier.classify_error(e))
        # Don't raise - allow app to start in degraded mode

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on application shutdown with enhanced error handling"""
    global qdrant_adapter, oxigraph_adapter
    
    try:
        logger.info("Starting application shutdown...")
        
        # Stop health monitoring
        await health_monitor.stop_monitoring()
        
        # Close storage connections with error handling
        cleanup_errors = []
        
        if qdrant_adapter:
            try:
                await qdrant_adapter.close()
                logger.info("Qdrant connection closed")
            except Exception as e:
                cleanup_errors.append(f"Qdrant cleanup error: {e}")
                logger.error(f"Error closing Qdrant connection: {e}")
        
        if oxigraph_adapter:
            try:
                await oxigraph_adapter.close()
                logger.info("Oxigraph connection closed")
            except Exception as e:
                cleanup_errors.append(f"Oxigraph cleanup error: {e}")
                logger.error(f"Error closing Oxigraph connection: {e}")
        
        # Log cleanup summary
        if cleanup_errors:
            logger.warning(f"Shutdown completed with {len(cleanup_errors)} errors: {cleanup_errors}")
        else:
            logger.info("Application shutdown completed successfully")
        
    except Exception as e:
        logger.critical(f"Critical error during shutdown: {e}", exc_info=True)
        error_handler.record_error(ErrorClassifier.classify_error(e))

# Import API models
from models.api import (
    IngestRequest, IngestResponse, SearchRequest, SearchResponse,
    NeighborsRequest, NeighborsResponse, QuestionRequest, QuestionResponse,
    GraphExportResponse, ErrorResponse
)

@app.post("/ingest", response_model=IngestResponse)
async def ingest_text(request: IngestRequest):
    """
    Ingest text and extract knowledge graph entities and relationships.
    
    This endpoint processes text through the complete pipeline:
    1. Text chunking with paragraph boundary preservation
    2. LLM-based information extraction
    3. Entity canonicalization via vector similarity
    4. Storage in vector and graph databases
    5. Real-time updates via WebSocket
    """
    start_time = time.time()
    
    try:
        logger.info(f"Starting ingestion for document {request.doc_id}")
        
        # Validate services are available
        if not ie_service:
            raise HTTPException(
                status_code=503,
                detail="Information extraction service not available. Please configure OpenAI API key."
            )
        
        # Step 1: Text chunking
        from services.text_chunking import chunk_text
        chunks = chunk_text(request.text, max_tokens=1800)
        
        if not chunks:
            return IngestResponse(
                success=True,
                doc_id=request.doc_id,
                chunks_processed=0,
                entities_extracted=0,
                relationships_extracted=0,
                processing_time=time.time() - start_time,
                message="No content to process"
            )
        
        logger.info(f"Split text into {len(chunks)} chunks")
        
        # Send status update for chunking completion
        from models.websocket import StatusMessage
        status_msg = StatusMessage(
            stage="chunking_complete",
            count=len(chunks),
            total=len(chunks),
            message=f"Split text into {len(chunks)} chunks"
        )
        await connection_manager.broadcast(status_msg)
        
        # Step 2: Information extraction from chunks
        status_msg = StatusMessage(
            stage="extracting_entities",
            count=0,
            total=len(chunks),
            message="Starting information extraction from chunks"
        )
        await connection_manager.broadcast(status_msg)
        
        ie_results = await ie_service.extract_from_chunks(chunks, request.doc_id)
        
        # Collect all entities and relationships
        all_entities = []
        all_relationships = []
        
        for result in ie_results:
            all_entities.extend(result.entities)
            all_relationships.extend(result.relationships)
        
        logger.info(f"Extracted {len(all_entities)} entities and {len(all_relationships)} relationships")
        
        # Send status update for extraction completion
        status_msg = StatusMessage(
            stage="extraction_complete",
            count=len(all_entities),
            total=len(all_entities),
            message=f"Extracted {len(all_entities)} entities and {len(all_relationships)} relationships"
        )
        await connection_manager.broadcast(status_msg)
        
        # Step 3: Entity canonicalization (if available)
        canonical_entities = all_entities
        if canonicalizer and all_entities:
            try:
                status_msg = StatusMessage(
                    stage="canonicalizing_entities",
                    count=0,
                    total=len(all_entities),
                    message="Starting entity canonicalization"
                )
                await connection_manager.broadcast(status_msg)
                
                canonical_entities = await canonicalizer.canonicalize_entities(all_entities)
                logger.info(f"Canonicalized to {len(canonical_entities)} entities")
                
                status_msg = StatusMessage(
                    stage="canonicalization_complete",
                    count=len(canonical_entities),
                    total=len(all_entities),
                    message=f"Canonicalized to {len(canonical_entities)} entities"
                )
                await connection_manager.broadcast(status_msg)
            except Exception as e:
                logger.warning(f"Canonicalization failed, using original entities: {e}")
                status_msg = StatusMessage(
                    stage="canonicalization_failed",
                    count=len(all_entities),
                    total=len(all_entities),
                    message="Canonicalization failed, using original entities"
                )
                await connection_manager.broadcast(status_msg)
        
        # Step 4: Conflict detection and comparison relationships
        comparison_relationships = []
        if len(canonical_entities) > 1:
            try:
                status_msg = StatusMessage(
                    stage="detecting_conflicts",
                    count=0,
                    total=len(canonical_entities),
                    message="Detecting conflicts and creating comparison relationships"
                )
                await connection_manager.broadcast(status_msg)
                
                from services.conflict_detection import detect_and_create_comparisons
                comparison_relationships, conflict_analysis = detect_and_create_comparisons(canonical_entities)
                
                if comparison_relationships:
                    logger.info(f"Created {len(comparison_relationships)} comparison relationships")
                    all_relationships.extend(comparison_relationships)
                
                status_msg = StatusMessage(
                    stage="conflict_detection_complete",
                    count=len(comparison_relationships),
                    total=len(canonical_entities),
                    message=f"Created {len(comparison_relationships)} comparison relationships"
                )
                await connection_manager.broadcast(status_msg)
                
            except Exception as e:
                logger.warning(f"Conflict detection failed: {e}")
                status_msg = StatusMessage(
                    stage="conflict_detection_failed",
                    count=0,
                    total=len(canonical_entities),
                    message="Conflict detection failed, continuing without comparisons"
                )
                await connection_manager.broadcast(status_msg)

        # Step 5: Store in databases
        status_msg = StatusMessage(
            stage="storing_data",
            count=0,
            total=len(canonical_entities) + len(all_relationships),
            message="Starting data storage"
        )
        await connection_manager.broadcast(status_msg)
        
        stored_entities = 0
        stored_relationships = 0
        
        # Store entities in Qdrant (if available)
        if qdrant_adapter:
            try:
                stored_entities = await qdrant_adapter.store_entities(canonical_entities)
                logger.info(f"Stored {stored_entities} entities in Qdrant")
            except Exception as e:
                logger.error(f"Error storing entities in Qdrant: {e}")
        
        # Store entities and relationships in Oxigraph (if available)
        if oxigraph_adapter:
            try:
                # Store entities
                for entity in canonical_entities:
                    await oxigraph_adapter.store_entity(entity)
                
                # Store relationships
                for relationship in all_relationships:
                    await oxigraph_adapter.store_relationship(relationship)
                    stored_relationships += 1
                
                logger.info(f"Stored {len(canonical_entities)} entities and {stored_relationships} relationships in Oxigraph")
            except Exception as e:
                logger.error(f"Error storing in Oxigraph: {e}")
        
        # Send storage completion status
        status_msg = StatusMessage(
            stage="storage_complete",
            count=stored_entities + stored_relationships,
            total=len(canonical_entities) + len(all_relationships),
            message=f"Stored {stored_entities} entities and {stored_relationships} relationships"
        )
        await connection_manager.broadcast(status_msg)
        
        # Step 5: Real-time updates (WebSocket broadcasting)
        if canonical_entities:
            from models.websocket import UpsertNodesMessage
            nodes_message = UpsertNodesMessage(nodes=canonical_entities)
            await connection_manager.broadcast(nodes_message)
            logger.info(f"Broadcasted {len(canonical_entities)} node updates via WebSocket")
        
        if all_relationships:
            from models.websocket import UpsertEdgesMessage
            edges_message = UpsertEdgesMessage(edges=all_relationships)
            await connection_manager.broadcast(edges_message)
            logger.info(f"Broadcasted {len(all_relationships)} edge updates via WebSocket")
        
        processing_time = time.time() - start_time
        
        logger.info(
            f"Ingestion complete for {request.doc_id}: "
            f"{len(canonical_entities)} entities, {len(all_relationships)} relationships "
            f"in {processing_time:.2f}s"
        )
        
        return IngestResponse(
            success=True,
            doc_id=request.doc_id,
            chunks_processed=len(chunks),
            entities_extracted=len(canonical_entities),
            relationships_extracted=len(all_relationships),
            processing_time=processing_time,
            message=f"Successfully processed {len(chunks)} chunks"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during ingestion: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}"
        )

@app.get("/search", response_model=SearchResponse)
async def search_entities(q: str, k: int = 8):
    """
    Search for entities using vector similarity search.
    
    Args:
        q: Search query string
        k: Number of results to return (1-50)
    """
    start_time = time.time()
    
    try:
        # Validate parameters
        if not q or not q.strip():
            raise HTTPException(status_code=400, detail="Search query cannot be empty")
        
        if k < 1 or k > 50:
            raise HTTPException(status_code=400, detail="k must be between 1 and 50")
        
        # Check if services are available
        if not qdrant_adapter:
            raise HTTPException(
                status_code=503,
                detail="Vector search service not available"
            )
        
        if not ie_service:
            raise HTTPException(
                status_code=503,
                detail="Embedding service not available. Please configure OpenAI API key."
            )
        
        logger.info(f"Search query: '{q}' (k={k})")
        
        # Generate embedding for search query
        try:
            from services.ai_provider import get_ai_provider
            ai_provider = get_ai_provider()
            
            response = await ai_provider.create_embedding(
                input_text=q.strip(),
                encoding_format="float"
            )
            query_embedding = response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating search embedding: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to generate search embedding"
            )
        
        # Perform vector similarity search
        similar_entities = await qdrant_adapter.search_entities_by_text(
            query_embedding=query_embedding,
            limit=k
        )
        
        # Convert to SearchResult objects
        from models.api import SearchResult
        results = []
        for entity, score in similar_entities:
            results.append(SearchResult(
                entity=entity,
                score=score
            ))
        
        processing_time = time.time() - start_time
        
        logger.info(f"Found {len(results)} search results for query '{q}'")
        
        return SearchResponse(
            results=results,
            query=q.strip(),
            total_results=len(results),
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during search: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@app.get("/neighbors", response_model=NeighborsResponse)
async def get_neighbors(node_id: str, hops: int = 1, limit: int = 200):
    """
    Get neighboring entities using SPARQL graph traversal.
    
    Args:
        node_id: Target node ID
        hops: Number of hops to expand (1-3)
        limit: Maximum number of results (1-1000)
    """
    start_time = time.time()
    
    try:
        # Validate parameters
        if not node_id or not node_id.strip():
            raise HTTPException(status_code=400, detail="node_id cannot be empty")
        
        if hops < 1 or hops > 3:
            raise HTTPException(status_code=400, detail="hops must be between 1 and 3")
        
        if limit < 1 or limit > 1000:
            raise HTTPException(status_code=400, detail="limit must be between 1 and 1000")
        
        # Check if services are available
        if not oxigraph_adapter:
            raise HTTPException(
                status_code=503,
                detail="Graph traversal service not available"
            )
        
        if not qdrant_adapter:
            raise HTTPException(
                status_code=503,
                detail="Entity storage service not available"
            )
        
        logger.info(f"Getting neighbors for node {node_id} (hops={hops}, limit={limit})")
        
        # Get the center entity
        center_entity = await qdrant_adapter.get_entity(node_id)
        if not center_entity:
            raise HTTPException(
                status_code=404,
                detail=f"Entity {node_id} not found"
            )
        
        # Get neighbors from graph
        neighbor_info = await oxigraph_adapter.get_neighbors(
            entity_id=node_id,
            hops=hops,
            limit=limit
        )
        
        # Get full entity data for neighbors
        neighbor_ids = [info["entity_id"] for info in neighbor_info]
        neighbor_entities = await qdrant_adapter.get_entities_by_ids(neighbor_ids)
        
        # Get relationships
        relationships = await oxigraph_adapter.get_entity_relationships(node_id)
        
        # Convert to Relationship objects
        relationship_objects = []
        for rel_info in relationships:
            from models.core import Relationship, RelationType, Evidence
            try:
                relationship_objects.append(Relationship(
                    from_entity=rel_info["from_entity"],
                    to_entity=rel_info["to_entity"],
                    predicate=RelationType(rel_info["predicate"]),
                    confidence=rel_info["confidence"],
                    evidence=[Evidence(
                        doc_id=ev["doc_id"],
                        quote=ev["quote"],
                        offset=0
                    ) for ev in rel_info.get("evidence", [])],
                    directional=rel_info["directional"]
                ))
            except Exception as e:
                logger.warning(f"Error converting relationship: {e}")
                continue
        
        processing_time = time.time() - start_time
        
        logger.info(f"Found {len(neighbor_entities)} neighbors and {len(relationship_objects)} relationships")
        
        return NeighborsResponse(
            center_node=center_entity,
            neighbors=neighbor_entities,
            relationships=relationship_objects,
            total_neighbors=len(neighbor_entities),
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting neighbors: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Neighbor search failed: {str(e)}"
        )

@app.get("/ask", response_model=QuestionResponse)
async def ask_question(q: str):
    """
    Answer questions using the knowledge graph with grounded citations.
    
    Args:
        q: Natural language question
    """
    start_time = time.time()
    
    try:
        # Validate parameters
        if not q or not q.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        # Check if services are available
        if not ie_service:
            raise HTTPException(
                status_code=503,
                detail="Question answering service not available. Please configure OpenAI API key."
            )
        
        if not qdrant_adapter:
            raise HTTPException(
                status_code=503,
                detail="Vector search service not available for question answering."
            )
        
        if not oxigraph_adapter:
            raise HTTPException(
                status_code=503,
                detail="Graph traversal service not available for question answering."
            )
        
        logger.info(f"Question: '{q}'")
        
        # Step 1: Embed the question
        from services.qa_service import QuestionAnsweringService
        qa_service = QuestionAnsweringService(
            ie_service=ie_service,
            qdrant_adapter=qdrant_adapter,
            oxigraph_adapter=oxigraph_adapter
        )
        
        # Step 2: Process question and generate answer
        result = await qa_service.answer_question(q.strip())
        
        processing_time = time.time() - start_time
        
        return QuestionResponse(
            answer=result.answer,
            citations=result.citations,
            question=q.strip(),
            confidence=result.confidence,
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Question answering failed: {str(e)}"
        )

@app.get("/graph/export", response_model=GraphExportResponse)
async def export_graph():
    """
    Export the complete knowledge graph as structured data.
    """
    start_time = time.time()
    
    try:
        # Check if services are available
        if not oxigraph_adapter:
            raise HTTPException(
                status_code=503,
                detail="Graph export service not available"
            )
        
        logger.info("Exporting graph data")
        
        # Export from Oxigraph
        graph_data = await oxigraph_adapter.export_graph()
        
        # Convert to API response format
        from models.core import Entity, Relationship, EntityType, RelationType, Evidence
        
        entities = []
        relationships = []
        
        # Convert entities (simplified for export)
        for entity_data in graph_data.get("entities", []):
            try:
                entity = Entity(
                    id=entity_data["id"],
                    name=entity_data["name"],
                    type=EntityType(entity_data["type"]),
                    aliases=[],
                    embedding=[],
                    salience=entity_data.get("salience", 0.0),
                    source_spans=[],
                    summary=entity_data.get("summary", "")
                )
                entities.append(entity)
            except Exception as e:
                logger.warning(f"Error converting entity for export: {e}")
                continue
        
        # Convert relationships
        for rel_data in graph_data.get("relationships", []):
            try:
                relationship = Relationship(
                    from_entity=rel_data["from"],
                    to_entity=rel_data["to"],
                    predicate=RelationType(rel_data["predicate"]),
                    confidence=rel_data.get("confidence", 0.0),
                    evidence=[],
                    directional=rel_data.get("directional", True)
                )
                relationships.append(relationship)
            except Exception as e:
                logger.warning(f"Error converting relationship for export: {e}")
                continue
        
        processing_time = time.time() - start_time
        
        logger.info(f"Exported {len(entities)} entities and {len(relationships)} relationships")
        
        return GraphExportResponse(
            nodes=entities,
            edges=relationships,
            metadata={
                "export_source": "oxigraph",
                "processing_time": processing_time
            },
            export_timestamp=datetime.utcnow().isoformat(),
            total_nodes=len(entities),
            total_edges=len(relationships)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting graph: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Graph export failed: {str(e)}"
        )

@app.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket, client_id: str = None):
    """
    WebSocket endpoint for real-time communication.
    
    Handles client connections and provides real-time updates for:
    - Node additions and updates
    - Edge additions and updates  
    - Processing status updates
    - Error notifications
    
    Args:
        websocket: The WebSocket connection
        client_id: Optional client identifier (UUID generated if not provided)
    """
    assigned_client_id = None
    
    try:
        # Connect the client
        assigned_client_id = await connection_manager.connect(websocket, client_id)
        logger.info(f"WebSocket client {assigned_client_id} connected")
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client
                data = await websocket.receive_text()
                
                # Handle the message
                await connection_manager.handle_client_message(assigned_client_id, data)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket client {assigned_client_id} disconnected normally")
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message from {assigned_client_id}: {e}")
                # Send error message to client
                from models.websocket import ErrorMessage
                error_msg = ErrorMessage(
                    error="message_handling_error",
                    message=f"Error processing message: {str(e)}"
                )
                await connection_manager.send_personal_message(error_msg, assigned_client_id)
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket client {assigned_client_id or 'unknown'} disconnected during handshake")
    except Exception as e:
        logger.error(f"WebSocket connection error for client {assigned_client_id or 'unknown'}: {e}")
    finally:
        # Clean up connection
        if assigned_client_id:
            await connection_manager.disconnect(assigned_client_id)

@app.get("/ws/stats")
async def get_websocket_stats():
    """
    Get WebSocket connection statistics.
    Useful for monitoring and debugging.
    """
    try:
        stats = connection_manager.get_connection_stats()
        return {
            "websocket_stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting WebSocket stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get WebSocket stats: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)