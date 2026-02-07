#!/usr/bin/env python3
"""Test OpenAI/DeepSeek API with provided key."""

import os
import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


async def test_openai_api():
    """Test OpenAI/DeepSeek API connection."""
    print("=== OpenAI/DeepSeek API Test ===\n")
    
    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("[X] ERROR: OPENAI_API_KEY environment variable not set")
        print("    Set it with: export OPENAI_API_KEY=your-key")
        return False
    
    try:
        from src.langchain_integration import LLMManager
        
        print("1. Loading configuration...")
        llm_manager = LLMManager()
        
        info = llm_manager.get_model_info()
        print(f"   Provider: {info['provider']}")
        print(f"   Model: {info['model']}")
        print(f"   Base URL: {info.get('base_url', 'default')}")
        print()
        
        print("2. Testing API connection...")
        llm = llm_manager.get_llm()
        
        from langchain_core.messages import HumanMessage
        
        print("   Sending test message...")
        response = await llm.ainvoke([HumanMessage(content="Say hello in 5 words or less.")])
        
        print(f"   [OK] API responded successfully!")
        print(f"   Response: {response.content}")
        print()
        
        print("=" * 50)
        print("SUCCESS: OpenAI/DeepSeek API test passed!")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"\n[X] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False



if __name__ == "__main__":
    success = asyncio.run(test_openai_api())
    sys.exit(0 if success else 1)
