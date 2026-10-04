import os
import json
import time
from typing import Dict, Any, Optional
from google import genai
from google.genai import types

class GeminiClient:
    def __init__(self, model_name: str = "gemini-flash-lite-latest", temperature: float = 0.1):
        # We'll use gemini-flash-lite-latest as the default for classification.
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set.")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name
        self.temperature = temperature

    def generate_json(self, prompt: str, schema: Optional[Dict[str, Any]] = None, max_retries: int = 5) -> Optional[Dict[str, Any]]:
        """Generates a JSON response from Gemini with retry logic."""
        config_kwargs = {
            "temperature": self.temperature,
            "response_mime_type": "application/json",
        }
        if schema:
            config_kwargs["response_schema"] = schema
            
        config = types.GenerateContentConfig(**config_kwargs)

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config
                )
                
                try:
                    return json.loads(response.text)
                except json.JSONDecodeError:
                    backoff = 2 ** attempt
                    print(f"Attempt {attempt + 1}: Failed to parse JSON response. Retrying in {backoff}s...")
                    time.sleep(backoff)
            except Exception as e:
                backoff = 2 ** attempt
                print(f"Attempt {attempt + 1}: Error calling Gemini API: {e}. Retrying in {backoff}s...")
                time.sleep(backoff)
                
        print(f"Failed to generate valid JSON after {max_retries} attempts.")
        return None

if __name__ == "__main__":
    # Simple test
    import dotenv
    dotenv.load_dotenv()
    client = GeminiClient()
    response = client.generate_json("Output a JSON object with a key 'test' and value 'success'.")
    print("Test Response:", response)
