"""
WebSocket connection manager for real-time communication.
Handles client connections, message broadcasting, and connection lifecycle.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from models.websocket import WSMessage, WSMessageWrapper, ConnectionMessage, ErrorMessage
from utils.error_handling import (
    error_handler, handle_graceful_degradation, ErrorClassifier
)

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting"""
    
    def __init__(self):
        # Active connections: client_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # Message queues for disconnected clients: client_id -> List[WSMessageWrapper]
        self.message_queues: Dict[str, List[WSMessageWrapper]] = {}
        # Connection metadata: client_id -> dict
        self.connection_metadata: Dict[str, dict] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, client_id: Optional[str] = None) -> str:
        """
        Accept a new WebSocket connection and assign client ID.
        
        Args:
            websocket: The WebSocket connection
            client_id: Optional client ID (generates UUID if not provided)
            
        Returns:
            The assigned client ID
        """
        await websocket.accept()
        
        # Generate client ID if not provided
        if not client_id:
            client_id = str(uuid.uuid4())
        
        async with self._lock:
            # Store connection
            self.active_connections[client_id] = websocket
            self.connection_metadata[client_id] = {
                "connected_at": datetime.utcnow().isoformat(),
                "messages_sent": 0,
                "messages_received": 0
            }
            
            # Send queued messages if any
            if client_id in self.message_queues:
                queued_messages = self.message_queues[client_id]
                logger.info(f"Sending {len(queued_messages)} queued messages to client {client_id}")
                
                for message_wrapper in queued_messages:
                    try:
                        await websocket.send_text(message_wrapper.model_dump_json())
                        self.connection_metadata[client_id]["messages_sent"] += 1
                    except Exception as e:
                        logger.error(f"Error sending queued message to {client_id}: {e}")
                
                # Clear the queue
                del self.message_queues[client_id]
        
        logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")
        
        # Send connection confirmation
        connection_msg = ConnectionMessage(
            status="connected",
            client_id=client_id
        )
        await self.send_personal_message(connection_msg, client_id)
        
        return client_id
    
    async def disconnect(self, client_id: str):
        """
        Remove a WebSocket connection.
        
        Args:
            client_id: The client ID to disconnect
        """
        async with self._lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
            
            if client_id in self.connection_metadata:
                metadata = self.connection_metadata[client_id]
                logger.info(
                    f"Client {client_id} disconnected. "
                    f"Messages sent: {metadata['messages_sent']}, "
                    f"Messages received: {metadata['messages_received']}"
                )
                del self.connection_metadata[client_id]
        
        logger.info(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: WSMessage, client_id: str):
        """
        Send a message to a specific client.
        
        Args:
            message: The message to send
            client_id: Target client ID
        """
        message_wrapper = WSMessageWrapper(
            message=message,
            timestamp=datetime.utcnow().isoformat(),
            client_id=client_id
        )
        
        async with self._lock:
            if client_id in self.active_connections:
                websocket = self.active_connections[client_id]
                try:
                    await websocket.send_text(message_wrapper.model_dump_json())
                    self.connection_metadata[client_id]["messages_sent"] += 1
                    logger.debug(f"Sent message to client {client_id}: {message.type}")
                except Exception as e:
                    logger.error(f"Error sending message to {client_id}: {e}")
                    # Connection might be broken, remove it
                    await self.disconnect(client_id)
            else:
                # Client not connected, queue the message
                if client_id not in self.message_queues:
                    self.message_queues[client_id] = []
                
                self.message_queues[client_id].append(message_wrapper)
                
                # Limit queue size to prevent memory issues
                max_queue_size = 100
                if len(self.message_queues[client_id]) > max_queue_size:
                    self.message_queues[client_id] = self.message_queues[client_id][-max_queue_size:]
                
                logger.debug(f"Queued message for disconnected client {client_id}: {message.type}")
    
    async def broadcast(self, message: WSMessage, exclude_client: Optional[str] = None):
        """
        Broadcast a message to all connected clients.
        
        Args:
            message: The message to broadcast
            exclude_client: Optional client ID to exclude from broadcast
        """
        message_wrapper = WSMessageWrapper(
            message=message,
            timestamp=datetime.utcnow().isoformat(),
            client_id=""  # Empty for broadcast
        )
        
        async with self._lock:
            if not self.active_connections:
                logger.debug("No active connections for broadcast")
                return
            
            # Get list of clients to send to
            target_clients = [
                client_id for client_id in self.active_connections.keys()
                if client_id != exclude_client
            ]
        
        if not target_clients:
            logger.debug("No target clients for broadcast")
            return
        
        logger.debug(f"Broadcasting {message.type} to {len(target_clients)} clients")
        
        # Send to all clients concurrently
        tasks = []
        for client_id in target_clients:
            task = self._send_to_client(message_wrapper, client_id)
            tasks.append(task)
        
        # Wait for all sends to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log any errors
        failed_sends = sum(1 for result in results if isinstance(result, Exception))
        if failed_sends > 0:
            logger.warning(f"Failed to send broadcast to {failed_sends} clients")
    
    @handle_graceful_degradation(fallback_value=None, log_fallback=False)
    async def _send_to_client(self, message_wrapper: WSMessageWrapper, client_id: str):
        """
        Internal method to send a message to a specific client with enhanced error handling.
        
        Args:
            message_wrapper: The wrapped message to send
            client_id: Target client ID
        """
        async with self._lock:
            if client_id not in self.active_connections:
                return
            
            websocket = self.active_connections[client_id]
        
        # Send message with timeout
        try:
            await asyncio.wait_for(
                websocket.send_text(message_wrapper.model_dump_json()),
                timeout=5.0  # 5 second timeout for WebSocket sends
            )
            
            async with self._lock:
                if client_id in self.connection_metadata:
                    self.connection_metadata[client_id]["messages_sent"] += 1
        
        except asyncio.TimeoutError:
            logger.warning(f"Timeout sending message to client {client_id}")
            await self.disconnect(client_id)
            raise Exception(f"WebSocket send timeout for client {client_id}")
        except Exception as e:
            # Classify the error for better handling
            error_info = ErrorClassifier.classify_error(e)
            error_handler.record_error(error_info)
            
            logger.error(f"Error sending message to client {client_id}: {e}")
            # Remove broken connection
            await self.disconnect(client_id)
            raise
    
    async def handle_client_message(self, client_id: str, message_data: str):
        """
        Handle incoming message from a client.
        
        Args:
            client_id: The client ID
            message_data: Raw message data
        """
        try:
            # Parse the message
            message_dict = json.loads(message_data)
            
            # Update message received count
            async with self._lock:
                if client_id in self.connection_metadata:
                    self.connection_metadata[client_id]["messages_received"] += 1
            
            # Log the message (could be extended to handle specific message types)
            logger.debug(f"Received message from client {client_id}: {message_dict.get('type', 'unknown')}")
            
            # For now, we don't process client messages, but this is where
            # you would handle client-to-server communication
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from client {client_id}: {e}")
            error_msg = ErrorMessage(
                error="invalid_json",
                message="Invalid JSON format"
            )
            await self.send_personal_message(error_msg, client_id)
        
        except Exception as e:
            logger.error(f"Error handling message from client {client_id}: {e}")
            error_msg = ErrorMessage(
                error="processing_error",
                message="Error processing message"
            )
            await self.send_personal_message(error_msg, client_id)
    
    def get_connection_stats(self) -> dict:
        """
        Get statistics about current connections.
        
        Returns:
            Dictionary with connection statistics
        """
        return {
            "active_connections": len(self.active_connections),
            "queued_clients": len(self.message_queues),
            "total_queued_messages": sum(len(queue) for queue in self.message_queues.values()),
            "clients": list(self.active_connections.keys())
        }
    
    async def cleanup_stale_connections(self):
        """
        Clean up stale connections and old message queues.
        This should be called periodically.
        """
        # Test all connections by sending a ping
        stale_clients = []
        
        # Get a snapshot of current connections to avoid lock issues
        current_connections = dict(self.active_connections)
        
        for client_id, websocket in current_connections.items():
            try:
                await websocket.ping()
            except Exception:
                stale_clients.append(client_id)
        
        # Remove stale connections
        for client_id in stale_clients:
            logger.info(f"Removing stale connection: {client_id}")
            await self.disconnect(client_id)
        
        # Clean up old message queues (older than 1 hour)
        # This is a simple cleanup - in production you might want more sophisticated logic
        old_queues = []
        
        for client_id in self.message_queues:
            # If client hasn't connected in a while, remove their queue
            # For simplicity, we'll just limit the number of queued clients
            if len(self.message_queues) > 50:  # Arbitrary limit
                old_queues.append(client_id)
        
        for client_id in old_queues[:10]:  # Remove oldest 10
            logger.info(f"Removing old message queue for client: {client_id}")
            del self.message_queues[client_id]


# Global connection manager instance
connection_manager = ConnectionManager()