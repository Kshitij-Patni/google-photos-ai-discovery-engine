"""
Phase 5.1: Sentiment & Emotion Analyzer

Adds multi-dimensional sentiment analysis beyond the crude 4-level frustration_level.
Runs entirely locally — no API calls, no cost.

Produces per-record:
  - sentiment_polarity  (-1.0 to +1.0)
  - sentiment_label     (very_negative | negative | neutral | positive | very_positive)
  - urgency_score       (0.0 to 1.0)
  - user_effort_score   (0.0 to 1.0) — how much effort the user put into describing
  - emotion_signals     dict of detected emotion markers

Pipeline position: runs AFTER archetype_classifier
Input:  data/enriched/corpus_classified.json
Output: data/enriched/corpus_sentiment.json
        reports/sentiment_report.json
"""

import json
import re
import os
import sys
from pathlib import Path
from collections import Counter
from tqdm import tqdm

# --- Configuration ---

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENRICHED_DIR = BASE_DIR / "data" / "enriched"
INPUT_FILE = ENRICHED_DIR / "corpus_classified.json"
OUTPUT_FILE = ENRICHED_DIR / "corpus_sentiment.json"
REPORT_DIR = BASE_DIR / "reports"
REPORT_FILE = REPORT_DIR / "sentiment_report.json"


# --- VADER-like Sentiment (lightweight, no heavy model load) ---

# Curated lexicon for photo-retrieval domain
POSITIVE_WORDS = {
    "love", "great", "amazing", "excellent", "awesome", "perfect", "fantastic",
    "wonderful", "best", "helpful", "useful", "easy", "convenient", "brilliant",
    "impressed", "beautiful", "quick", "fast", "reliable", "smooth", "intuitive",
    "finally", "found", "success", "works", "working", "solved", "fixed",
    "thank", "thanks", "happy", "glad", "pleased", "satisfied", "recommend",
}

NEGATIVE_WORDS = {
    "terrible", "horrible", "awful", "worst", "hate", "useless", "broken",
    "frustrating", "frustrated", "annoying", "annoyed", "disappointed",
    "disappointing", "pathetic", "ridiculous", "impossible", "stupid",
    "trash", "garbage", "waste", "wasted", "ruined", "nightmare", "disaster",
    "lost", "missing", "gone", "disappeared", "deleted", "removed", "bug",
    "buggy", "glitch", "crash", "crashes", "slow", "laggy", "lag",
    "can't", "cannot", "unable", "fail", "failed", "failure", "error",
    "worse", "downgrade", "regression", "unusable", "pointless", "abandoned",
}

INTENSIFIERS = {
    "very", "extremely", "absolutely", "completely", "totally", "utterly",
    "really", "so", "incredibly", "unbelievably", "super", "highly",
}

NEGATORS = {"not", "no", "never", "neither", "nor", "don't", "doesn't",
            "didn't", "won't", "wouldn't", "shouldn't", "can't", "cannot"}

# Urgency markers
URGENCY_WORDS = {
    "urgent", "urgently", "asap", "immediately", "help", "please", "need",
    "critical", "important", "emergency", "desperate", "desperately",
    "begging", "pray", "praying", "serious", "seriously",
}

# Emotion marker patterns
EMOTION_PATTERNS = {
    "anger": ["angry", "furious", "rage", "mad", "infuriating", "outraged",
              "livid", "pissed", "enraged_face", "hate"],
    "sadness": ["sad", "depressed", "heartbroken", "devastated", "crying",
                "miss", "lost", "mourn", "grief", "loudly_crying_face",
                "pensive_face", "crying_face"],
    "fear": ["scared", "afraid", "worried", "anxious", "panic", "terrified",
             "nervous", "concern", "concerned"],
    "surprise": ["shocked", "surprised", "unexpected", "suddenly", "wow",
                 "exploding_head", "astonished"],
    "disgust": ["disgusting", "gross", "sick", "appalling", "revolting",
                "shameful", "unacceptable"],
    "joy": ["happy", "joy", "excited", "thrilled", "delighted", "celebrate",
            "partying_face", "grinning", "party_popper", "love"],
    "resignation": ["give up", "gave up", "giving up", "given up",
                    "no point", "pointless", "whatever", "done with",
                    "moving on", "switching", "uninstall"],
}


def compute_sentiment_polarity(text):
    """
    Compute sentiment polarity from -1.0 to +1.0.
    Uses word-level lexicon with intensifier/negator awareness.
    """
    words = re.findall(r'\b\w+\b', text.lower())
    if not words:
        return 0.0

    score = 0.0
    multiplier = 1.0

    for i, word in enumerate(words):
        if word in NEGATORS:
            multiplier = -1.0
            continue

        if word in INTENSIFIERS:
            continue  # intensifier modifies next word

        intensity = 1.0
        if i > 0 and words[i - 1] in INTENSIFIERS:
            intensity = 1.5

        if word in POSITIVE_WORDS:
            score += intensity * multiplier
        elif word in NEGATIVE_WORDS:
            score -= intensity * multiplier

        # Reset negation after use
        if word in POSITIVE_WORDS or word in NEGATIVE_WORDS:
            multiplier = 1.0

    # Handle exclamation marks (amplify existing sentiment)
    excl_count = text.count("!")
    if excl_count > 0:
        score *= (1 + min(excl_count * 0.1, 0.5))

    # Handle ALL CAPS words (amplify)
    caps_words = [w for w in text.split() if w.isupper() and len(w) > 2]
    if caps_words:
        score *= (1 + min(len(caps_words) * 0.05, 0.3))

    # Normalize to -1.0 to 1.0 range using tanh-like scaling
    import math
    normalized = math.tanh(score / max(len(words) * 0.1, 1))

    return round(normalized, 4)


def polarity_to_label(polarity):
    """Convert numeric polarity to categorical label."""
    if polarity <= -0.5:
        return "very_negative"
    elif polarity <= -0.15:
        return "negative"
    elif polarity <= 0.15:
        return "neutral"
    elif polarity <= 0.5:
        return "positive"
    else:
        return "very_positive"


def compute_urgency_score(text):
    """
    Score 0.0 to 1.0 based on urgency markers.
    """
    words = set(re.findall(r'\b\w+\b', text.lower()))
    urgency_hits = words & URGENCY_WORDS
    excl_count = min(text.count("!"), 5)
    caps_ratio = sum(1 for w in text.split() if w.isupper() and len(w) > 2) / max(len(text.split()), 1)

    score = (
        min(len(urgency_hits) * 0.15, 0.6) +
        min(excl_count * 0.05, 0.2) +
        min(caps_ratio * 2, 0.2)
    )

    return round(min(score, 1.0), 4)


def compute_user_effort_score(text):
    """
    How much effort did the user put into describing the problem?
    Higher effort = longer, more detailed, structured feedback.
    """
    word_count = len(text.split())
    sentence_count = max(len(re.split(r'[.!?]+', text)), 1)
    avg_sentence_length = word_count / sentence_count

    # Indicators of high effort
    has_specific_details = bool(re.search(
        r'\b(example|for instance|specifically|e\.g\.|i\.e\.|such as|like when)\b',
        text, re.IGNORECASE
    ))
    has_temporal_refs = bool(re.search(
        r'\b(yesterday|last week|last month|last year|ago|since|before|after|when|date)\b',
        text, re.IGNORECASE
    ))
    has_feature_refs = bool(re.search(
        r'\b(search|album|face|tag|filter|folder|label|share|library|archive|map)\b',
        text, re.IGNORECASE
    ))
    has_steps_described = bool(re.search(
        r'\b(first|then|next|after that|tried|attempt|step)\b',
        text, re.IGNORECASE
    ))
    has_update_markers = bool(re.search(
        r'\b(update|edit|follow.?up|addendum)\b', text, re.IGNORECASE
    ))

    # Length score (0-0.4)
    length_score = min(word_count / 150, 0.4)

    # Detail score (0-0.6)
    detail_score = sum([
        0.12 if has_specific_details else 0,
        0.12 if has_temporal_refs else 0,
        0.12 if has_feature_refs else 0,
        0.12 if has_steps_described else 0,
        0.08 if has_update_markers else 0,
        0.04 if avg_sentence_length > 12 else 0,
    ])

    return round(min(length_score + detail_score, 1.0), 4)


def detect_emotion_signals(text):
    """
    Detect emotion markers in text.
    Returns dict of emotion → intensity (0.0-1.0).
    """
    text_lower = text.lower()
    emotions = {}

    for emotion, markers in EMOTION_PATTERNS.items():
        hits = sum(1 for m in markers if m in text_lower)
        if hits > 0:
            emotions[emotion] = round(min(hits * 0.25, 1.0), 2)

    return emotions


def analyze_record(record):
    """
    Run all sentiment analyses on a single record.
    Returns a sentiment_analysis dict.
    """
    text = record.get("cleaned_text", record.get("raw_text", ""))

    polarity = compute_sentiment_polarity(text)
    label = polarity_to_label(polarity)
    urgency = compute_urgency_score(text)
    effort = compute_user_effort_score(text)
    emotions = detect_emotion_signals(text)

    return {
        "sentiment_polarity": polarity,
        "sentiment_label": label,
        "urgency_score": urgency,
        "user_effort_score": effort,
        "emotion_signals": emotions,
    }


def generate_report(records):
    """Generate aggregate sentiment statistics."""
    total = len(records)
    label_dist = Counter()
    urgency_dist = {"low": 0, "medium": 0, "high": 0}
    effort_dist = {"low": 0, "medium": 0, "high": 0}
    emotion_counts = Counter()

    polarity_sum = 0.0
    urgency_sum = 0.0
    effort_sum = 0.0

    for r in records:
        sa = r.get("sentiment_analysis", {})
        polarity = sa.get("sentiment_polarity", 0)
        urgency = sa.get("urgency_score", 0)
        effort = sa.get("user_effort_score", 0)

        polarity_sum += polarity
        urgency_sum += urgency
        effort_sum += effort

        label_dist[sa.get("sentiment_label", "neutral")] += 1

        if urgency < 0.3:
            urgency_dist["low"] += 1
        elif urgency < 0.6:
            urgency_dist["medium"] += 1
        else:
            urgency_dist["high"] += 1

        if effort < 0.3:
            effort_dist["low"] += 1
        elif effort < 0.6:
            effort_dist["medium"] += 1
        else:
            effort_dist["high"] += 1

        for emotion in sa.get("emotion_signals", {}):
            emotion_counts[emotion] += 1

    return {
        "total_records": total,
        "average_polarity": round(polarity_sum / max(total, 1), 4),
        "average_urgency": round(urgency_sum / max(total, 1), 4),
        "average_effort": round(effort_sum / max(total, 1), 4),
        "sentiment_label_distribution": dict(label_dist.most_common()),
        "urgency_distribution": urgency_dist,
        "effort_distribution": effort_dist,
        "emotion_frequency": dict(emotion_counts.most_common()),
    }


# --- Main ---

def main():
    print("=" * 60)
    print("Phase 5.1: Sentiment & Emotion Analysis")
    print("=" * 60)

    # Load data
    if not INPUT_FILE.exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        sys.exit(1)

    with open(INPUT_FILE, "r") as f:
        records = json.load(f)
    print(f"Loaded {len(records)} classified records.\n")

    # Process each record
    for record in tqdm(records, desc="Analyzing Sentiment"):
        record["sentiment_analysis"] = analyze_record(record)

    # Save output
    ENRICHED_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(records, f, indent=2)
    print(f"\nSaved sentiment-analyzed data to: {OUTPUT_FILE}")

    # Generate report
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = generate_report(records)
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print(f"\n{'=' * 60}")
    print("Sentiment Analysis Complete.")
    print(f"{'=' * 60}")
    print(f"Average polarity:  {report['average_polarity']:+.4f}")
    print(f"Average urgency:   {report['average_urgency']:.4f}")
    print(f"Average effort:    {report['average_effort']:.4f}")
    print(f"\n--- Sentiment Distribution ---")
    for label, count in report["sentiment_label_distribution"].items():
        pct = (count / report["total_records"]) * 100
        print(f"  {label:20s} {count:5d}  ({pct:.1f}%)")
    print(f"\n--- Emotion Frequency ---")
    for emotion, count in report["emotion_frequency"].items():
        pct = (count / report["total_records"]) * 100
        print(f"  {emotion:20s} {count:5d}  ({pct:.1f}%)")


if __name__ == "__main__":
    main()
