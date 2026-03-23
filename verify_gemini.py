import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    print("❌ API_KEY not found in .env")
    exit(1)

# 1. List Models
list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
print(f"Fetching available models for this API key via {list_url[:65]}...")

response = requests.get(list_url)
data = response.json()

if "error" in data:
    print("Failed to list models:")
    print(data)
    exit(1)

models = data.get("models", [])
print(f"\nSuccessfully retrieved {len(models)} models.")

supported_models = []
print("\n--- Models Supporting generateContent ---")
for m in models:
    if "generateContent" in m.get("supportedGenerationMethods", []):
        name = m.get("name")
        supported_models.append(name)
        print(f" - {name}")

if not supported_models:
    print("NO models support generateContent for this API Key.")
    exit(1)

# 2. Test specific model (the first one)
test_model = supported_models[0]
print(f"\nTesting model: {test_model}")

test_url = f"https://generativelanguage.googleapis.com/v1beta/{test_model}:generateContent?key={API_KEY}"

payload = {
    "contents": [{"parts": [{"text": "Say hello!"}]}],
    "generationConfig": {"maxOutputTokens": 20}
}

test_res = requests.post(test_url, json=payload)
test_data = test_res.json()

if "error" in test_data:
    print("Generate Content FAILED")
    print(test_data)
else:
    print("Generate Content SUCCESS")
    print("Output:", test_data["candidates"][0]["content"]["parts"][0]["text"])

