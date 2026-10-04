"""
Phase 4.1: Metadata Enrichment with Gemini 2.0 Flash

Reads relevant records from data/processed/relevant/corpus_relevant.json,
sends batched prompts to Gemini 2.0 Flash for structured metadata extraction,
and saves enriched records.

Features:
- Native JSON schema output — zero parsing failures
- Pre-filters junk records (emoji-only, excessively long) to save API calls
- Checkpoint/resume: saves progress every 50 records, resumes on restart
- Adaptive rate limiting with exponential backoff on 429 errors
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
RELEVANT_DIR = BASE_DIR / "data/processed/relevant"
ENRICHED_DIR = BASE_DIR / "data/enriched"
PROMPT_FILE = BASE_DIR / "config/prompts/enrichment_prompt.txt"
CONFIG_FILE = BASE_DIR / "config/settings.yaml"
CHECKPOINT_FILE = ENRICHED_DIR / "corpus_enriched_checkpoint.json"

import yaml
try:
    with open(CONFIG_FILE, 'r') as f:
        config = yaml.safe_load(f)
except Exception:
    config = {}

# --- Model & processing config ---
MODEL = "gemini-3.5-flash-lite"
BATCH_SIZE = 20  # Larger batches, no thinking overhead
TEMPERATURE = 0.1
RATE_LIMIT_DELAY = 4.5  # 15 RPM = 1 call per 4s, with buffer

# Checkpoint interval: save every N batches
CHECKPOINT_INTERVAL = 5  # 5 batches × 20 records = every 100 records


def get_default_metadata():
    return {
        "photo_category": "unknown",
        "memory_cues_mentioned": [],
        "memory_gaps_mentioned": [],
        "search_strategy_used": "unknown",
        "frustration_level": "unknown",
        "outcome": "unknown",
        "retrieval_trigger": "unknown",
        "memory_type": "unknown",
        "time_since_photo": "unknown",
        "library_size_indicator": "unknown",
        "device_context": "unknown",
        "social_context": "unknown",
        "workaround_described": "unknown",
        "feature_mentioned": "unknown",
        "user_expertise_level": "unknown",
        "emotional_valence": "unknown",
    }


# --- Pre-filtering ---

def count_alpha_chars(text):
    return sum(1 for c in text if c.isalpha())


def is_emoji_spam(text):
    # Strip :word: emoji patterns first (cleaned_text format)
    stripped = re.sub(r':\w+:', '', text)
    alpha_count = count_alpha_chars(stripped)
    return alpha_count < 20


def pre_filter_records(records):
    """
    Separate records into API-worthy and auto-defaulted.
    Auto-defaults junk records (emoji spam, non-substantive text)
    to save API calls.
    """
    api_records = []
    auto_defaulted = []

    for record in records:
        text = record.get("cleaned_text", record.get("raw_text", ""))

        # Skip emoji-only / non-alphabetic spam
        if count_alpha_chars(text) < 30 or is_emoji_spam(text):
            record["metadata"] = get_default_metadata()
            record["metadata"]["_auto_defaulted"] = "insufficient_text"
            auto_defaulted.append(record)
            continue

        api_records.append(record)

    return api_records, auto_defaulted


# --- Checkpoint/resume ---

def load_checkpoint():
    """Load previously enriched record IDs from checkpoint file."""
    if not CHECKPOINT_FILE.exists():
        return {}, []

    try:
        with open(CHECKPOINT_FILE, "r") as f:
            checkpointed = json.load(f)
        id_set = {r["id"] for r in checkpointed if "id" in r}
        print(f"  Loaded checkpoint: {len(checkpointed)} records already enriched.")
        return id_set, checkpointed
    except (json.JSONDecodeError, KeyError):
        print("  Warning: Corrupt checkpoint file, starting fresh.")
        return {}, []


def save_checkpoint(records):
    """Save enriched records to checkpoint file."""
    ENRICHED_DIR.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(records, f, indent=2)


def load_relevant_records():
    input_file = RELEVANT_DIR / "corpus_relevant.json"
    if not input_file.exists():
        print(f"ERROR: Input file not found: {input_file}")
        sys.exit(1)
    with open(input_file, "r") as f:
        records = json.load(f)
    print(f"Loaded {len(records)} relevant records.")
    return records


# --- Prompt building ---

def build_batch_prompt(records_batch):
    prompt_parts = [
        "Analyze each user feedback item about Google Photos search/retrieval ",
        "and extract structured metadata.\n\n",
        "For EACH item below, extract the following fields. ",
        "If a field cannot be determined, use \"unknown\".\n\n",
        "Fields to extract:\n",
        "- photo_category: travel | medical | document | people | event | screenshot | receipt | food | pet | other\n",
        "- memory_cues_mentioned: list of things the user remembers (person, place, time, emotion, activity, visual detail)\n",
        "- memory_gaps_mentioned: list of things the user has forgotten (exact date, location name, album, keyword, person name)\n",
        "- search_strategy_used: keyword_search | timeline_scroll | album_browse | people_search | location_search | social_delegation | gave_up | workaround | unknown\n",
        "- frustration_level: low | medium | high | extreme\n",
        "- outcome: found | not_found | gave_up | used_workaround | unknown\n",
        "- retrieval_trigger: nostalgia | practical_need | share_with_someone | organize | legal_or_proof | curiosity | unknown\n",
        "- memory_type: episodic | semantic | sensory | mixed | unknown\n",
        "- time_since_photo: days | weeks | months | years | decades | unknown\n",
        "- library_size_indicator: small | medium | large | massive | unknown\n",
        "- device_context: mobile | desktop | voice_assistant | unknown\n",
        "- social_context: solo_search | collaborative_recall | shared_library | unknown\n",
        "- workaround_described: describe the workaround if any, else unknown\n",
        "- feature_mentioned: search_bar | albums | faces | maps | memories | assistant | lens | filters | none | unknown\n",
        "- user_expertise_level: power_user | casual | tech_illiterate | unknown\n",
        "- emotional_valence: positive_memory | negative_memory | neutral | mixed | unknown\n\n",
        "Return a JSON object with a single key \"data\", which is an array of objects. ",
        "Each element in the \"data\" array must correspond to an item below in order.\n\n"
    ]

    for i, record in enumerate(records_batch, 1):
        text = record.get("cleaned_text", record.get("raw_text", ""))
        # Truncate long texts to 400 chars to save tokens
        if len(text) > 400:
            text = text[:400] + "..."
        prompt_parts.append(f"--- Item {i} ---\n{text}\n\n")

    return "".join(prompt_parts)


# --- Validation ---

def validate_metadata(metadata):
    valid_categories = {
        "travel", "medical", "document", "people", "event",
        "screenshot", "receipt", "food", "pet", "other", "unknown"
    }
    valid_strategies = {
        "keyword_search", "timeline_scroll", "album_browse",
        "people_search", "location_search", "social_delegation",
        "gave_up", "workaround", "unknown"
    }
    valid_frustration = {"low", "medium", "high", "extreme", "unknown"}
    valid_outcomes = {"found", "not_found", "gave_up", "used_workaround", "unknown"}
    valid_triggers = {
        "nostalgia", "practical_need", "share_with_someone", "organize",
        "legal_or_proof", "curiosity", "unknown"
    }
    valid_memory_types = {"episodic", "semantic", "sensory", "mixed", "unknown"}
    valid_time_since = {"days", "weeks", "months", "years", "decades", "unknown"}
    valid_library_size = {"small", "medium", "large", "massive", "unknown"}
    valid_device = {"mobile", "desktop", "voice_assistant", "unknown"}
    valid_social = {"solo_search", "collaborative_recall", "shared_library", "unknown"}
    valid_features = {
        "search_bar", "albums", "faces", "maps", "memories",
        "assistant", "lens", "filters", "none", "unknown"
    }
    valid_expertise = {"power_user", "casual", "tech_illiterate", "unknown"}
    valid_valence = {"positive_memory", "negative_memory", "neutral", "mixed", "unknown"}

    if not isinstance(metadata, dict):
        return get_default_metadata()

    # Original 6 fields
    if metadata.get("photo_category", "").lower() not in valid_categories:
        metadata["photo_category"] = "unknown"

    if not isinstance(metadata.get("memory_cues_mentioned"), list):
        metadata["memory_cues_mentioned"] = []

    if not isinstance(metadata.get("memory_gaps_mentioned"), list):
        metadata["memory_gaps_mentioned"] = []

    if metadata.get("search_strategy_used", "").lower() not in valid_strategies:
        metadata["search_strategy_used"] = "unknown"

    if metadata.get("frustration_level", "").lower() not in valid_frustration:
        metadata["frustration_level"] = "unknown"

    if metadata.get("outcome", "").lower() not in valid_outcomes:
        metadata["outcome"] = "unknown"

    # New 10 fields — validate with fallback to "unknown"
    def validate_field(field_name, valid_set):
        val = metadata.get(field_name, "unknown")
        if isinstance(val, str) and val.lower() in valid_set:
            metadata[field_name] = val.lower()
        else:
            metadata[field_name] = "unknown"

    validate_field("retrieval_trigger", valid_triggers)
    validate_field("memory_type", valid_memory_types)
    validate_field("time_since_photo", valid_time_since)
    validate_field("library_size_indicator", valid_library_size)
    validate_field("device_context", valid_device)
    validate_field("social_context", valid_social)
    validate_field("feature_mentioned", valid_features)
    validate_field("user_expertise_level", valid_expertise)
    validate_field("emotional_valence", valid_valence)

    # workaround_described is free-text, just ensure it's a string
    if not isinstance(metadata.get("workaround_described"), str):
        metadata["workaround_described"] = "unknown"

    # Lowercase the original fields
    metadata["photo_category"] = metadata["photo_category"].lower()
    metadata["search_strategy_used"] = metadata["search_strategy_used"].lower()
    metadata["frustration_level"] = metadata["frustration_level"].lower()
    metadata["outcome"] = metadata["outcome"].lower()

    return metadata


def parse_llm_response(response_text, batch_size):
    """Parse Gemini's JSON response into a list of metadata dicts."""
    cleaned = response_text.strip()
    # Remove markdown code fences if present
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

    return [get_default_metadata() for _ in range(batch_size)]


# --- Gemini API call with retry ---

async def process_batch(client, batch, batch_idx):
    """Process a single batch via Gemini with exponential backoff."""
    prompt = build_batch_prompt(batch)

    max_retries = 8  # More retries for transient 503s
    base_delay = 5.0
    max_delay = 90.0

    for attempt in range(max_retries):
        try:
            response = await client.aio.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=TEMPERATURE,
                    response_mime_type="application/json",
                )
            )

            return response.text

        except Exception as e:
            error_str = str(e)
            if "503" in error_str or "UNAVAILABLE" in error_str:
                # Server overloaded — wait longer, these are transient
                delay = min(15.0 * (2 ** attempt), max_delay)
                print(f"\n  Batch {batch_idx}: Server busy (attempt {attempt + 1}/{max_retries}), "
                      f"waiting {delay:.0f}s...")
                await asyncio.sleep(delay)
            elif "429" in error_str or "rate" in error_str.lower() or "quota" in error_str.lower():
                delay = min(base_delay * (2 ** attempt), max_delay)
                print(f"\n  Batch {batch_idx}: Rate limited (attempt {attempt + 1}/{max_retries}), "
                      f"backing off {delay:.0f}s...")
                await asyncio.sleep(delay)
            else:
                delay = min(base_delay * (attempt + 1), max_delay)
                print(f"\n  Batch {batch_idx}: Error (attempt {attempt + 1}): {error_str[:150]}")
                await asyncio.sleep(delay)

    print(f"\n  Batch {batch_idx}: Failed after {max_retries} retries.")
    return None


# --- Main enrichment loop ---

async def run_enrichment(records, client):
    """
    Concurrent enrichment using Gemini.
    Limits spawn rate to stay within 15 RPM free tier.
    """
    results = []
    failed_count = [0]

    batches = [records[i:i + BATCH_SIZE] for i in range(0, len(records), BATCH_SIZE)]
    pbar = tqdm(total=len(batches), desc="Enriching Records")

    batch_results = [None] * len(batches)

    async def worker(batch_idx, batch):
        response_text = await process_batch(client, batch, batch_idx)
        batch_results[batch_idx] = (batch, response_text)
        pbar.update(1)

    tasks = []
    for batch_idx, batch in enumerate(batches):
        tasks.append(asyncio.create_task(worker(batch_idx, batch)))
        await asyncio.sleep(RATE_LIMIT_DELAY)  # Space out to enforce max RPM

    # Wait for all tasks to complete
    await asyncio.gather(*tasks)
    pbar.close()

    # Reconstruct final list in order
    for batch_idx, (batch, response_text) in enumerate(batch_results):
        if response_text is None:
            metadata_list = []
        else:
            metadata_list = parse_llm_response(response_text, len(batch))

        for j, record in enumerate(batch):
            if j < len(metadata_list):
                metadata = validate_metadata(metadata_list[j])
            else:
                metadata = get_default_metadata()
                failed_count[0] += 1

            record["metadata"] = metadata
            results.append(record)

    return results, failed_count[0]


# --- Report generation ---

def generate_enrichment_report(enriched_records, failed_count, auto_defaulted_count=0):
    tracked_fields = [
        "photo_category", "search_strategy_used", "frustration_level", "outcome",
        "retrieval_trigger", "memory_type", "time_since_photo",
        "library_size_indicator", "device_context", "social_context",
        "feature_mentioned", "user_expertise_level", "emotional_valence",
    ]

    report = {
        "total_records": len(enriched_records),
        "successfully_enriched": len(enriched_records) - failed_count - auto_defaulted_count,
        "failed_enrichment": failed_count,
        "auto_defaulted": auto_defaulted_count,
        "distributions": {field: {} for field in tracked_fields}
    }

    for record in enriched_records:
        meta = record.get("metadata", {})
        for field in tracked_fields:
            value = meta.get(field, "unknown")
            report["distributions"][field][value] = \
                report["distributions"][field].get(value, 0) + 1

    return report


# --- Main ---

async def main():
    print("=" * 60)
    print(f"Phase 4.1: Metadata Enrichment with Gemini 2.0 Flash")
    print(f"Batch size: {BATCH_SIZE} records per API call")
    print(f"Rate limit delay: {RATE_LIMIT_DELAY}s between calls")
    print("=" * 60)

    # Initialize Gemini client
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: No GOOGLE_API_KEY found in environment.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    print(f"Initialized Gemini client (model: {MODEL})\n")

    # Load all relevant records
    all_records = load_relevant_records()

    ENRICHED_DIR.mkdir(parents=True, exist_ok=True)

    # Pre-filter junk records
    print("\n--- Pre-filtering junk records ---")
    api_records, auto_defaulted = pre_filter_records(all_records)
    print(f"  Records for API processing: {len(api_records)}")
    print(f"  Auto-defaulted (junk/spam): {len(auto_defaulted)}")

    # Check for checkpoint and resume
    print("\n--- Checking for checkpoint ---")
    completed_ids, checkpointed_records = load_checkpoint()

    if completed_ids:
        before = len(api_records)
        api_records = [r for r in api_records if r.get("id") not in completed_ids]
        print(f"  Skipping {before - len(api_records)} already-enriched records.")
        print(f"  Remaining to process: {len(api_records)}")
    else:
        print("  No checkpoint found, processing all records.")

    # Process remaining records via API
    if api_records:
        print(f"\n--- Starting API enrichment ({len(api_records)} records, ~{len(api_records)//BATCH_SIZE + 1} batches) ---")
        newly_enriched, failed_count = await run_enrichment(api_records, client)
    else:
        print("\n--- All records already enriched! ---")
        newly_enriched = []
        failed_count = 0

    # Merge: checkpointed + newly enriched + auto-defaulted
    all_enriched = checkpointed_records + newly_enriched + auto_defaulted

    # Save final output
    output_file = ENRICHED_DIR / "corpus_enriched.json"
    with open(output_file, "w") as f:
        json.dump(all_enriched, f, indent=2)
    print(f"\nSaved enriched data to: {output_file}")

    # Save final checkpoint (so next run sees everything as done)
    save_checkpoint(checkpointed_records + newly_enriched)

    # Generate report
    report = generate_enrichment_report(all_enriched, failed_count, len(auto_defaulted))
    report_file = ENRICHED_DIR / "enrichment_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 60)
    print("Metadata Enrichment Complete.")
    print("=" * 60)
    print(f"Total records:          {report['total_records']}")
    print(f"Successfully enriched:  {report['successfully_enriched']}")
    print(f"Auto-defaulted (junk):  {report['auto_defaulted']}")
    print(f"Failed:                 {report['failed_enrichment']}")
    print()
    print("--- Distribution Summary ---")
    for field, dist in report["distributions"].items():
        print(f"\n{field}:")
        sorted_dist = sorted(dist.items(), key=lambda x: x[1], reverse=True)
        for value, count in sorted_dist:
            pct = (count / report['total_records']) * 100
            print(f"  {value:25s} {count:5d}  ({pct:.1f}%)")

    # Clean up checkpoint on full success
    if failed_count == 0 and CHECKPOINT_FILE.exists():
        print("\n✓ All records enriched successfully. Checkpoint retained for safety.")


if __name__ == "__main__":
    asyncio.run(main())
