"""Test Gemini AI integration for Luna."""

import asyncio
import os
from dotenv import load_dotenv

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("google-generativeai not installed. Install with: pip install google-generativeai")


async def test_gemini():
    """Test Gemini API connection."""
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not set in environment")
        return
    
    if not GEMINI_AVAILABLE:
        print("❌ google-generativeai package not available")
        return
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-pro")
        
        print("🔄 Testing Gemini API...")
        
        # Test prompt
        prompt = "You are Luna, a strict Discord bot. Respond professionally in under 50 words: What is your purpose?"
        
        response = await asyncio.to_thread(model.generate_content, prompt)
        
        print(f"✅ Gemini API Response:\n{response.text}")
        
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_gemini())
