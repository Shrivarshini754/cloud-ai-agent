
import os
from dotenv import load_dotenv
from google import genai

# Load our secure .env file
load_dotenv()

# Initialize the Google GenAI client (it automatically looks for GOOGLE_API_KEY)
client = genai.Client()

# Ask the AI brain a test question in Spanish
print("Asking the AI brain a question...")
response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="Say hello in Spanish and tell me you are ready to be my language tutor.",
)

# Print out what the AI brain replies with
print("\n--- AI Brain Response ---")
print(response.text)