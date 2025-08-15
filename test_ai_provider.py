#!/usr/bin/env python3
"""
Quick test script to debug AI provider configuration.
"""

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_ai_provider():
    print("🔍 Testing AI Provider Configuration")
    print("=" * 50)
    
    # Check environment variables
    print("\n📋 Environment Variables:")
    ai_provider = os.getenv("AI_PROVIDER", "not_set")
    print(f"   AI_PROVIDER: {ai_provider}")
    
    if ai_provider == "azure":
        print(f"   AZURE_OPENAI_API_KEY: {'✅ Set' if os.getenv('AZURE_OPENAI_API_KEY') else '❌ Not set'}")
        print(f"   AZURE_OPENAI_ENDPOINT: {os.getenv('AZURE_OPENAI_ENDPOINT', 'Not set')}")
        print(f"   AZURE_OPENAI_CHAT_DEPLOYMENT: {os.getenv('AZURE_OPENAI_CHAT_DEPLOYMENT', 'Not set')}")
        print(f"   AZURE_OPENAI_EMBEDDING_DEPLOYMENT: {os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT', 'Not set')}")
    else:
        print(f"   OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Not set'}")
    
    # Test AI provider initialization
    print("\n🚀 Testing AI Provider Initialization:")
    try:
        # Import the AI provider modules
        from server.services.ai_provider import AIProviderFactory, initialize_ai_provider
        
        # Get provider info
        provider_info = AIProviderFactory.get_provider_info()
        print(f"   Provider Info: {provider_info}")
        
        # Try to initialize
        ai_provider = initialize_ai_provider()
        print(f"   ✅ AI Provider initialized successfully: {type(ai_provider).__name__}")
        
        # Test a simple embedding call
        print("\n🧪 Testing Embedding Generation:")
        response = await ai_provider.create_embedding(
            input_text="test",
            encoding_format="float"
        )
        print(f"   ✅ Embedding test successful: {len(response.data[0].embedding)} dimensions")
        
    except Exception as e:
        print(f"   ❌ AI Provider initialization failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ai_provider())