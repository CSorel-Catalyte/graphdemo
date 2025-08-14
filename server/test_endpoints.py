#!/usr/bin/env python3
"""
Simple test script to verify FastAPI endpoints are working
"""
import asyncio
import httpx
from main import app
from fastapi.testclient import TestClient

def test_endpoints():
    """Test the basic endpoints"""
    client = TestClient(app)
    
    # Test root endpoint
    print("Testing root endpoint...")
    response = client.get("/")
    print(f"GET / - Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    
    # Test health endpoint
    print("\nTesting health endpoint...")
    response = client.get("/health")
    print(f"GET /health - Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    
    # Test status endpoint
    print("\nTesting status endpoint...")
    response = client.get("/status")
    print(f"GET /status - Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    
    print("\nAll endpoint tests passed!")

if __name__ == "__main__":
    test_endpoints()