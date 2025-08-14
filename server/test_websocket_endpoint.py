"""
Tests for the WebSocket endpoint in the FastAPI application.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from unittest.mock import AsyncMock, patch

# Import the FastAPI app
from main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


def test_websocket_stats_endpoint(client):
    """Test the WebSocket stats endpoint"""
    response = client.get("/ws/stats")
    assert response.status_code == 200
    
    data = response.json()
    assert "websocket_stats" in data
    assert "timestamp" in data
    
    stats = data["websocket_stats"]
    assert "active_connections" in stats
    assert "queued_clients" in stats
    assert "total_queued_messages" in stats
    assert "clients" in stats
    
    # Initially should have no connections
    assert stats["active_connections"] == 0
    assert stats["queued_clients"] == 0
    assert stats["total_queued_messages"] == 0
    assert stats["clients"] == []


def test_websocket_endpoint_connection():
    """Test WebSocket endpoint connection (basic connectivity test)"""
    # This is a basic test to ensure the WebSocket endpoint exists
    # Full WebSocket testing requires more complex setup with actual WebSocket clients
    
    with TestClient(app) as client:
        # Test that the WebSocket endpoint exists and can be accessed
        # We can't easily test the full WebSocket functionality with TestClient
        # but we can verify the endpoint is properly configured
        
        # Check that the endpoint is registered
        websocket_routes = [route for route in app.routes if hasattr(route, 'path') and route.path == '/stream']
        assert len(websocket_routes) == 1
        
        # Verify it's a WebSocket route
        websocket_route = websocket_routes[0]
        assert hasattr(websocket_route, 'endpoint')


@pytest.mark.asyncio
async def test_websocket_connection_manager_integration():
    """Test that the WebSocket endpoint uses the connection manager correctly"""
    from services.websocket_manager import connection_manager
    
    # Get initial stats
    initial_stats = connection_manager.get_connection_stats()
    initial_connections = initial_stats["active_connections"]
    
    # The connection manager should be properly initialized
    assert hasattr(connection_manager, 'active_connections')
    assert hasattr(connection_manager, 'message_queues')
    assert hasattr(connection_manager, 'connection_metadata')
    
    # Test that we can call the connection manager methods
    stats = connection_manager.get_connection_stats()
    assert isinstance(stats, dict)
    assert "active_connections" in stats


def test_app_startup_includes_websocket_support():
    """Test that the app is configured with WebSocket support"""
    # Check that the app has WebSocket support enabled
    assert hasattr(app, 'websocket')
    
    # Check that the status endpoint reports WebSocket support
    client = TestClient(app)
    response = client.get("/status")
    assert response.status_code == 200
    
    data = response.json()
    assert "features" in data
    assert data["features"]["websocket_support"] is True
    assert data["features"]["real_time_updates"] is True


def test_websocket_endpoint_in_status():
    """Test that the WebSocket endpoint is listed in the status"""
    client = TestClient(app)
    response = client.get("/status")
    assert response.status_code == 200
    
    data = response.json()
    # The WebSocket endpoint should be documented in the status
    # (though it's not explicitly listed in endpoints since it's not REST)
    assert data["features"]["websocket_support"] is True


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])