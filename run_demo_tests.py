#!/usr/bin/env python3
"""
Demo testing suite runner
Runs all tests required for demo readiness validation
"""

import subprocess
import sys
import time
import os
from typing import List, Tuple, Dict

class DemoTestRunner:
    """Runs comprehensive demo readiness tests"""
    
    def __init__(self):
        self.test_results = []
        self.server_dir = "server"
        
    def run_command(self, command: List[str], cwd: str = None, timeout: int = 300) -> Tuple[bool, str, str]:
        """Run a command and return success, stdout, stderr"""
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return False, "", str(e)
    
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log a test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append((test_name, success, details))
        print(f"{status} {test_name}")
        if details and not success:
            print(f"    Details: {details}")
    
    def run_smoke_tests(self) -> bool:
        """Run smoke tests for all API endpoints"""
        print("\n🔍 Running Smoke Tests...")
        
        success, stdout, stderr = self.run_command(
            ["python", "-m", "pytest", "test_smoke.py", "-v", "--tb=short"],
            cwd=self.server_dir
        )
        
        self.log_test_result("Smoke Tests", success, stderr if not success else "")
        return success
    
    def run_e2e_tests(self) -> bool:
        """Run end-to-end workflow tests"""
        print("\n🔍 Running End-to-End Tests...")
        
        success, stdout, stderr = self.run_command(
            ["python", "-m", "pytest", "test_e2e_workflows.py", "-v", "--tb=short"],
            cwd=self.server_dir
        )
        
        self.log_test_result("End-to-End Tests", success, stderr if not success else "")
        return success
    
    def run_performance_tests(self) -> bool:
        """Run performance tests for demo scenarios"""
        print("\n🔍 Running Performance Tests...")
        
        success, stdout, stderr = self.run_command(
            ["python", "-m", "pytest", "test_performance.py", "-v", "--tb=short"],
            cwd=self.server_dir
        )
        
        self.log_test_result("Performance Tests", success, stderr if not success else "")
        return success
    
    def run_integration_tests(self) -> bool:
        """Run existing integration tests"""
        print("\n🔍 Running Integration Tests...")
        
        integration_tests = [
            "test_integration_workflow.py",
            "test_ie_integration.py", 
            "test_canonicalization_integration.py",
            "test_multi_document_integration.py"
        ]
        
        all_passed = True
        for test_file in integration_tests:
            if os.path.exists(os.path.join(self.server_dir, test_file)):
                success, stdout, stderr = self.run_command(
                    ["python", "-m", "pytest", test_file, "-v", "--tb=short"],
                    cwd=self.server_dir
                )
                self.log_test_result(f"Integration: {test_file}", success, 
                                   stderr if not success else "")
                all_passed &= success
        
        return all_passed
    
    def run_frontend_tests(self) -> bool:
        """Run frontend tests"""
        print("\n🔍 Running Frontend Tests...")
        
        # Check if frontend tests exist and run them
        client_dir = "client"
        if os.path.exists(os.path.join(client_dir, "package.json")):
            success, stdout, stderr = self.run_command(
                ["npm", "run", "test:run"],
                cwd=client_dir
            )
            self.log_test_result("Frontend Tests", success, stderr if not success else "")
            return success
        else:
            self.log_test_result("Frontend Tests", False, "Frontend directory not found")
            return False
    
    def validate_deployment(self) -> bool:
        """Run deployment validation"""
        print("\n🔍 Running Deployment Validation...")
        
        success, stdout, stderr = self.run_command(
            ["python", "validate-deployment.py"]
        )
        
        self.log_test_result("Deployment Validation", success, stderr if not success else "")
        return success
    
    def test_demo_data_loading(self) -> bool:
        """Test demo data can be loaded successfully"""
        print("\n🔍 Testing Demo Data Loading...")
        
        success, stdout, stderr = self.run_command(
            ["python", "demo_data.py"]
        )
        
        self.log_test_result("Demo Data Loading", success, stderr if not success else "")
        return success
    
    def run_all_tests(self) -> bool:
        """Run all demo readiness tests"""
        print("🚀 Starting Demo Readiness Test Suite")
        print("=" * 60)
        
        # Define test sequence
        test_sequence = [
            ("Backend Smoke Tests", self.run_smoke_tests),
            ("Backend Integration Tests", self.run_integration_tests),
            ("End-to-End Workflows", self.run_e2e_tests),
            ("Performance Tests", self.run_performance_tests),
            ("Frontend Tests", self.run_frontend_tests),
            ("Deployment Validation", self.validate_deployment),
            ("Demo Data Loading", self.test_demo_data_loading)
        ]
        
        overall_success = True
        
        for test_name, test_func in test_sequence:
            try:
                print(f"\n{'='*20} {test_name} {'='*20}")
                result = test_func()
                overall_success &= result
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
                self.log_test_result(test_name, False, str(e))
                overall_success = False
        
        # Print summary
        self.print_summary(overall_success)
        return overall_success
    
    def print_summary(self, overall_success: bool):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 Demo Readiness Test Summary")
        print("=" * 60)
        
        passed = sum(1 for _, success, _ in self.test_results if success)
        total = len(self.test_results)
        
        print(f"Tests passed: {passed}/{total}")
        print(f"Success rate: {passed/total*100:.1f}%")
        
        if overall_success:
            print("\n🎉 All tests passed! System is demo-ready.")
            print("\nDemo readiness checklist:")
            print("✅ All API endpoints working")
            print("✅ End-to-end workflows functional")
            print("✅ Performance meets demo requirements")
            print("✅ Frontend components working")
            print("✅ Deployment is stable")
            print("✅ Demo data can be loaded")
            
            print("\n🚀 Ready to demo! Next steps:")
            print("1. Run: python demo_data.py (if not already done)")
            print("2. Open: http://localhost:3000")
            print("3. Review: DEMO_SCRIPT.md")
            print("4. Present with confidence!")
            
        else:
            print("\n❌ Some tests failed. Demo readiness issues detected.")
            print("\nFailed tests:")
            for test_name, success, details in self.test_results:
                if not success:
                    print(f"  - {test_name}: {details}")
            
            print("\n🔧 Recommended actions:")
            print("1. Review failed test details above")
            print("2. Check application logs for errors")
            print("3. Ensure all services are running")
            print("4. Re-run tests after fixes")
    
    def run_quick_check(self) -> bool:
        """Run a quick subset of tests for rapid validation"""
        print("⚡ Running Quick Demo Readiness Check...")
        
        quick_tests = [
            ("Smoke Tests", self.run_smoke_tests),
            ("Deployment Check", self.validate_deployment)
        ]
        
        success = True
        for test_name, test_func in quick_tests:
            result = test_func()
            success &= result
        
        if success:
            print("✅ Quick check passed! System appears demo-ready.")
        else:
            print("❌ Quick check failed. Run full test suite for details.")
        
        return success

def main():
    """Main test runner function"""
    runner = DemoTestRunner()
    
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        success = runner.run_quick_check()
    else:
        success = runner.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()