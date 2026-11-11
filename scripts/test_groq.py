
import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

# Load project environment variables
BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

api_key = os.getenv("GROQ_API_KEY")
model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

if not api_key:
    raise ValueError("GROQ_API_KEY is missing from .env")

client = Groq(api_key=api_key)

response = client.chat.completions.create(
    model=model,
    messages=[
        {
            "role": "user",
            "content": "You are Nexora HR Intelligence Agent. Reply with: Nexora AI connection successful."
        }
    ],
    max_tokens=512
)

print("Groq connection successful!")
print("Model:", model)
print("Finish reason:", response.choices[0].finish_reason)
print("Response:", repr(response.choices[0].message.content))
