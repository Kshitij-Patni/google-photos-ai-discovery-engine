import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

for model in ['openai/gpt-oss-120b', 'qwen/qwen3.8-27b']:
    try:
        print(f"Testing {model}...")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Return {\"status\": \"ok\"}"}],
            response_format={"type": "json_object"}
        )
        print(f"Success with {model}: {response.choices[0].message.content}")
        break
    except Exception as e:
        print(f"Error with {model}: {e}")
