#!/usr/bin/env python3
"""Quick test script for AI functionality."""

import sys
import os
sys.path.insert(0, '/home/engine/project')

from vertigo.helpers import get_ai_response, get_personality_prompt, truncate_response

def test_config():
    """Test configuration values."""
    from vertigo.config import AI_PERSONALITIES, HUGGINGFACE_TOKEN, MAX_RESPONSE_LENGTH
    
    print("=== Configuration Test ===")
    print(f"AI personalities: {list(AI_PERSONALITIES.keys())}")
    print(f"HuggingFace token configured: {bool(HUGGINGFACE_TOKEN)}")
    print(f"Max response length: {MAX_RESPONSE_LENGTH}")
    print()

def test_personality_prompts():
    """Test personality prompt generation."""
    print("=== Personality Prompts Test ===")
    for personality in ["genz", "professional", "funny"]:
        prompt = get_personality_prompt(personality)
        print(f"Personality: {personality}")
        print(f"Prompt length: {len(prompt)} chars")
        print(f"First 100 chars: {prompt[:100]}...")
        print()

def test_truncation():
    """Test response truncation."""
    print("=== Response Truncation Test ===")
    
    long_text = "This is a very long response that should definitely be truncated because it exceeds the Discord character limit of 200 characters and needs to be cut off at a reasonable point."
    short_text = "Short response"
    
    truncated_long = truncate_response(long_text)
    truncated_short = truncate_response(short_text)
    
    print(f"Original long text ({len(long_text)} chars): {long_text}")
    print(f"Truncated long text ({len(truncated_long)} chars): {truncated_long}")
    print()
    print(f"Original short text ({len(short_text)} chars): {short_text}")
    print(f"Truncated short text ({len(truncated_short)} chars): {truncated_short}")
    print()

async def test_ai_response():
    """Test AI response generation (requires valid HuggingFace token)."""
    from vertigo.config import HUGGINGFACE_TOKEN
    
    print("=== AI Response Test ===")
    
    if not HUGGINGFACE_TOKEN:
        print("⚠️  HUGGINGFACE_TOKEN not configured. Skipping AI test.")
        print("To test AI functionality:")
        print("1. Sign up at https://huggingface.co/")
        print("2. Get an API token")
        print("3. Add HUGGINGFACE_TOKEN to your .env file")
        return
    
    try:
        print("Testing AI response generation...")
        response = await get_ai_response("What's your favorite food?", "genz")
        print(f"AI Response: {response}")
        print(f"Response length: {len(response)} chars")
        print("✅ AI test successful!")
    except Exception as e:
        print(f"❌ AI test failed: {e}")
    print()

def main():
    """Run all tests."""
    print("🤖 Vertigo AI Chatbot - Test Suite")
    print("=" * 50)
    
    test_config()
    test_personality_prompts()
    test_truncation()
    
    # Test AI response (async)
    import asyncio
    asyncio.run(test_ai_response())
    
    print("🎉 All tests completed!")

if __name__ == "__main__":
    main()