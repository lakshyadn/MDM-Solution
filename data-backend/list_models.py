import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not set")

genai.configure(api_key=api_key)

print("Available Gemini models:\n")
for model in genai.list_models():
    methods = model.supported_generation_methods
    if 'generateContent' in methods or 'embedContent' in methods:
        print(f"Model: {model.name}")
        print(f"  Display Name: {model.display_name}")
        print(f"  Supported methods: {methods}")
        if 'embedContent' in methods:
            print("  -> Supports embeddings")
        print()
