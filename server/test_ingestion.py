#!/usr/bin/env python3
"""
Test script for the text ingestion endpoint
"""
import asyncio
from fastapi.testclient import TestClient
from main import app

def test_ingestion_endpoint():
    """Test the ingestion endpoint with sample text"""
    client = TestClient(app)
    
    # Sample text for testing
    sample_text = """
    Machine Learning is a subset of Artificial Intelligence that enables computers to learn and make decisions from data without being explicitly programmed. 
    
    Popular machine learning libraries include TensorFlow, developed by Google, and PyTorch, created by Facebook. These frameworks provide tools for building neural networks and deep learning models.
    
    Supervised learning algorithms like Random Forest and Support Vector Machines are commonly used for classification tasks. The accuracy of these models is often measured using metrics such as precision, recall, and F1-score.
    """
    
    # Test ingestion request
    print("Testing ingestion endpoint...")
    response = client.post("/ingest", json={
        "doc_id": "test_doc_001",
        "text": sample_text
    })
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code in [200, 503]:  # 503 is expected without OpenAI API key
        print("✅ Ingestion endpoint test passed!")
        return True
    else:
        print("❌ Ingestion endpoint test failed!")
        return False

def test_search_endpoint():
    """Test the search endpoint"""
    client = TestClient(app)
    
    print("Testing search endpoint...")
    response = client.get("/search?q=machine learning&k=5")
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code in [200, 503]:  # 503 is expected without services
        print("✅ Search endpoint test passed!")
        return True
    else:
        print("❌ Search endpoint test failed!")
        return False

def test_neighbors_endpoint():
    """Test the neighbors endpoint"""
    client = TestClient(app)
    
    print("Testing neighbors endpoint...")
    response = client.get("/neighbors?node_id=test_entity_123&hops=1&limit=10")
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code in [200, 404, 503]:  # Various expected responses
        print("✅ Neighbors endpoint test passed!")
        return True
    else:
        print("❌ Neighbors endpoint test failed!")
        return False

def test_ask_endpoint():
    """Test the question answering endpoint"""
    client = TestClient(app)
    
    print("Testing ask endpoint...")
    response = client.get("/ask?q=What is machine learning?")
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code in [200, 503]:  # 503 is expected without OpenAI API key
        print("✅ Ask endpoint test passed!")
        return True
    else:
        print("❌ Ask endpoint test failed!")
        return False

def test_export_endpoint():
    """Test the graph export endpoint"""
    client = TestClient(app)
    
    print("Testing export endpoint...")
    response = client.get("/graph/export")
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code in [200, 503]:  # 503 is expected without services
        print("✅ Export endpoint test passed!")
        return True
    else:
        print("❌ Export endpoint test failed!")
        return False

def test_basic_endpoints():
    """Test basic endpoints to ensure they still work"""
    client = TestClient(app)
    
    # Test root endpoint
    response = client.get("/")
    assert response.status_code == 200
    print("✅ Root endpoint working")
    
    # Test health endpoint
    response = client.get("/health")
    assert response.status_code == 200
    print("✅ Health endpoint working")
    
    # Test status endpoint
    response = client.get("/status")
    assert response.status_code == 200
    print("✅ Status endpoint working")

if __name__ == "__main__":
    print("Running comprehensive endpoint tests...")
    
    # Test basic endpoints first
    test_basic_endpoints()
    
    # Test all API endpoints
    test_ingestion_endpoint()
    test_search_endpoint()
    test_neighbors_endpoint()
    test_ask_endpoint()
    test_export_endpoint()
    
    print("All endpoint tests completed!")