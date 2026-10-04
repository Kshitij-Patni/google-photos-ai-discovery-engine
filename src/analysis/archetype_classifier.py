"""
Phase 4.2: Archetype Classification with Gemini

Reads enriched records from data/enriched/corpus_enriched.json,
sends batched prompts to Gemini for multi-label archetype classification,
and saves the classified records.

Features:
- Native JSON schema output
- Checkpoint/resume: saves progress
- Concurrent processing mapped to rate limits (15 RPM)
"""

import json
import os
import sys
import re
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from tqdm.asyncio import tqdm

from google import genai
from google.genai import types

# --- Configuration ---
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENRICHED_DIR = BASE_DIR / "data/enriched"
INPUT_FILE = ENRICHED_DIR / "corpus_enriched.json"
OUTPUT_FILE = ENRICHED_DIR / "corpus_classified.json"
CHECKPOINT_FILE = ENRICHED_DIR / "corpus_classified_checkpoint.json"
REPORT_FILE = BASE_DIR / "reports/archetype_distribution.json"

# --- Model & processing config ---
MODEL = "gemini-3.5-flash-lite"
BATCH_SIZE = 20
TEMPERATURE = 0.1
RATE_LIMIT_DELAY = 4.5  # 15 RPM

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

# --- Checkpoint/resume ---

def load_checkpoint():
    if not CHECKPOINT_FILE.exists():
        return {}, []

    try:
        with open(CHECKPOINT_FILE, "r") as f:
            checkpointed = json.load(f)
        id_set = {r["id"] for r in checkpointed if "id" in r}
        print(f"  Loaded checkpoint: {len(checkpointed)} records already classified.")
        return id_set, checkpointed
    except (json.JSONDecodeError, KeyError):
        print("  Warning: Corrupt checkpoint file, starting fresh.")
        return {}, []

def save_checkpoint(records):
    ENRICHED_DIR.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(records, f, indent=2)

def load_enriched_records():
    if not INPUT_FILE.exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        sys.exit(1)
    with open(INPUT_FILE, "r") as f:
        records = json.load(f)
    print(f"Loaded {len(records)} enriched records.")
    return records

# --- Prompt building ---

def build_batch_prompt(records_batch):
    prompt_parts = [
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
        "Return a JSON object with a single key \"data\", which is an array of objects.\n",
        "Each element in the \"data\" array must correspond to an item below in order and match this structure:\n",
        "{\n  \"archetypes\": [\n    {\"code\": \"ARCHETYPE_CODE\", \"confidence\": 0.85}\n  ],\n  \"reasoning\": \"Brief explanation\"\n}\n\n"
    ]

    for i, record in enumerate(records_batch, 1):
        text = record.get("cleaned_text", record.get("raw_text", ""))
        if len(text) > 400:
            text = text[:400] + "..."
            
        meta = record.get("metadata", {})
        meta_str = f"Category: {meta.get('photo_category')}, Strategy: {meta.get('search_strategy_used')}, Frustration: {meta.get('frustration_level')}, Outcome: {meta.get('outcome')}"
        
        prompt_parts.append(f"--- Item {i} ---\nUser Feedback: \"{text}\"\nMetadata: {meta_str}\n\n")

    return "".join(prompt_parts)

# --- Validation ---

def validate_classification(classification):
    if not isinstance(classification, dict):
        return get_default_archetypes()

    archetypes = classification.get("archetypes", [])
    valid_archs = []
    
    if isinstance(archetypes, list):
        for a in archetypes:
            if isinstance(a, dict) and a.get("code") in VALID_ARCHETYPES:
                conf = a.get("confidence", 0.0)
                try:
                    conf = float(conf)
                    if 0.0 <= conf <= 1.0:
                        valid_archs.append({"code": a.get("code"), "confidence": conf})
                except (ValueError, TypeError):
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
        elif isinstance(parsed, dict):
            return [parsed]
    except json.JSONDecodeError:
        pass

    return [get_default_archetypes() for _ in range(batch_size)]

# --- Gemini API call with retry ---

async def process_batch(client, batch, batch_idx):
    prompt = build_batch_prompt(batch)
    max_retries = 8
    base_delay = 5.0
    max_delay = 90.0

    for attempt in range(max_retries):
        try:
            response = await client.aio.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                )
            )
            return response.text

        except Exception as e:
            error_str = str(e)
            if "503" in error_str or "UNAVAILABLE" in error_str:
                delay = min(15.0 * (2 ** attempt), max_delay)
                print(f"\n  Batch {batch_idx}: Server busy (attempt {attempt + 1}/{max_retries}), waiting {delay:.0f}s...")
                await asyncio.sleep(delay)
            elif "429" in error_str or "rate" in error_str.lower() or "quota" in error_str.lower():
                delay = min(base_delay * (2 ** attempt), max_delay)
                print(f"\n  Batch {batch_idx}: Rate limited (attempt {attempt + 1}/{max_retries}), backing off {delay:.0f}s...")
                await asyncio.sleep(delay)
            else:
                delay = min(base_delay * (attempt + 1), max_delay)
                print(f"\n  Batch {batch_idx}: Error (attempt {attempt + 1}): {error_str[:150]}")
                await asyncio.sleep(delay)

    print(f"\n  Batch {batch_idx}: Failed after {max_retries} retries.")
    return None

# --- Main loop ---

async def run_classification(records, client):
    results = []
    failed_count = [0]

    batches = [records[i:i + BATCH_SIZE] for i in range(0, len(records), BATCH_SIZE)]
    pbar = tqdm(total=len(batches), desc="Classifying Archetypes")

    batch_results = []
    
    for batch_idx, batch in enumerate(batches):
        response_text = await process_batch(client, batch, batch_idx)
        batch_results.append((batch, response_text))
        pbar.update(1)
        
        if batch_idx < len(batches) - 1:
            await asyncio.sleep(RATE_LIMIT_DELAY)

    pbar.close()

    for batch_idx, (batch, response_text) in enumerate(batch_results):
        if response_text is None:
            classification_list = []
        else:
            classification_list = parse_llm_response(response_text, len(batch))

        for j, record in enumerate(batch):
            if j < len(classification_list):
                classification = validate_classification(classification_list[j])
            else:
                classification = get_default_archetypes()
                failed_count[0] += 1

            record["archetype_classification"] = classification
            results.append(record)

    return results, failed_count[0]

# --- Report generation ---

def generate_report(classified_records, failed_count):
    report = {
        "total_records": len(classified_records),
        "successfully_classified": len(classified_records) - failed_count,
        "failed_classification": failed_count,
        "archetype_distribution": {arch: 0 for arch in VALID_ARCHETYPES},
        "records_with_multiple_archetypes": 0,
        "records_with_no_archetypes": 0
    }

    for record in classified_records:
        archs = record.get("archetype_classification", {}).get("archetypes", [])
        if len(archs) > 1:
            report["records_with_multiple_archetypes"] += 1
        elif len(archs) == 0:
            report["records_with_no_archetypes"] += 1
            
        for a in archs:
            code = a.get("code")
            if code in report["archetype_distribution"]:
                report["archetype_distribution"][code] += 1

    return report

# --- Main ---

async def main():
    print("=" * 60)
    print(f"Phase 4.2: Archetype Classification with Gemini API")
    print(f"Batch size: {BATCH_SIZE} records per API call")
    print("=" * 60)

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: No GOOGLE_API_KEY found.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    print(f"Initialized Gemini client (model: {MODEL})\n")

    all_records = load_enriched_records()
    
    # We don't need to re-process auto-defaulted (junk) records, but let's keep them and pass them through 
    # as having no archetypes, or we can classify them too. Actually let's skip API calls for junk.
    api_records = []
    auto_defaulted = []
    
    for r in all_records:
        if r.get("metadata", {}).get("_auto_defaulted"):
            r["archetype_classification"] = get_default_archetypes()
            auto_defaulted.append(r)
        else:
            api_records.append(r)
            
    print(f"\n--- Separated Records ---")
    print(f"  Records for API processing: {len(api_records)}")
    print(f"  Auto-defaulted (junk/spam) skipped: {len(auto_defaulted)}")

    print("\n--- Checking for checkpoint ---")
    completed_ids, checkpointed_records = load_checkpoint()

    if completed_ids:
        before = len(api_records)
        api_records = [r for r in api_records if r.get("id") not in completed_ids]
        print(f"  Skipping {before - len(api_records)} already-classified records.")
        print(f"  Remaining to process: {len(api_records)}")
    else:
        print("  No checkpoint found, processing all records.")

    if api_records:
        print(f"\n--- Starting API classification ({len(api_records)} records, ~{len(api_records)//BATCH_SIZE + 1} batches) ---")
        newly_classified, failed_count = await run_classification(api_records, client)
    else:
        print("\n--- All records already classified! ---")
        newly_classified = []
        failed_count = 0

    all_classified = checkpointed_records + newly_classified + auto_defaulted

    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_classified, f, indent=2)
    print(f"\nSaved classified data to: {OUTPUT_FILE}")

    valid_newly_classified = [r for r in newly_classified if r.get("archetype_classification", {}).get("reasoning") != "Failed to classify or insufficient context."]
    save_checkpoint(checkpointed_records + valid_newly_classified)

    BASE_DIR.joinpath("reports").mkdir(parents=True, exist_ok=True)
    report = generate_report(all_classified, failed_count)
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 60)
    print("Archetype Classification Complete.")
    print("=" * 60)
    print(f"Total records:          {report['total_records']}")
    print(f"Successfully classified:{report['successfully_classified']}")
    print(f"Failed:                 {report['failed_classification']}")
    print("\n--- Archetype Distribution ---")
    sorted_dist = sorted(report["archetype_distribution"].items(), key=lambda x: x[1], reverse=True)
    for value, count in sorted_dist:
        pct = (count / report['total_records']) * 100
        print(f"  {value:25s} {count:5d}  ({pct:.1f}%)")

if __name__ == "__main__":
    asyncio.run(main())
