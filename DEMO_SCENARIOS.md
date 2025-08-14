# AI Knowledge Mapper - Demo Scenarios

This document outlines the demo scenarios available for the AI Knowledge Mapper POC, designed to showcase different aspects of the system during presentations.

## Quick Start

1. **Start the system**: `docker-compose up -d`
2. **Load demo data**: `python demo_seed_data.py --scenario ai_research`
3. **Open browser**: Navigate to `http://localhost:3000`
4. **Begin demo**: Follow the scenario guide below

## Demo Scenarios

### 1. AI Research Papers (`ai_research`)

**Duration**: 5-7 minutes  
**Complexity**: Medium  
**Best for**: Technical audiences, AI researchers

**Narrative**: "Let's explore how recent AI breakthroughs are connected"

**Key Features Demonstrated**:
- Entity extraction from academic papers
- Cross-document relationship detection
- Technical concept mapping
- Citation-style evidence grounding

**Demo Flow**:
1. **Load Data** (30s): Load the AI research scenario
2. **Explore Graph** (2m): Show the knowledge graph with papers, models, and concepts
3. **Search Demo** (1m): Search for "Transformer" and show connections
4. **Node Details** (1m): Click on BERT node, show evidence quotes
5. **Q&A Demo** (2m): Ask "How are BERT and GPT related?" and show grounded answer
6. **Cross-Document** (1m): Highlight relationships between different papers

**Sample Questions**:
- "What is the Transformer architecture?"
- "How are BERT and GPT different?"
- "What are the key innovations in attention mechanisms?"

**Expected Graph Structure**:
- ~15-20 nodes (models, concepts, techniques)
- ~25-30 edges (relationships between concepts)
- Node types: Concept, Paper, Model, Technique
- Relationship types: based_on, uses, improves_upon, compares_with

---

### 2. Technology Companies (`tech_companies`)

**Duration**: 4-6 minutes  
**Complexity**: Low-Medium  
**Best for**: Business audiences, general tech interest

**Narrative**: "Understanding the AI landscape through company relationships"

**Key Features Demonstrated**:
- Business entity recognition
- Partnership and competition mapping
- Multi-document integration
- Conflict detection (competing claims)

**Demo Flow**:
1. **Load Data** (30s): Load the tech companies scenario
2. **Company Overview** (1.5m): Show major companies and their AI initiatives
3. **Partnership Focus** (1m): Highlight Microsoft-OpenAI partnership
4. **Competition View** (1m): Show competitive relationships
5. **Q&A Demo** (1.5m): Ask "Who are Microsoft's AI competitors?"
6. **Evidence Deep-dive** (1m): Show source quotes for key claims

**Sample Questions**:
- "What is Microsoft's relationship with OpenAI?"
- "Who are the major players in AI?"
- "How do Google and Microsoft compete in AI?"

**Expected Graph Structure**:
- ~12-15 nodes (companies, people, products)
- ~18-22 edges (partnerships, competition, leadership)
- Node types: Company, Person, Product, Technology
- Relationship types: partners_with, competes_with, develops, leads

---

### 3. Climate Science (`climate_science`)

**Duration**: 6-8 minutes  
**Complexity**: High  
**Best for**: Scientific audiences, policy discussions

**Narrative**: "Mapping climate science knowledge for better understanding"

**Key Features Demonstrated**:
- Scientific concept extraction
- Quantitative data handling
- Policy-science connections
- Evidence-based reasoning

**Demo Flow**:
1. **Load Data** (30s): Load the climate science scenario
2. **Scientific Concepts** (2m): Explore climate change mechanisms
3. **Solutions Focus** (1.5m): Navigate to renewable energy solutions
4. **Data Integration** (1m): Show how different reports connect
5. **Policy Questions** (2m): Ask about mitigation strategies
6. **Evidence Grounding** (1m): Show scientific source citations

**Sample Questions**:
- "What are the main causes of climate change?"
- "How effective are renewable energy solutions?"
- "What does the IPCC recommend for mitigation?"

**Expected Graph Structure**:
- ~18-25 nodes (concepts, technologies, organizations)
- ~30-40 edges (causal relationships, solutions)
- Node types: Concept, Technology, Organization, Report
- Relationship types: causes, mitigates, recommends, measures

## Demo Presentation Tips

### Pre-Demo Setup (5 minutes before)
1. **System Check**: Verify all services are running
2. **Data Loading**: Pre-load your chosen scenario
3. **Browser Setup**: Open in full-screen mode
4. **Performance**: Check that graph renders smoothly
5. **Backup Plan**: Have offline export ready if needed

### During Demo
1. **Start Simple**: Begin with graph overview, don't dive into details immediately
2. **Narrate Actions**: Explain what you're clicking and why
3. **Use Zoom**: Zoom in on specific areas for clarity
4. **Highlight Features**: Point out real-time updates, smooth animations
5. **Engage Audience**: Ask what they'd like to explore next

### Common Demo Flows

#### **Technical Deep-Dive** (10-12 minutes)
1. Load AI research scenario
2. Show graph structure and node types
3. Demonstrate search functionality
4. Explore node details and evidence
5. Show Q&A with citations
6. Discuss technical architecture
7. Performance monitoring (if enabled)

#### **Business Overview** (6-8 minutes)
1. Load tech companies scenario
2. High-level graph overview
3. Focus on key relationships
4. Quick Q&A demonstration
5. Discuss business applications
6. Export/import capabilities

#### **Quick Feature Demo** (3-5 minutes)
1. Use pre-loaded data
2. Graph navigation basics
3. Search one entity
4. Ask one question
5. Show evidence grounding
6. Highlight real-time updates

## Troubleshooting

### Common Issues

**Graph Not Loading**:
- Check backend health: `curl http://localhost:8000/health`
- Verify WebSocket connection in browser dev tools
- Try refreshing the page

**Slow Performance**:
- Enable performance monitor: `Ctrl+Shift+P`
- Check if too many nodes are displayed
- Consider using smaller dataset

**Demo Data Issues**:
- Verify scenario loaded: `python demo_seed_data.py --stats`
- Check backend logs: `docker-compose logs server`
- Try reloading scenario

**Network Issues**:
- Use offline mode: Import pre-exported graph data
- Check firewall settings
- Verify Docker networking

### Recovery Strategies

**If Live Demo Fails**:
1. Switch to offline mode with pre-exported data
2. Use static screenshots as backup
3. Focus on architecture discussion
4. Demo the code instead of running system

**If Questions Don't Work**:
1. Focus on search and navigation
2. Show node details and evidence
3. Discuss the underlying technology
4. Demonstrate graph exploration

## Performance Optimization

### For Smooth Demos
1. **Pre-load Data**: Load scenarios before presentation
2. **Close Unnecessary Apps**: Free up system resources
3. **Use Wired Connection**: Avoid WiFi if possible
4. **Test Beforehand**: Run through demo flow once
5. **Have Backup**: Export graph data as fallback

### System Requirements
- **RAM**: 8GB minimum, 16GB recommended
- **CPU**: Modern multi-core processor
- **Network**: Stable connection for live demo
- **Browser**: Chrome or Firefox, latest version
- **Display**: 1920x1080 minimum resolution

## Customization

### Creating New Scenarios
1. Add scenario to `DEMO_SCENARIOS` in `demo_seed_data.py`
2. Include 2-4 documents with rich, interconnected content
3. Test the scenario thoroughly
4. Document expected graph structure
5. Create demo flow guide

### Modifying Existing Scenarios
1. Edit document text in scenario definition
2. Reload the scenario: `python demo_seed_data.py --scenario <name>`
3. Verify graph structure matches expectations
4. Update demo flow if needed

## Advanced Features

### Performance Monitoring
- Enable with `Ctrl+Shift+P` during demo
- Shows FPS, memory usage, network latency
- Useful for technical audiences

### Graph Transitions
- Toggle with `Ctrl+Shift+T`
- Adds particle effects and animations
- Good for visual appeal, may impact performance

### Offline Mode
- Export graph: Click export button or use API
- Import graph: Use import button
- Useful for unreliable network conditions

### Developer Tools
- Open browser dev tools for WebSocket monitoring
- Check console for any errors
- Network tab shows API call performance

## Success Metrics

### Demo Success Indicators
- Graph loads within 10 seconds
- Search returns results in under 2 seconds
- Q&A responses generated in under 5 seconds
- Smooth animations and transitions
- No visible errors or crashes

### Audience Engagement
- Questions about technical implementation
- Interest in specific use cases
- Requests for follow-up demonstrations
- Discussion of potential applications

### Technical Validation
- All major features demonstrated
- Performance remains stable throughout
- Real-time updates work correctly
- Evidence grounding is clear and accurate