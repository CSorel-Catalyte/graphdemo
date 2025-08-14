# AI Knowledge Mapper

An interactive AI-powered knowledge graph system that converts arbitrary text into structured knowledge representations with 3D visualization.

## Features

- Real-time knowledge extraction from text using LLMs
- Entity canonicalization through vector similarity
- Interactive 3D graph visualization
- Question-answering with grounded citations
- WebSocket-based real-time updates

## Prerequisites

- Docker and Docker Compose
- OpenAI API key

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

## WSL Deployment

For Windows users, you can deploy and run the application in Windows Subsystem for Linux (WSL):

### Prerequisites for WSL
- Windows 10/11 with WSL2 enabled
- Ubuntu 20.04+ or similar Linux distribution in WSL
- Docker Desktop for Windows with WSL2 integration enabled

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

- **Docker Integration**: Ensure Docker Desktop has WSL2 integration enabled for your distribution
- **Port Forwarding**: WSL2 automatically forwards ports to Windows, so localhost should work from Windows browsers
- **File System**: Keep project files in the WSL file system (`/home/username/`) for better performance
- **Memory Limits**: WSL2 uses dynamic memory allocation, but you can configure limits in `.wslconfig` if needed

### Troubleshooting WSL Deployment

**Docker Issues:**
```bash
# Restart Docker service in WSL
sudo service docker start

# Check Docker status
sudo service docker status
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