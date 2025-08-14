#!/usr/bin/env python3
"""
Validation script to check if the project structure is correctly set up.
"""

import os
import json
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists and print status."""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} (missing)")
        return False

def check_json_valid(filepath, description):
    """Check if a JSON file is valid."""
    if not os.path.exists(filepath):
        print(f"❌ {description}: {filepath} (missing)")
        return False
    
    try:
        with open(filepath, 'r') as f:
            json.load(f)
        print(f"✅ {description}: {filepath} (valid JSON)")
        return True
    except json.JSONDecodeError as e:
        print(f"❌ {description}: {filepath} (invalid JSON: {e})")
        return False

def main():
    print("🔍 Validating AI Knowledge Mapper project structure...\n")
    
    all_good = True
    
    # Check root configuration files
    print("📁 Root Configuration:")
    all_good &= check_file_exists("docker-compose.yml", "Docker Compose config")
    all_good &= check_file_exists(".env.example", "Environment template")
    all_good &= check_file_exists("package.json", "Root package.json")
    all_good &= check_file_exists("README.md", "README documentation")
    all_good &= check_file_exists(".gitignore", "Git ignore file")
    
    print("\n🐍 Backend (Python FastAPI):")
    all_good &= check_file_exists("server/Dockerfile", "Backend Dockerfile")
    all_good &= check_file_exists("server/requirements.txt", "Python dependencies")
    all_good &= check_file_exists("server/main.py", "FastAPI application")
    
    print("\n⚛️ Frontend (React TypeScript):")
    all_good &= check_file_exists("client/Dockerfile", "Frontend Dockerfile")
    all_good &= check_json_valid("client/package.json", "Frontend package.json")
    all_good &= check_file_exists("client/vite.config.ts", "Vite configuration")
    all_good &= check_file_exists("client/tsconfig.json", "TypeScript config")
    all_good &= check_file_exists("client/tailwind.config.js", "Tailwind config")
    all_good &= check_file_exists("client/index.html", "HTML template")
    all_good &= check_file_exists("client/src/main.tsx", "React entry point")
    all_good &= check_file_exists("client/src/App.tsx", "Main App component")
    all_good &= check_file_exists("client/src/index.css", "CSS styles")
    
    print("\n📊 Summary:")
    if all_good:
        print("🎉 All files are present and valid!")
        print("\n🚀 Next steps:")
        print("1. Copy .env.example to .env and add your OPENAI_API_KEY")
        print("2. Start Docker Desktop")
        print("3. Run: npm run dev")
        print("4. Access frontend at http://localhost:3000")
        print("5. Access backend at http://localhost:8000")
    else:
        print("⚠️ Some files are missing or invalid. Please check the errors above.")
    
    return all_good

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)