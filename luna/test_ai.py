"""
Test script for Gemini AI integration
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# Test API key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ ERROR: GEMINI_API_KEY not found in environment variables!")
    exit(1)

print(f"🔑 API Key found: {api_key[:10]}...{api_key[-10:]}")

# Configure
try:
    genai.configure(api_key=api_key)
    print("✅ Gemini API configured")
except Exception as e:
    print(f"❌ Error configuring API: {e}")
    exit(1)

# Test model
try:
    model = genai.GenerativeModel('gemini-pro')
    print("✅ Gemini Pro model initialized")
except Exception as e:
    print(f"❌ Error initializing model: {e}")
    exit(1)

# Test prompts
test_prompts = [
    ("helpful", "What is 2+2?"),
    ("sarcastic", "Tell me a joke"),
    ("genz", "What's up?"),
    ("professional", "Explain Python briefly"),
]

system_prompts = {
    "helpful": "You are Luna, a helpful and friendly AI assistant. Be concise and direct.",
    "sarcastic": "You are Luna, a witty and sarcastic AI. Use humor and light roasting.",
    "genz": "You are Luna, a Gen-Z AI. Use slang casually and be chill.",
    "professional": "You are Luna, a professional AI assistant. Be formal and precise.",
}

print("\n" + "="*60)
print("Testing AI Responses")
print("="*60 + "\n")

for personality, prompt in test_prompts:
    print(f"Testing '{personality}' personality...")
    print(f"Prompt: {prompt}")
    
    try:
        full_prompt = f"{system_prompts[personality]}\n\n{prompt}"
        response = model.generate_content(full_prompt)
        
        if response and hasattr(response, 'text'):
            print(f"✅ Response: {response.text[:100]}...")
        else:
            print(f"⚠️  No response text received")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()

print("="*60)
print("Test Complete")
print("="*60)
