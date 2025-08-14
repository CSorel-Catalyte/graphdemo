#!/usr/bin/env python3
"""
Demo seed data loading script for AI Knowledge Mapper POC.
Provides pre-prepared demo scenarios with realistic knowledge graph data.
"""

import json
import asyncio
import aiohttp
import time
from typing import List, Dict, Any
from pathlib import Path

# Demo scenarios with different complexity levels
DEMO_SCENARIOS = {
    "ai_research": {
        "name": "AI Research Papers",
        "description": "Knowledge graph from recent AI research papers",
        "documents": [
            {
                "doc_id": "transformer_paper",
                "title": "Attention Is All You Need",
                "text": """
                The Transformer model architecture relies entirely on attention mechanisms to draw global dependencies between input and output. 
                The model uses multi-head self-attention to allow the model to jointly attend to information from different representation 
                subspaces at different positions. The encoder-decoder structure consists of stacked self-attention and point-wise, 
                fully connected layers. BERT and GPT models are based on the Transformer architecture. The attention mechanism computes 
                a weighted sum of values, where the weight assigned to each value is computed by a compatibility function of the query 
                with the corresponding key. Scaled dot-product attention is used as the attention function. The model achieves 
                state-of-the-art results on machine translation tasks while being more parallelizable and requiring significantly 
                less time to train than recurrent neural networks.
                """
            },
            {
                "doc_id": "bert_paper", 
                "title": "BERT: Pre-training of Deep Bidirectional Transformers",
                "text": """
                BERT (Bidirectional Encoder Representations from Transformers) is designed to pre-train deep bidirectional 
                representations from unlabeled text by jointly conditioning on both left and right context in all layers. 
                The pre-trained BERT model can be fine-tuned with just one additional output layer to create state-of-the-art 
                models for a wide range of tasks, such as question answering and language inference. BERT uses the Transformer 
                encoder architecture and is trained on masked language modeling and next sentence prediction tasks. 
                The bidirectional training allows BERT to understand context better than previous unidirectional models like GPT. 
                BERT achieves significant improvements on eleven natural language processing tasks including GLUE benchmark.
                """
            },
            {
                "doc_id": "gpt_paper",
                "title": "Language Models are Unsupervised Multitask Learners", 
                "text": """
                GPT-2 demonstrates that language models begin to learn various tasks without explicit supervision when trained 
                on a large and diverse dataset. The model uses a Transformer decoder architecture and is trained using 
                unsupervised pre-training on a large corpus of text. GPT-2 shows that scaling up language models improves 
                performance across many domains. The model can perform reading comprehension, machine translation, question 
                answering, and summarization without task-specific training. Zero-shot task transfer is achieved through 
                the language modeling objective. GPT-2 uses byte-pair encoding for tokenization and demonstrates emergent 
                capabilities as model size increases. The largest GPT-2 model has 1.5 billion parameters.
                """
            }
        ]
    },
    
    "tech_companies": {
        "name": "Technology Companies",
        "description": "Knowledge graph about major technology companies and their relationships",
        "documents": [
            {
                "doc_id": "openai_info",
                "title": "OpenAI Company Overview",
                "text": """
                OpenAI is an artificial intelligence research laboratory consisting of the for-profit corporation OpenAI LP 
                and its parent company, the non-profit OpenAI Inc. The company was founded in 2015 by Sam Altman, Elon Musk, 
                Greg Brockman, Ilya Sutskever, and others. OpenAI's mission is to ensure that artificial general intelligence 
                benefits all of humanity. The company has developed several notable AI models including GPT-3, GPT-4, DALL-E, 
                and ChatGPT. Microsoft has invested billions of dollars in OpenAI and has an exclusive license to GPT-3. 
                OpenAI transitioned from a non-profit to a capped-profit model in 2019. The company focuses on AI safety 
                and alignment research while developing commercially viable AI products.
                """
            },
            {
                "doc_id": "microsoft_ai",
                "title": "Microsoft AI Initiatives", 
                "text": """
                Microsoft has made significant investments in artificial intelligence, including a multi-billion dollar 
                partnership with OpenAI. The company integrates AI capabilities across its product portfolio including 
                Azure AI services, Office 365 Copilot, and Bing Chat. Satya Nadella, Microsoft's CEO, has positioned 
                AI as central to the company's future strategy. Microsoft Azure provides cloud computing services that 
                power many AI applications. The company competes with Google, Amazon, and other tech giants in the AI space. 
                Microsoft's AI research division works on machine learning, computer vision, and natural language processing. 
                The partnership with OpenAI gives Microsoft exclusive access to GPT models for commercial use.
                """
            },
            {
                "doc_id": "google_ai",
                "title": "Google AI and DeepMind",
                "text": """
                Google has been a leader in artificial intelligence research through its Google AI division and DeepMind 
                subsidiary. DeepMind, acquired by Google in 2014, developed AlphaGo which defeated world champion Go players. 
                Google's AI research includes work on neural networks, machine learning, and large language models like LaMDA 
                and PaLM. Sundar Pichai, Google's CEO, has emphasized AI-first approach across Google's products. 
                Google Search, Gmail, Google Photos, and other services incorporate AI capabilities. The company developed 
                the Transformer architecture which became foundational for modern language models. Google competes with 
                Microsoft, OpenAI, and other companies in the generative AI space with products like Bard.
                """
            }
        ]
    },
    
    "climate_science": {
        "name": "Climate Science",
        "description": "Knowledge graph about climate change research and environmental science",
        "documents": [
            {
                "doc_id": "ipcc_report",
                "title": "IPCC Climate Change Assessment",
                "text": """
                The Intergovernmental Panel on Climate Change (IPCC) provides comprehensive assessments of climate change 
                science. The IPCC reports show that human activities are the primary driver of climate change since the 
                mid-20th century. Greenhouse gas emissions from fossil fuel combustion, deforestation, and industrial 
                processes are increasing atmospheric CO2 concentrations. Global average temperatures have risen by 
                approximately 1.1°C since pre-industrial times. Climate impacts include rising sea levels, changing 
                precipitation patterns, more frequent extreme weather events, and ecosystem disruption. The Paris Agreement 
                aims to limit global warming to well below 2°C above pre-industrial levels. Mitigation strategies include 
                renewable energy deployment, energy efficiency improvements, and carbon capture technologies.
                """
            },
            {
                "doc_id": "renewable_energy",
                "title": "Renewable Energy Technologies",
                "text": """
                Renewable energy sources including solar, wind, hydroelectric, and geothermal power are essential for 
                reducing greenhouse gas emissions. Solar photovoltaic technology has experienced dramatic cost reductions 
                making it competitive with fossil fuels in many markets. Wind power capacity has grown rapidly worldwide 
                with both onshore and offshore installations. Energy storage technologies like lithium-ion batteries 
                are crucial for integrating variable renewable sources into the grid. The International Energy Agency 
                projects that renewable energy will dominate electricity generation by 2050. Government policies including 
                renewable energy standards and carbon pricing support clean energy deployment. Tesla, First Solar, 
                and Vestas are leading companies in the renewable energy sector.
                """
            }
        ]
    }
}

class DemoDataLoader:
    """Loads demo scenarios into the AI Knowledge Mapper system."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def check_health(self) -> bool:
        """Check if the backend is healthy and ready."""
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                return response.status == 200
        except Exception as e:
            print(f"Health check failed: {e}")
            return False
    
    async def ingest_document(self, doc_id: str, text: str) -> bool:
        """Ingest a single document into the system."""
        try:
            payload = {
                "doc_id": doc_id,
                "text": text
            }
            
            async with self.session.post(
                f"{self.base_url}/ingest",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300)  # 5 minute timeout
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✓ Ingested document '{doc_id}' - {result.get('chunks_processed', 0)} chunks processed")
                    return True
                else:
                    error_text = await response.text()
                    print(f"✗ Failed to ingest document '{doc_id}': {response.status} - {error_text}")
                    return False
                    
        except asyncio.TimeoutError:
            print(f"✗ Timeout ingesting document '{doc_id}'")
            return False
        except Exception as e:
            print(f"✗ Error ingesting document '{doc_id}': {e}")
            return False
    
    async def load_scenario(self, scenario_name: str) -> Dict[str, Any]:
        """Load a complete demo scenario."""
        if scenario_name not in DEMO_SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario_name}")
        
        scenario = DEMO_SCENARIOS[scenario_name]
        print(f"\n🚀 Loading demo scenario: {scenario['name']}")
        print(f"📝 Description: {scenario['description']}")
        print(f"📄 Documents to process: {len(scenario['documents'])}")
        
        # Check backend health
        if not await self.check_health():
            raise RuntimeError("Backend is not healthy - cannot load demo data")
        
        results = {
            "scenario_name": scenario_name,
            "total_documents": len(scenario['documents']),
            "successful_ingestions": 0,
            "failed_ingestions": 0,
            "processing_time": 0,
            "documents": []
        }
        
        start_time = time.time()
        
        # Process each document
        for doc in scenario['documents']:
            print(f"\n📖 Processing: {doc.get('title', doc['doc_id'])}")
            success = await self.ingest_document(doc['doc_id'], doc['text'])
            
            doc_result = {
                "doc_id": doc['doc_id'],
                "title": doc.get('title', ''),
                "success": success,
                "text_length": len(doc['text'])
            }
            results['documents'].append(doc_result)
            
            if success:
                results['successful_ingestions'] += 1
            else:
                results['failed_ingestions'] += 1
            
            # Small delay between documents to avoid overwhelming the system
            await asyncio.sleep(2)
        
        results['processing_time'] = time.time() - start_time
        
        print(f"\n✅ Scenario loading complete!")
        print(f"📊 Results: {results['successful_ingestions']}/{results['total_documents']} documents processed successfully")
        print(f"⏱️  Total time: {results['processing_time']:.1f} seconds")
        
        return results
    
    async def get_graph_stats(self) -> Dict[str, Any]:
        """Get current graph statistics."""
        try:
            async with self.session.get(f"{self.base_url}/graph/export") as response:
                if response.status == 200:
                    graph_data = await response.json()
                    return {
                        "nodes": len(graph_data.get('nodes', [])),
                        "edges": len(graph_data.get('edges', [])),
                        "node_types": {},
                        "edge_types": {}
                    }
                else:
                    return {"error": f"Failed to get graph stats: {response.status}"}
        except Exception as e:
            return {"error": f"Error getting graph stats: {e}"}

def list_scenarios():
    """List available demo scenarios."""
    print("\n📋 Available Demo Scenarios:")
    print("=" * 50)
    
    for key, scenario in DEMO_SCENARIOS.items():
        print(f"\n🎯 {key}")
        print(f"   Name: {scenario['name']}")
        print(f"   Description: {scenario['description']}")
        print(f"   Documents: {len(scenario['documents'])}")

async def main():
    """Main demo data loading function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Load demo data into AI Knowledge Mapper")
    parser.add_argument("--scenario", "-s", help="Scenario to load", choices=list(DEMO_SCENARIOS.keys()))
    parser.add_argument("--list", "-l", action="store_true", help="List available scenarios")
    parser.add_argument("--url", "-u", default="http://localhost:8000", help="Backend URL")
    parser.add_argument("--stats", action="store_true", help="Show current graph statistics")
    
    args = parser.parse_args()
    
    if args.list:
        list_scenarios()
        return
    
    async with DemoDataLoader(args.url) as loader:
        if args.stats:
            stats = await loader.get_graph_stats()
            print(f"\n📊 Current Graph Statistics:")
            print(f"   Nodes: {stats.get('nodes', 'N/A')}")
            print(f"   Edges: {stats.get('edges', 'N/A')}")
            if 'error' in stats:
                print(f"   Error: {stats['error']}")
            return
        
        if args.scenario:
            try:
                results = await loader.load_scenario(args.scenario)
                
                # Save results to file
                results_file = Path(f"demo_results_{args.scenario}_{int(time.time())}.json")
                with open(results_file, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"\n💾 Results saved to: {results_file}")
                
            except Exception as e:
                print(f"\n❌ Error loading scenario: {e}")
                return
        else:
            print("Please specify a scenario to load or use --list to see available scenarios")
            list_scenarios()

if __name__ == "__main__":
    asyncio.run(main())