# AI Knowledge Mapper

An interactive AI-powered knowledge graph system that converts arbitrary text into structured knowledge representations with 3D visualization.

## Features

- Real-time knowledge extraction from text using LLMs
- Entity canonicalization through vector similarity
- Interactive 3D graph visualization
- Question-answering with grounded citations
- WebSocket-based real-time updates

## Prerequisites

- **Docker Engine** and **Docker Compose** (Docker Desktop is optional)
- **AI Provider**: Either OpenAI API key OR Azure OpenAI configuration

### Docker Installation Options

You have several options for running Docker:

#### Option 1: Docker Engine + Docker Compose (Lightweight)
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io docker-compose-plugin

# Or install Docker Compose standalone
sudo apt install docker-compose

# Add user to docker group (logout/login required)
sudo usermod -aG docker $USER
```

#### Option 2: Docker Desktop (Full GUI)
- Download from [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Includes Docker Engine, Docker Compose, and GUI management
- Heavier resource usage but easier management

#### Option 3: WSL2 with Docker Engine
```bash
# In WSL2 Ubuntu
sudo apt update
sudo apt install docker.io docker-compose-plugin
sudo service docker start

# Or use Docker Desktop with WSL2 integration
```

**Recommendation**: For development and demos, Docker Engine + Docker Compose is sufficient and more resource-efficient than Docker Desktop.

### Verify Docker Installation
```bash
# Check Docker Engine
docker --version
# Expected: Docker version 20.10.0+

# Check Docker Compose
docker-compose --version
# Expected: docker-compose version 1.29.0+ or Docker Compose version 2.0.0+

# Test Docker functionality
docker run hello-world
# Should download and run successfully
```

## Quick Start

1. **Clone and setup environment:**
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

2. **Start the application:**
   ```bash
   npm run dev
   ```

3. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## AI Provider Configuration

The AI Knowledge Mapper supports both OpenAI and Azure OpenAI as AI providers. Configure one of the following options in your `.env` file:

### Option 1: OpenAI (Default)

```bash
# Standard OpenAI Configuration
AI_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo-1106
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
```

### Option 2: Azure OpenAI

```bash
# Azure OpenAI Configuration
AI_PROVIDER=azure
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_CHAT_DEPLOYMENT=your-gpt-deployment-name
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=your-embedding-deployment-name
```

### Configuration Notes

- **OpenAI**: Requires an OpenAI API key with access to GPT models and embeddings
- **Azure OpenAI**: Requires Azure OpenAI resource with deployed models
- **Model Requirements**: 
  - Chat model must support JSON mode (GPT-3.5-turbo-1106+ or GPT-4)
  - Embedding model should be text-embedding-3-large or equivalent
- **Deployment Names**: For Azure, use your actual deployment names, not model names

### Verifying Configuration

Check your AI provider configuration:

```bash
# Check health endpoint for provider status
curl http://localhost:8000/health

# Validate demo setup (includes AI provider check)
python validate_demo_setup.py --quick
```

The health endpoint will show your configured AI provider and its status.

## WSL Deployment

For Windows users, you can deploy and run the application in Windows Subsystem for Linux (WSL):

### Prerequisites for WSL
- Windows 10/11 with WSL2 enabled
- Ubuntu 20.04+ or similar Linux distribution in WSL
- **Docker options** (choose one):
  - Docker Engine installed directly in WSL2 (lightweight)
  - Docker Desktop for Windows with WSL2 integration (heavier but easier)

### WSL Setup and Deployment

1. **Open WSL terminal** (Ubuntu or your preferred distribution)

2. **Install required dependencies:**
   ```bash
   # Update package list
   sudo apt update

   # Install Node.js and npm
   curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
   sudo apt-get install -y nodejs

   # Install Python and pip
   sudo apt install python3 python3-pip

   # Install required Python packages
   pip3 install aiohttp psutil
   ```

3. **Clone and setup the project:**
   ```bash
   git clone <repository-url>
   cd ai-knowledge-mapper
   
   # Copy and configure environment
   cp .env.example .env
   # Edit .env with your OpenAI API key using nano or vim
   nano .env
   ```

4. **Deploy using the WSL script:**
   ```bash
   # Make the deployment script executable
   chmod +x deploy-wsl.sh
   
   # Run the deployment script
   ./deploy-wsl.sh
   ```

   Or manually with PowerShell from Windows:
   ```powershell
   # Run from Windows PowerShell (not WSL)
   .\deploy-wsl.ps1
   ```

5. **Verify deployment:**
   ```bash
   # Check if services are running
   docker-compose ps
   
   # Validate the setup
   python3 validate_demo_setup.py --quick
   ```

6. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - From Windows browser, you can also use: http://[WSL-IP]:3000

### WSL-Specific Notes

#### Docker Engine in WSL2 (Recommended for lightweight setup)
- **Installation**: Install Docker Engine directly in WSL2 using apt
- **Service Management**: Start Docker with `sudo service docker start`
- **Auto-start**: Add to `.bashrc` or `.zshrc` for automatic startup
- **Resource Usage**: Lower memory and CPU usage compared to Docker Desktop

#### Docker Desktop with WSL2 Integration
- **Integration**: Ensure Docker Desktop has WSL2 integration enabled for your distribution
- **GUI Management**: Provides graphical interface for container management
- **Resource Usage**: Higher memory usage but easier management

#### General WSL Notes
- **Port Forwarding**: WSL2 automatically forwards ports to Windows, so localhost should work from Windows browsers
- **File System**: Keep project files in the WSL file system (`/home/username/`) for better performance
- **Memory Limits**: WSL2 uses dynamic memory allocation, but you can configure limits in `.wslconfig` if needed

### Troubleshooting WSL Deployment

**Docker Issues:**
```bash
# For Docker Engine in WSL2
sudo service docker start
sudo service docker status

# For Docker Desktop
# Use Docker Desktop GUI or restart from Windows

# Check if Docker is working
docker --version
docker-compose --version
docker ps
```

**Port Access Issues:**
```bash
# Check which ports are in use
netstat -tulpn | grep :3000
netstat -tulpn | grep :8000

# Get WSL IP address
ip addr show eth0
```

**Permission Issues:**
```bash
# Fix Docker permissions
sudo usermod -aG docker $USER
# Log out and back in to WSL
```

**Performance Issues:**
```bash
# Monitor system resources
python3 performance_monitor.py --validate

# Check WSL resource usage
wsl --status
```

## Demo Preparation

For presentations and demonstrations, use the included demo utilities:

### Quick Demo Setup
```bash
# Validate system readiness
python validate_demo_setup.py

# Load demo scenario
python demo_seed_data.py --scenario ai_research

# Monitor performance
python performance_monitor.py --validate
```

### Available Demo Scenarios
- `ai_research` - AI research papers and concepts (5-7 min demo)
- `tech_companies` - Technology companies and relationships (4-6 min demo)  
- `climate_science` - Climate science and environmental data (6-8 min demo)

See [DEMO_SCENARIOS.md](DEMO_SCENARIOS.md) for detailed demo guides and presentation tips.

## Development

### Available Scripts

- `npm run dev` - Start all services with hot reloading
- `npm run dev:backend` - Start only backend and database services
- `npm run dev:frontend` - Start only frontend service
- `npm run build` - Build all Docker images
- `npm run down` - Stop all services
- `npm run clean` - Stop services and remove volumes
- `npm run logs` - View logs from all services

### Project Structure

```
├── client/                 # React TypeScript frontend
│   ├── src/               # Source code
│   ├── Dockerfile         # Frontend container
│   └── package.json       # Frontend dependencies
├── server/                # Python FastAPI backend
│   ├── main.py           # Application entry point
│   ├── requirements.txt  # Python dependencies
│   └── Dockerfile        # Backend container
├── docker-compose.yml    # Service orchestration
└── .env.example         # Environment template
```

## Architecture

- **Backend:** Python FastAPI with Qdrant (vector DB) and Oxigraph (RDF store)
- **Frontend:** React 18 + TypeScript + Vite + Tailwind CSS
- **Visualization:** react-force-graph-3d for 3D graph rendering
- **Real-time:** WebSocket communication for live updates
- **Containerization:** Docker Compose for development and deployment

## API Endpoints

- `GET /` - Health check
- `GET /health` - Detailed service status
- `POST /ingest` - Text ingestion and processing (coming soon)
- `GET /search` - Vector similarity search (coming soon)
- `GET /ask` - Question answering (coming soon)
- `WebSocket /stream` - Real-time updates (coming soon)

## License

MIT