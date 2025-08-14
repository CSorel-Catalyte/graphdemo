#!/bin/bash

# WSL-specific deployment script for AI Knowledge Mapper POC
set -e

echo "🚀 Starting AI Knowledge Mapper deployment for WSL..."

# Check if running in WSL
if ! grep -q microsoft /proc/version 2>/dev/null; then
    echo "⚠️  Warning: This script is optimized for WSL environments"
fi

# Check required environment variables
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ Error: OPENAI_API_KEY environment variable is required"
    echo "Please set it with: export OPENAI_API_KEY=your_api_key_here"
    exit 1
fi

# Check Docker availability
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed or not in PATH"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed or not in PATH"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "❌ Error: Docker daemon is not running"
    echo "Please start Docker Desktop or Docker daemon"
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "OPENAI_API_KEY=$OPENAI_API_KEY" >> .env
fi

# Clean up any existing containers
echo "🧹 Cleaning up existing containers..."
docker-compose -f docker-compose.prod.yml down --remove-orphans 2>/dev/null || true

# Build and start services
echo "🔨 Building Docker images..."
docker-compose -f docker-compose.prod.yml build --no-cache

echo "🚀 Starting services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
timeout=120
elapsed=0

while [ $elapsed -lt $timeout ]; do
    if docker-compose -f docker-compose.prod.yml ps | grep -q "Up (healthy)"; then
        break
    fi
    sleep 5
    elapsed=$((elapsed + 5))
    echo "   Waiting... ($elapsed/${timeout}s)"
done

# Check service health
echo "🔍 Checking service health..."
backend_health=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || echo "000")
frontend_health=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/health || echo "000")
qdrant_health=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:6333/health || echo "000")

echo "Service Status:"
echo "  Backend:  $([ "$backend_health" = "200" ] && echo "✅ Healthy" || echo "❌ Unhealthy ($backend_health)")"
echo "  Frontend: $([ "$frontend_health" = "200" ] && echo "✅ Healthy" || echo "❌ Unhealthy ($frontend_health)")"
echo "  Qdrant:   $([ "$qdrant_health" = "200" ] && echo "✅ Healthy" || echo "❌ Unhealthy ($qdrant_health)")"

if [ "$backend_health" = "200" ] && [ "$frontend_health" = "200" ] && [ "$qdrant_health" = "200" ]; then
    echo ""
    echo "🎉 Deployment successful!"
    echo ""
    echo "Access the application at:"
    echo "  Frontend: http://localhost:3000"
    echo "  Backend API: http://localhost:8000"
    echo "  API Docs: http://localhost:8000/docs"
    echo "  Qdrant: http://localhost:6333/dashboard"
    echo ""
    echo "To view logs: docker-compose -f docker-compose.prod.yml logs -f"
    echo "To stop: docker-compose -f docker-compose.prod.yml down"
else
    echo ""
    echo "❌ Deployment failed - some services are not healthy"
    echo "Check logs with: docker-compose -f docker-compose.prod.yml logs"
    exit 1
fi