"""
Phase 5.2: Retrieval Journey Stage Mapper

Maps each feedback record to WHERE in the retrieval journey the breakdown
happened. This directly feeds Part 2 (Business Metric Decomposition) of the
fellowship project.

Journey stages:
  TRIGGER    → User realizes they want a photo
  FORMULATE  → User tries to describe/recall what they remember
  SEARCH     → User enters query / browses / uses a feature
  EVALUATE   → User scans results
  REFINE     → User modifies search / tries alternative approach
  ABANDON    → User gives up

Each record gets:
  - primary_breakdown_stage   (the stage where the main failure occurred)
  - journey_stages_mentioned  (all stages referenced in the feedback)
  - journey_depth             (how far the user got: 0-5)
  - retry_count_indicator     (how many times did they retry)

Pipeline position: runs AFTER sentiment_analyzer
Input:  data/enriched/corpus_sentiment.json
Output: data/enriched/corpus_journey.json
        reports/journey_report.json
"""

import json
import re
import sys
from pathlib import Path
from collections import Counter
from tqdm import tqdm

# --- Configuration ---

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENRICHED_DIR = BASE_DIR / "data" / "enriched"
INPUT_FILE = ENRICHED_DIR / "corpus_sentiment.json"
OUTPUT_FILE = ENRICHED_DIR / "corpus_journey.json"
REPORT_DIR = BASE_DIR / "reports"
REPORT_FILE = REPORT_DIR / "journey_report.json"


# --- Journey Stage Detection Patterns ---

# Each stage has keyword patterns that signal the user referenced it.
# Patterns are (regex_pattern, weight) tuples — higher weight = stronger signal.

STAGE_PATTERNS = {
    "TRIGGER": [
        (r'\b(looking for|trying to find|wanted to find|need to find|searching for|want to retrieve)\b', 1.0),
        (r'\b(remembered|recall|reminds me|thinking about|wanted to see)\b', 0.8),
        (r'\b(need|needed) (a|the|my|that) (photo|picture|pic|image|video)\b', 0.9),
        (r'\b(where is|where are|where did|where\'s)\b', 0.7),
        (r'\b(can\'t find|cannot find|unable to find|couldn\'t find)\b', 0.9),
    ],
    "FORMULATE": [
        (r'\b(how do (i|you)|how to) (search|find|look)\b', 1.0),
        (r'\b(don\'t know (what|how) to (search|type|enter))\b', 1.0),
        (r'\b(what (keyword|term|word)s? (to|should|do))\b', 0.9),
        (r'\b(i remember .{5,40} but)\b', 0.8),
        (r'\b(vaguely|roughly|approximately|somewhere|sometime)\b', 0.7),
        (r'\b(not sure (what|how|which))\b', 0.8),
        (r'\b(describe|express|articulate|put into words)\b', 0.7),
    ],
    "SEARCH": [
        (r'\b(searched|search for|typed|entered|queried|looked up)\b', 1.0),
        (r'\b(used? the search|search bar|search function|search feature)\b', 1.0),
        (r'\b(browsed?|scrolled?|scrolling|browsing)\b', 0.8),
        (r'\b(filter|filtered|sorted|sort by)\b', 0.7),
        (r'\b(went to|opened|clicked|tapped|checked)\b', 0.6),
        (r'\b(album|albums|folder|folders|face|faces|map|maps|location)\b', 0.5),
        (r'\b(google lens|assistant|ai|suggestions)\b', 0.5),
    ],
    "EVALUATE": [
        (r'\b(results|showed|returned|displayed|came up|appeared)\b', 0.9),
        (r'\b(too many|thousands|hundreds|tons of|flood|overwhelm)\b', 1.0),
        (r'\b(irrelevant|unrelated|wrong|incorrect|not what|nothing relevant)\b', 1.0),
        (r'\b(couldn\'t see|hard to (find|spot|see|identify))\b', 0.8),
        (r'\b(needle in|buried|hidden|lost in)\b', 0.9),
        (r'\b(no results|nothing (found|came|showed|appeared))\b', 1.0),
        (r'\b(mixed (up|in)|scattered|spread across)\b', 0.7),
    ],
    "REFINE": [
        (r'\b(tried (different|another|multiple|various|several))\b', 1.0),
        (r'\b(re.?search|search again|tried again|another (search|query|attempt))\b', 1.0),
        (r'\b(narrowed?|refined?|modified|changed|adjusted|tweaked)\b', 0.8),
        (r'\b(added|combined|combined with|plus|and also)\b', 0.5),
        (r'\b(still (can\'t|couldn\'t|unable|nothing|no)|same results)\b', 0.7),
        (r'\b(even after|despite|no matter (what|how))\b', 0.8),
    ],
    "ABANDON": [
        (r'\b(gave up|give up|giving up|given up|abandoned)\b', 1.0),
        (r'\b(pointless|hopeless|waste of time|wasted .{0,10} time)\b', 1.0),
        (r'\b(never (found|find|going to))\b', 0.9),
        (r'\b(uninstall|switch|moving (to|away)|switching|alternative)\b', 0.8),
        (r'\b(lost forever|permanently lost|gone forever)\b', 1.0),
        (r'\b(frustrated|frustrated enough|done with|fed up|had enough)\b', 0.7),
        (r'\b(stopped (trying|using|searching))\b', 0.9),
    ],
}

# Stage order for computing journey depth
STAGE_ORDER = ["TRIGGER", "FORMULATE", "SEARCH", "EVALUATE", "REFINE", "ABANDON"]
STAGE_DEPTH = {stage: i for i, stage in enumerate(STAGE_ORDER)}

# Retry indicators
RETRY_PATTERNS = [
    (r'\b(tried (\d+|multiple|several|many|various|different) times?)\b', 'explicit'),
    (r'\b(again and again|over and over|repeatedly|keep trying)\b', 'repeated'),
    (r'\b(tried (different|another|various) (keyword|search|term|approach|method))\b', 'strategy_change'),
    (r'\b(first .{5,50} then .{5,50} (then|finally|still))\b', 'sequential'),
]


def detect_journey_stages(text):
    """
    Detect which journey stages are mentioned in the text.
    Returns dict of stage → confidence score.
    """
    text_lower = text.lower()
    stages_detected = {}

    for stage, patterns in STAGE_PATTERNS.items():
        total_weight = 0.0
        hits = 0
        for pattern, weight in patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                hits += len(matches)
                total_weight += weight * len(matches)

        if hits > 0:
            # Normalize score to 0-1 range
            confidence = min(total_weight / (len(patterns) * 0.5), 1.0)
            stages_detected[stage] = round(confidence, 3)

    return stages_detected


def determine_primary_breakdown(stages_detected, metadata=None):
    """
    Determine the primary breakdown stage.
    Logic:
    1. If ABANDON is detected with high confidence, it's the deepest failure.
    2. Otherwise, find the latest stage with highest confidence.
    3. Use metadata hints if text signals are weak.
    """
    if not stages_detected:
        # Use metadata as fallback
        if metadata:
            outcome = metadata.get("outcome", "unknown")
            strategy = metadata.get("search_strategy_used", "unknown")
            if outcome == "gave_up":
                return "ABANDON"
            elif outcome == "not_found" and strategy != "unknown":
                return "EVALUATE"
            elif strategy != "unknown":
                return "SEARCH"
        return "UNKNOWN"

    # Priority: deepest stage with sufficient confidence
    best_stage = None
    best_priority = -1

    for stage, confidence in stages_detected.items():
        depth = STAGE_DEPTH.get(stage, 0)
        # Weight confidence by depth to prefer deeper stages
        effective_score = confidence * (1 + depth * 0.15)
        if effective_score > best_priority:
            best_priority = effective_score
            best_stage = stage

    return best_stage


def compute_journey_depth(stages_detected):
    """How far did the user get in the retrieval journey? (0-5)"""
    if not stages_detected:
        return 0
    max_depth = 0
    for stage in stages_detected:
        depth = STAGE_DEPTH.get(stage, 0)
        if depth > max_depth:
            max_depth = depth
    return max_depth


def detect_retry_count(text):
    """Estimate how many times the user retried."""
    text_lower = text.lower()
    retry_signals = 0

    for pattern, _ in RETRY_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            retry_signals += 1

    # Also check for explicit numbers
    explicit_match = re.search(r'tried (\d+) times?', text_lower)
    if explicit_match:
        return int(explicit_match.group(1))

    if retry_signals >= 2:
        return 3  # Multiple retry signals → estimate ~3
    elif retry_signals == 1:
        return 2  # Single retry signal → estimate ~2
    else:
        # Check if REFINE stage was detected (implies at least one retry)
        return 0


def map_journey(record):
    """
    Map a single record to journey stages.
    Returns journey_mapping dict.
    """
    text = record.get("cleaned_text", record.get("raw_text", ""))
    metadata = record.get("metadata", {})

    stages_detected = detect_journey_stages(text)
    primary_breakdown = determine_primary_breakdown(stages_detected, metadata)
    depth = compute_journey_depth(stages_detected)
    retry_count = detect_retry_count(text)

    # If we detected REFINE but retry is 0, set to at least 1
    if "REFINE" in stages_detected and retry_count == 0:
        retry_count = 1

    return {
        "primary_breakdown_stage": primary_breakdown,
        "journey_stages_mentioned": stages_detected,
        "journey_depth": depth,
        "retry_count_indicator": retry_count,
    }


def generate_report(records):
    """Generate aggregate journey stage statistics."""
    total = len(records)
    stage_dist = Counter()
    depth_dist = Counter()
    retry_dist = Counter()

    # Stage co-occurrence
    stage_cooccurrence = {}
    for s in STAGE_ORDER:
        stage_cooccurrence[s] = Counter()

    for r in records:
        jm = r.get("journey_mapping", {})
        primary = jm.get("primary_breakdown_stage", "UNKNOWN")
        stage_dist[primary] += 1
        depth_dist[jm.get("journey_depth", 0)] += 1

        retries = jm.get("retry_count_indicator", 0)
        if retries == 0:
            retry_dist["no_retry"] += 1
        elif retries == 1:
            retry_dist["1_retry"] += 1
        elif retries <= 3:
            retry_dist["2-3_retries"] += 1
        else:
            retry_dist["4+_retries"] += 1

        # Co-occurrence
        stages = list(jm.get("journey_stages_mentioned", {}).keys())
        for i, s1 in enumerate(stages):
            for s2 in stages[i + 1:]:
                stage_cooccurrence[s1][s2] += 1
                stage_cooccurrence[s2][s1] += 1

    # Flatten co-occurrence for JSON
    cooccurrence_flat = {}
    for s1, counts in stage_cooccurrence.items():
        if counts:
            cooccurrence_flat[s1] = dict(counts.most_common(5))

    return {
        "total_records": total,
        "primary_breakdown_distribution": dict(stage_dist.most_common()),
        "journey_depth_distribution": {str(k): v for k, v in sorted(depth_dist.items())},
        "retry_distribution": dict(retry_dist),
        "stage_cooccurrence_top5": cooccurrence_flat,
    }


# --- Main ---

def main():
    print("=" * 60)
    print("Phase 5.2: Retrieval Journey Mapping")
    print("=" * 60)

    if not INPUT_FILE.exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        sys.exit(1)

    with open(INPUT_FILE, "r") as f:
        records = json.load(f)
    print(f"Loaded {len(records)} records.\n")

    # Map each record
    for record in tqdm(records, desc="Mapping Journey Stages"):
        record["journey_mapping"] = map_journey(record)

    # Save output
    ENRICHED_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(records, f, indent=2)
    print(f"\nSaved journey-mapped data to: {OUTPUT_FILE}")

    # Generate report
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = generate_report(records)
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print(f"\n{'=' * 60}")
    print("Journey Mapping Complete.")
    print(f"{'=' * 60}")
    print(f"\n--- Primary Breakdown Stage ---")
    for stage, count in report["primary_breakdown_distribution"].items():
        pct = (count / report["total_records"]) * 100
        print(f"  {stage:20s} {count:5d}  ({pct:.1f}%)")
    print(f"\n--- Journey Depth ---")
    for depth, count in report["journey_depth_distribution"].items():
        pct = (count / report["total_records"]) * 100
        print(f"  Depth {depth:3s}           {count:5d}  ({pct:.1f}%)")
    print(f"\n--- Retry Behavior ---")
    for retry, count in report["retry_distribution"].items():
        pct = (count / report["total_records"]) * 100
        print(f"  {retry:20s} {count:5d}  ({pct:.1f}%)")


if __name__ == "__main__":
    main()
