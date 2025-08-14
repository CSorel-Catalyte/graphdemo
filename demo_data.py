"""
Demo seed data and preparation script
Creates sample data for demonstration purposes
"""

import json
import requests
import time
from typing import Dict, List

class DemoDataManager:
    """Manages demo data creation and loading"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.demo_documents = self.get_demo_documents()
        
    def get_demo_documents(self) -> List[Dict[str, str]]:
        """Get sample documents for demo"""
        return [
            {
                "doc_id": "ai_overview",
                "title": "AI Overview",
                "text": """
                Artificial Intelligence (AI) is a broad field of computer science focused on creating 
                intelligent machines that can perform tasks typically requiring human intelligence. 
                Machine Learning (ML) is a subset of AI that enables computers to learn and improve 
                from experience without being explicitly programmed. Deep Learning is a specialized 
                area of ML that uses neural networks with multiple layers to model and understand 
                complex patterns in data. Natural Language Processing (NLP) is another AI subfield 
                that focuses on the interaction between computers and human language, enabling 
                machines to understand, interpret, and generate human text.
                """
            },
            {
                "doc_id": "ml_techniques",
                "title": "Machine Learning Techniques", 
                "text": """
                Machine Learning encompasses various techniques including supervised learning, 
                unsupervised learning, and reinforcement learning. Supervised learning uses 
                labeled training data to learn a mapping from inputs to outputs. Popular 
                supervised learning algorithms include Linear Regression, Decision Trees, 
                Random Forest, and Support Vector Machines (SVM). Unsupervised learning 
                finds hidden patterns in data without labeled examples, using techniques 
                like K-Means clustering and Principal Component Analysis (PCA). Reinforcement 
                learning involves agents learning to make decisions through trial and error 
                in an environment to maximize cumulative reward.
                """
            },
            {
                "doc_id": "neural_networks",
                "title": "Neural Networks and Deep Learning",
                "text": """
                Neural Networks are computing systems inspired by biological neural networks. 
                A basic neural network consists of interconnected nodes (neurons) organized 
                in layers: input layer, hidden layers, and output layer. Deep Learning uses 
                neural networks with many hidden layers (typically 3 or more) to learn 
                complex representations. Convolutional Neural Networks (CNNs) are specialized 
                for processing grid-like data such as images, using convolutional layers 
                that apply filters to detect features. Recurrent Neural Networks (RNNs) 
                are designed for sequential data, with connections that create loops allowing 
                information to persist. Long Short-Term Memory (LSTM) networks are a type 
                of RNN that can learn long-term dependencies.
                """
            },
            {
                "doc_id": "nlp_applications",
                "title": "NLP Applications and Techniques",
                "text": """
                Natural Language Processing has numerous applications including machine 
                translation, sentiment analysis, text summarization, and question answering. 
                Transformer models have revolutionized NLP, with architectures like BERT 
                (Bidirectional Encoder Representations from Transformers) and GPT (Generative 
                Pre-trained Transformer) achieving state-of-the-art results. BERT uses 
                bidirectional training to understand context from both directions, making 
                it excellent for understanding tasks. GPT models are autoregressive and 
                excel at text generation. Large Language Models (LLMs) like GPT-3 and GPT-4 
                demonstrate emergent capabilities in few-shot learning and reasoning. 
                Attention mechanisms allow models to focus on relevant parts of the input 
                when making predictions.
                """
            },
            {
                "doc_id": "ai_ethics",
                "title": "AI Ethics and Challenges",
                "text": """
                As AI systems become more powerful and widespread, ethical considerations 
                become increasingly important. Bias in AI systems can perpetuate or amplify 
                existing societal inequalities, particularly affecting marginalized groups. 
                Algorithmic fairness seeks to ensure AI systems make decisions that are 
                equitable across different demographic groups. Explainable AI (XAI) focuses 
                on making AI decision-making processes transparent and interpretable to humans. 
                Privacy concerns arise from AI systems' ability to infer sensitive information 
                from seemingly innocuous data. The alignment problem in AI safety refers to 
                ensuring AI systems pursue intended goals without harmful side effects. 
                Responsible AI development requires considering these ethical implications 
                throughout the design and deployment process.
                """
            }
        ]
    
    def check_service_health(self) -> bool:
        """Check if the service is running and healthy"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Service health check failed: {e}")
            return False
    
    def ingest_document(self, doc: Dict[str, str]) -> bool:
        """Ingest a single document"""
        try:
            print(f"Ingesting: {doc['title']}")
            response = requests.post(
                f"{self.base_url}/ingest",
                json={"doc_id": doc["doc_id"], "text": doc["text"]},
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ Success: {result.get('chunks_processed', 0)} chunks processed")
                return True
            else:
                print(f"  ❌ Failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"  ❌ Error ingesting {doc['title']}: {e}")
            return False
    
    def load_demo_data(self) -> bool:
        """Load all demo documents"""
        print("🚀 Loading demo data...")
        
        if not self.check_service_health():
            print("❌ Service is not healthy. Please start the application first.")
            return False
        
        success_count = 0
        total_count = len(self.demo_documents)
        
        for doc in self.demo_documents:
            if self.ingest_document(doc):
                success_count += 1
            time.sleep(2)  # Brief pause between ingestions
        
        print(f"\n📊 Demo data loading complete: {success_count}/{total_count} documents loaded")
        
        if success_count == total_count:
            print("🎉 All demo data loaded successfully!")
            return True
        else:
            print("⚠️  Some documents failed to load. Check the logs above.")
            return False
    
    def verify_demo_data(self) -> bool:
        """Verify demo data was loaded correctly"""
        print("\n🔍 Verifying demo data...")
        
        # Test search functionality
        search_terms = ["artificial intelligence", "machine learning", "neural networks"]
        
        for term in search_terms:
            try:
                response = requests.get(f"{self.base_url}/search?q={term}", timeout=10)
                if response.status_code == 200:
                    results = response.json()
                    print(f"  ✅ Search '{term}': {len(results)} results")
                else:
                    print(f"  ❌ Search '{term}' failed: {response.status_code}")
                    return False
            except Exception as e:
                print(f"  ❌ Search '{term}' error: {e}")
                return False
        
        # Test question answering
        test_questions = [
            "What is machine learning?",
            "How do neural networks work?",
            "What are the applications of NLP?"
        ]
        
        for question in test_questions:
            try:
                response = requests.get(f"{self.base_url}/ask?q={question}", timeout=30)
                if response.status_code == 200:
                    result = response.json()
                    print(f"  ✅ Q&A '{question[:30]}...': Answer generated")
                else:
                    print(f"  ❌ Q&A '{question[:30]}...' failed: {response.status_code}")
            except Exception as e:
                print(f"  ❌ Q&A '{question[:30]}...' error: {e}")
        
        # Test graph export
        try:
            response = requests.get(f"{self.base_url}/graph/export", timeout=10)
            if response.status_code == 200:
                graph_data = response.json()
                node_count = len(graph_data.get("nodes", []))
                edge_count = len(graph_data.get("edges", []))
                print(f"  ✅ Graph export: {node_count} nodes, {edge_count} edges")
            else:
                print(f"  ❌ Graph export failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"  ❌ Graph export error: {e}")
            return False
        
        print("✅ Demo data verification complete!")
        return True
    
    def create_demo_script(self) -> str:
        """Create a demo script with suggested interactions"""
        script = """
# AI Knowledge Mapper Demo Script

## Demo Flow (15 minutes)

### 1. Introduction (2 minutes)
- Show the application running at http://localhost:3000
- Explain the concept: "Transform text into interactive knowledge graphs"
- Show the 3D visualization with existing demo data

### 2. Text Ingestion Demo (3 minutes)
- Use the ingest endpoint to add new content
- Show real-time graph updates via WebSocket
- Demonstrate entity extraction and relationship discovery

**Sample text to ingest:**
```
Transformer architecture revolutionized natural language processing through the attention mechanism. 
BERT and GPT are both based on transformers but serve different purposes. BERT excels at understanding 
tasks while GPT specializes in text generation. The attention mechanism allows models to focus on 
relevant parts of the input sequence when making predictions.
```

### 3. Interactive Exploration (4 minutes)
- Click on nodes to see detailed information
- Show evidence quotes and source references
- Demonstrate 1-hop neighborhood expansion
- Highlight cross-document entity merging

**Key nodes to explore:**
- "Machine Learning" - shows connections to AI and Deep Learning
- "Neural Networks" - demonstrates technical relationships
- "BERT" - shows transformer connections

### 4. Search Functionality (2 minutes)
- Search for "deep learning"
- Show how search centers and highlights nodes
- Demonstrate vector similarity matching

### 5. Question Answering (3 minutes)
- Ask: "What is the relationship between AI and machine learning?"
- Show grounded answers with citations
- Click citations to navigate to source nodes
- Ask: "How do transformers work in NLP?"

### 6. Advanced Features (1 minute)
- Show graph export functionality
- Demonstrate offline mode capability
- Highlight multi-document conflict detection

## Demo Tips

### Preparation Checklist:
- [ ] Application running and healthy
- [ ] Demo data loaded successfully
- [ ] All endpoints responding quickly
- [ ] WebSocket connections working
- [ ] Browser zoom set appropriately

### Talking Points:
- "Real-time knowledge extraction from unstructured text"
- "Vector similarity for entity canonicalization"
- "Grounded AI with transparent citations"
- "Interactive 3D visualization for intuitive exploration"
- "Cross-document relationship discovery"

### Backup Plans:
- If live ingestion fails: Use pre-loaded demo data
- If WebSocket fails: Refresh page to reconnect
- If search is slow: Use smaller queries
- If Q&A fails: Show existing graph exploration

### Common Questions & Answers:
Q: "How accurate is the entity extraction?"
A: "Uses state-of-the-art LLMs with structured output validation"

Q: "Can it handle different document types?"
A: "Currently optimized for text, extensible to PDFs and web content"

Q: "How does it scale?"
A: "Vector databases and graph stores provide efficient scaling"

Q: "What about data privacy?"
A: "Configurable for local deployment, no data leaves your environment"
        """
        
        return script.strip()
    
    def save_demo_script(self, filename: str = "DEMO_SCRIPT.md"):
        """Save the demo script to a file"""
        script = self.create_demo_script()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(script)
        print(f"📝 Demo script saved to {filename}")

def main():
    """Main demo preparation function"""
    print("🎬 AI Knowledge Mapper Demo Preparation")
    print("=" * 50)
    
    manager = DemoDataManager()
    
    # Load demo data
    if manager.load_demo_data():
        # Verify data loaded correctly
        manager.verify_demo_data()
        
        # Create demo script
        manager.save_demo_script()
        
        print("\n🎉 Demo preparation complete!")
        print("\nNext steps:")
        print("1. Review DEMO_SCRIPT.md for presentation flow")
        print("2. Open http://localhost:3000 in your browser")
        print("3. Test the key demo scenarios")
        print("4. You're ready to present!")
        
    else:
        print("\n❌ Demo preparation failed!")
        print("Please check the application logs and try again.")

if __name__ == "__main__":
    main()