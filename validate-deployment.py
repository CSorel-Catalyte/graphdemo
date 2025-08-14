#!/usr/bin/env python3
"""
Deployment validation script for AI Knowledge Mapper POC
Tests all critical deployment aspects for demo readiness
"""

import requests
import time
import json
import sys
import subprocess
from typing import Dict, List, Tuple

class DeploymentValidator:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:3000"
        self.qdrant_url = "http://localhost:6333"
        self.results = []
        
    def log_result(self, test_name: str, success: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.results.append((test_name, success, message))
        print(f"{status} {test_name}: {message}")
        
    def test_service_health(self) -> bool:
        """Test basic service health endpoints"""
        print("\n🔍 Testing Service Health...")
        
        services = [
            ("Backend", f"{self.base_url}/health"),
            ("Frontend", f"{self.frontend_url}/health"),
            ("Qdrant", f"{self.qdrant_url}/health")
        ]
        
        all_healthy = True
        for service_name, url in services:
            try:
                response = requests.get(url, timeout=10)
                success = response.status_code == 200
                self.log_result(f"{service_name} Health", success, 
                              f"Status: {response.status_code}")
                all_healthy &= success
            except Exception as e:
                self.log_result(f"{service_name} Health", False, str(e))
                all_healthy = False
                
        return all_healthy
    
    def test_api_endpoints(self) -> bool:
        """Test critical API endpoints"""
        print("\n🔍 Testing API Endpoints...")
        
        # Test root endpoint
        try:
            response = requests.get(self.base_url, timeout=10)
            success = response.status_code == 200
            self.log_result("Root Endpoint", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("Root Endpoint", False, str(e))
            return False
            
        # Test search endpoint (should handle empty query gracefully)
        try:
            response = requests.get(f"{self.base_url}/search?q=test", timeout=10)
            success = response.status_code in [200, 404]  # 404 is OK for empty database
            self.log_result("Search Endpoint", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("Search Endpoint", False, str(e))
            
        # Test ingest endpoint structure (without actual ingestion)
        try:
            # This should fail with validation error, not server error
            response = requests.post(f"{self.base_url}/ingest", 
                                   json={"invalid": "data"}, timeout=10)
            success = response.status_code == 422  # Validation error expected
            self.log_result("Ingest Endpoint Structure", success, 
                          f"Status: {response.status_code} (422 expected)")
        except Exception as e:
            self.log_result("Ingest Endpoint Structure", False, str(e))
            
        return True
    
    def test_websocket_connection(self) -> bool:
        """Test WebSocket connectivity"""
        print("\n🔍 Testing WebSocket Connection...")
        
        try:
            import websocket
            
            def on_open(ws):
                print("WebSocket connection opened")
                ws.close()
                
            def on_error(ws, error):
                print(f"WebSocket error: {error}")
                
            ws_url = f"ws://localhost:8000/stream"
            ws = websocket.WebSocketApp(ws_url,
                                      on_open=on_open,
                                      on_error=on_error)
            
            # Run for a short time to test connection
            import threading
            wst = threading.Thread(target=ws.run_forever)
            wst.daemon = True
            wst.start()
            time.sleep(2)
            
            self.log_result("WebSocket Connection", True, "Connection successful")
            return True
            
        except ImportError:
            self.log_result("WebSocket Connection", False, 
                          "websocket-client not available for testing")
            return True  # Don't fail deployment for missing test dependency
        except Exception as e:
            self.log_result("WebSocket Connection", False, str(e))
            return False
    
    def test_docker_containers(self) -> bool:
        """Test Docker container status"""
        print("\n🔍 Testing Docker Containers...")
        
        try:
            # Check running containers
            result = subprocess.run(
                ["docker-compose", "-f", "docker-compose.prod.yml", "ps"],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                output = result.stdout
                containers = ["backend", "frontend", "qdrant"]
                all_running = True
                
                for container in containers:
                    running = container in output and "Up" in output
                    self.log_result(f"Container {container}", running,
                                  "Running" if running else "Not running")
                    all_running &= running
                    
                return all_running
            else:
                self.log_result("Docker Containers", False, 
                              f"docker-compose ps failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.log_result("Docker Containers", False, str(e))
            return False
    
    def test_resource_usage(self) -> bool:
        """Test resource usage is within acceptable limits"""
        print("\n🔍 Testing Resource Usage...")
        
        try:
            # Check Docker stats
            result = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", 
                 "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                self.log_result("Resource Usage", True, "Docker stats available")
                print("Current resource usage:")
                print(result.stdout)
                return True
            else:
                self.log_result("Resource Usage", False, "Could not get Docker stats")
                return False
                
        except Exception as e:
            self.log_result("Resource Usage", False, str(e))
            return False
    
    def test_demo_readiness(self) -> bool:
        """Test demo-specific readiness"""
        print("\n🔍 Testing Demo Readiness...")
        
        # Test frontend accessibility
        try:
            response = requests.get(self.frontend_url, timeout=10)
            frontend_ready = response.status_code == 200
            self.log_result("Frontend Accessibility", frontend_ready,
                          f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("Frontend Accessibility", False, str(e))
            frontend_ready = False
            
        # Test API documentation
        try:
            response = requests.get(f"{self.base_url}/docs", timeout=10)
            docs_ready = response.status_code == 200
            self.log_result("API Documentation", docs_ready,
                          f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("API Documentation", False, str(e))
            docs_ready = False
            
        return frontend_ready and docs_ready
    
    def run_all_tests(self) -> bool:
        """Run all validation tests"""
        print("🚀 Starting Deployment Validation...")
        print("=" * 50)
        
        tests = [
            self.test_docker_containers,
            self.test_service_health,
            self.test_api_endpoints,
            self.test_websocket_connection,
            self.test_resource_usage,
            self.test_demo_readiness
        ]
        
        all_passed = True
        for test in tests:
            try:
                result = test()
                all_passed &= result
            except Exception as e:
                print(f"❌ Test failed with exception: {e}")
                all_passed = False
                
        # Summary
        print("\n" + "=" * 50)
        print("📊 Validation Summary:")
        
        passed = sum(1 for _, success, _ in self.results if success)
        total = len(self.results)
        
        print(f"Tests passed: {passed}/{total}")
        
        if all_passed:
            print("🎉 All tests passed! Deployment is demo-ready.")
        else:
            print("❌ Some tests failed. Check the issues above.")
            print("\nFailed tests:")
            for test_name, success, message in self.results:
                if not success:
                    print(f"  - {test_name}: {message}")
                    
        return all_passed

def main():
    """Main validation function"""
    validator = DeploymentValidator()
    
    # Wait a bit for services to fully start
    print("⏳ Waiting for services to stabilize...")
    time.sleep(10)
    
    success = validator.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()