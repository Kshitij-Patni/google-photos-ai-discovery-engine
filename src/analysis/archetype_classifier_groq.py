"""
Phase 4.2: Archetype Classification with Groq API (Fallback)

Uses multiple Groq API keys to bypass rate limits and classify 
remaining records using Llama 3.3.
"""

import json
import os
import sys
import re
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from tqdm.asyncio import tqdm

from groq import AsyncGroq

# --- Configuration ---
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENRICHED_DIR = BASE_DIR / "data/enriched"
INPUT_FILE = ENRICHED_DIR / "corpus_enriched.json"
OUTPUT_FILE = ENRICHED_DIR / "corpus_classified.json"
CHECKPOINT_FILE = ENRICHED_DIR / "corpus_classified_checkpoint.json"
REPORT_FILE = BASE_DIR / "reports/archetype_distribution.json"

MODEL = "openai/gpt-oss-120b"
BATCH_SIZE = 15  # Smaller batch for Groq token limits
RATE_LIMIT_DELAY = 1.0  # Wait a bit between calls
CONCURRENCY_LIMIT = 4

VALID_ARCHETYPES = {
    "TEMPORAL_DECAY", "SPATIAL_AMBIGUITY", "KEYWORD_MISMATCH", 
    "CONTEXT_WITHOUT_CONTENT", "PEOPLE_WITHOUT_NAMES", 
    "VISUAL_MEMORY_ONLY", "ALBUM_FRAGMENTATION", "VOLUME_OVERWHELM"
}

def get_default_archetypes():
    return {
        "archetypes": [],
        "reasoning": "Failed to classify or insufficient context."
    }

def load_checkpoint():
    if not CHECKPOINT_FILE.exists():
        return {}, []
    try:
        with open(CHECKPOINT_FILE, "r") as f:
            checkpointed = json.load(f)
        id_set = {r["id"] for r in checkpointed if "id" in r}
        print(f"  Loaded checkpoint: {len(checkpointed)} valid records already classified.")
        return id_set, checkpointed
    except (json.JSONDecodeError, KeyError):
        return {}, []

def save_checkpoint(records):
    ENRICHED_DIR.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(records, f, indent=2)

def load_enriched_records():
    with open(INPUT_FILE, "r") as f:
        return json.load(f)

def build_batch_prompt(records_batch):
    prompt = [
        "Analyze each user feedback item about Google Photos search/retrieval and classify it into one or more problem archetypes.\n\n",
        "Archetypes (select ALL that apply, with confidence 0.0-1.0):\n",
        "- TEMPORAL_DECAY: User remembers the event but not when it happened\n",
        "- SPATIAL_AMBIGUITY: User remembers a place vaguely but not precisely\n",
        "- KEYWORD_MISMATCH: User's search terms don't match system's indexing/labels\n",
        "- CONTEXT_WITHOUT_CONTENT: User remembers the context but not what the photo shows\n",
        "- PEOPLE_WITHOUT_NAMES: User remembers people but they aren't tagged/identifiable\n",
        "- VISUAL_MEMORY_ONLY: User remembers visual appearance but no metadata\n",
        "- ALBUM_FRAGMENTATION: Photo is lost across albums, shared libraries, or archives\n",
        "- VOLUME_OVERWHELM: Too many photos to browse manually\n\n",
        "Return ONLY a JSON object with a key \"data\", an array of objects matching this exact structure:\n",
        "{\n  \"archetypes\": [\n    {\"code\": \"ARCHETYPE_CODE\", \"confidence\": 0.85}\n  ],\n  \"reasoning\": \"Brief explanation\"\n}\n\n"
    ]
    for i, record in enumerate(records_batch, 1):
        text = record.get("cleaned_text", record.get("raw_text", ""))
        if len(text) > 300: text = text[:300] + "..."
        meta = record.get("metadata", {})
        meta_str = f"Cat: {meta.get('photo_category')}, Strat: {meta.get('search_strategy_used')}"
        prompt.append(f"--- Item {i} ---\nFeedback: \"{text}\"\nMeta: {meta_str}\n\n")
    return "".join(prompt)

def validate_classification(classification):
    if not isinstance(classification, dict):
        return get_default_archetypes()
    archetypes = classification.get("archetypes", [])
    valid_archs = []
    if isinstance(archetypes, list):
        for a in archetypes:
            if isinstance(a, dict) and a.get("code") in VALID_ARCHETYPES:
                try:
                    conf = float(a.get("confidence", 0.0))
                    if 0.0 <= conf <= 1.0:
                        valid_archs.append({"code": a.get("code"), "confidence": conf})
                except:
                    pass
    classification["archetypes"] = valid_archs
    if not isinstance(classification.get("reasoning"), str):
        classification["reasoning"] = "No reasoning provided."
    return classification

def parse_llm_response(response_text, batch_size):
    cleaned = response_text.strip()
    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    cleaned = cleaned.strip()
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict) and "data" in parsed:
            return parsed["data"]
        elif isinstance(parsed, list):
            return parsed
    except:
        pass
    return [get_default_archetypes() for _ in range(batch_size)]

async def process_batch(client, batch, batch_idx, sem):
    async with sem:
        prompt = build_batch_prompt(batch)
        for attempt in range(5):
            try:
                response = await client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                return response.choices[0].message.content
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "rate" in error_str.lower():
                    await asyncio.sleep(10 * (attempt + 1))
                else:
                    await asyncio.sleep(5)
        return None

async def run_classification(records, clients):
    results = []
    failed_count = [0]
    batches = [records[i:i + BATCH_SIZE] for i in range(0, len(records), BATCH_SIZE)]
    pbar = tqdm(total=len(batches), desc="Classifying with Groq")
    batch_results = [None] * len(batches)
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)

    async def worker(batch_idx, batch):
        client = clients[batch_idx % len(clients)]
        res = await process_batch(client, batch, batch_idx, sem)
        batch_results[batch_idx] = (batch, res)
        pbar.update(1)

    tasks = [asyncio.create_task(worker(i, b)) for i, b in enumerate(batches)]
    await asyncio.gather(*tasks)
    pbar.close()

    for batch, response_text in batch_results:
        c_list = parse_llm_response(response_text, len(batch)) if response_text else []
        for j, record in enumerate(batch):
            if j < len(c_list):
                c = validate_classification(c_list[j])
            else:
                c = get_default_archetypes()
                failed_count[0] += 1
            record["archetype_classification"] = c
            results.append(record)
    return results, failed_count[0]

def generate_report(classified_records, failed_count):
    report = {
        "total_records": len(classified_records),
        "successfully_classified": len(classified_records) - failed_count,
        "failed_classification": failed_count,
        "archetype_distribution": {arch: 0 for arch in VALID_ARCHETYPES}
    }
    for record in classified_records:
        archs = record.get("archetype_classification", {}).get("archetypes", [])
        for a in archs:
            code = a.get("code")
            if code in report["archetype_distribution"]:
                report["archetype_distribution"][code] += 1
    return report

async def main():
    keys = [os.getenv("GROQ_API_KEY"), os.getenv("GROQ_API_KEY_2")]
    keys = [k for k in keys if k]
    if not keys:
        print("ERROR: No Groq keys.")
        sys.exit(1)
        
    clients = [AsyncGroq(api_key=k) for k in keys]
    print(f"Using {len(clients)} Groq keys.")

    all_records = load_enriched_records()
    api_records = [r for r in all_records if not r.get("metadata", {}).get("_auto_defaulted")]
    auto_defaulted = [r for r in all_records if r.get("metadata", {}).get("_auto_defaulted")]
    
    for r in auto_defaulted:
        r["archetype_classification"] = get_default_archetypes()

    completed_ids, checkpointed_records = load_checkpoint()
    api_records = [r for r in api_records if r.get("id") not in completed_ids]

    if api_records:
        newly_classified, failed_count = await run_classification(api_records, clients)
    else:
        newly_classified, failed_count = [], 0

    all_classified = checkpointed_records + newly_classified + auto_defaulted
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_classified, f, indent=2)

    valid_new = [r for r in newly_classified if r.get("archetype_classification", {}).get("reasoning") != "Failed to classify or insufficient context."]
    save_checkpoint(checkpointed_records + valid_new)

    BASE_DIR.joinpath("reports").mkdir(parents=True, exist_ok=True)
    report = generate_report(all_classified, failed_count)
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)
        
    print(f"\nTotal: {report['total_records']} | Success: {report['successfully_classified']} | Fail: {report['failed_classification']}")

if __name__ == "__main__":
    asyncio.run(main())
