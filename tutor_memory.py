
import os
from dotenv import load_dotenv
from google import genai

# Load your secure API key
load_dotenv()
client = genai.Client()

# Let's simulate a conversation where you mention a mistake
print("Simulating student conversation...")
user_message = "I always mess up the Spanish past tense endings for irregular verbs."

# We can ask the AI model to extract the core weakness and print it
response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents=f"Extract the specific grammar weakness from this sentence in 5 words or less: '{user_message}'",
)

print("\n--- Extracted Weakness for Memory ---")
print(response.text)