import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables from .env
load_dotenv()

# Get API key from environment
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not set in environment or .env file.")

genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-3-flash-preview")
response = model.generate_content("How does AI work?")

print(response.text)


 