import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from src.analysis.metadata_enricher import build_batch_prompt, parse_llm_response, validate_metadata

# Load records
input_file = Path("data/processed/relevant/corpus_relevant.json")
with open(input_file, "r") as f:
    records = json.load(f)[:30] # Just take 30

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

print("Running validation on first 30 records...")
enriched = []

for i in range(0, min(len(records), 5), 5):
    batch = records[i:i + 5]
    prompt = build_batch_prompt(batch, "You are a structured data extraction assistant... (truncated for brevity)")
    
    import time
    success = False
    while not success:
        try:
            response = client.chat.completions.create(
                model="llama3.2",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a structured data extraction assistant. You always respond with valid JSON arrays only."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=4096,
                response_format={"type": "json_object"}
            )
            success = True
        except Exception as e:
            if "429" in str(e):
                print("Rate limited by main task. Waiting 30s...")
                time.sleep(30)
            else:
                raise e
    
    metadata_list = parse_llm_response(response.choices[0].message.content, len(batch))
    for j, record in enumerate(batch):
        if j < len(metadata_list):
            metadata = validate_metadata(metadata_list[j])
        else:
            metadata = {}
        record["metadata"] = metadata
        enriched.append(record)

# Save to temp file
with open("scratch/validation_sample.json", "w") as f:
    json.dump(enriched, f, indent=2)

print("Saved to scratch/validation_sample.json")
