# WSL-specific deployment script for AI Knowledge Mapper POC (PowerShell version)
param(
    [string]$OpenAIKey = $env:OPENAI_API_KEY
)

Write-Host "🚀 Starting AI Knowledge Mapper deployment for WSL..." -ForegroundColor Green

# Check required environment variables
if (-not $OpenAIKey) {
    Write-Host "❌ Error: OPENAI_API_KEY environment variable is required" -ForegroundColor Red
    Write-Host "Please set it with: `$env:OPENAI_API_KEY='your_api_key_here'" -ForegroundColor Yellow
    exit 1
}

# Check Docker availability
try {
    docker --version | Out-Null
} catch {
    Write-Host "❌ Error: Docker is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

try {
    docker-compose --version | Out-Null
} catch {
    Write-Host "❌ Error: Docker Compose is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

# Check if Docker daemon is running
try {
    docker info | Out-Null
} catch {
    Write-Host "❌ Error: Docker daemon is not running" -ForegroundColor Red
    Write-Host "Please start Docker Desktop or Docker daemon" -ForegroundColor Yellow
    exit 1
}

# Create .env file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "📝 Creating .env file..." -ForegroundColor Blue
    Copy-Item ".env.example" ".env"
    Add-Content ".env" "OPENAI_API_KEY=$OpenAIKey"
}

# Clean up any existing containers
Write-Host "🧹 Cleaning up existing containers..." -ForegroundColor Blue
docker-compose -f docker-compose.prod.yml down --remove-orphans 2>$null

# Build and start services
Write-Host "🔨 Building Docker images..." -ForegroundColor Blue
docker-compose -f docker-compose.prod.yml build --no-cache

Write-Host "🚀 Starting services..." -ForegroundColor Blue
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
Write-Host "⏳ Waiting for services to be ready..." -ForegroundColor Blue
$timeout = 120
$elapsed = 0

while ($elapsed -lt $timeout) {
    $status = docker-compose -f docker-compose.prod.yml ps
    if ($status -match "Up \(healthy\)") {
        break
    }
    Start-Sleep 5
    $elapsed += 5
    Write-Host "   Waiting... ($elapsed/${timeout}s)" -ForegroundColor Gray
}

# Check service health
Write-Host "🔍 Checking service health..." -ForegroundColor Blue

try { $backendHealth = (Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing).StatusCode } catch { $backendHealth = 0 }
try { $frontendHealth = (Invoke-WebRequest -Uri "http://localhost:3000/health" -UseBasicParsing).StatusCode } catch { $frontendHealth = 0 }
try { $qdrantHealth = (Invoke-WebRequest -Uri "http://localhost:6333/health" -UseBasicParsing).StatusCode } catch { $qdrantHealth = 0 }

Write-Host "Service Status:" -ForegroundColor White
Write-Host "  Backend:  $(if ($backendHealth -eq 200) { '✅ Healthy' } else { "❌ Unhealthy ($backendHealth)" })" -ForegroundColor $(if ($backendHealth -eq 200) { 'Green' } else { 'Red' })
Write-Host "  Frontend: $(if ($frontendHealth -eq 200) { '✅ Healthy' } else { "❌ Unhealthy ($frontendHealth)" })" -ForegroundColor $(if ($frontendHealth -eq 200) { 'Green' } else { 'Red' })
Write-Host "  Qdrant:   $(if ($qdrantHealth -eq 200) { '✅ Healthy' } else { "❌ Unhealthy ($qdrantHealth)" })" -ForegroundColor $(if ($qdrantHealth -eq 200) { 'Green' } else { 'Red' })

if ($backendHealth -eq 200 -and $frontendHealth -eq 200 -and $qdrantHealth -eq 200) {
    Write-Host ""
    Write-Host "🎉 Deployment successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Access the application at:" -ForegroundColor White
    Write-Host "  Frontend: http://localhost:3000" -ForegroundColor Cyan
    Write-Host "  Backend API: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host "  Qdrant: http://localhost:6333/dashboard" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To view logs: docker-compose -f docker-compose.prod.yml logs -f" -ForegroundColor Yellow
    Write-Host "To stop: docker-compose -f docker-compose.prod.yml down" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "❌ Deployment failed - some services are not healthy" -ForegroundColor Red
    Write-Host "Check logs with: docker-compose -f docker-compose.prod.yml logs" -ForegroundColor Yellow
    exit 1
}