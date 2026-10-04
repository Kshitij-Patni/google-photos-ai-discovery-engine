"""
Phase 6.2: User Segment Clusterer

Clusters users into behavioral segments based on their combination of:
  - Photo category they search for
  - Search strategy used
  - Frustration level
  - Outcome
  - Journey depth
  - Sentiment
  - Archetype profile

Uses feature encoding + K-Means/HDBSCAN clustering, then generates
human-readable segment personas.

Pipeline position: runs AFTER correlation_engine (uses same input)
Input:  data/enriched/corpus_themed.json
Output: data/enriched/corpus_segmented.json
        reports/user_segments_report.json
"""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict
from tqdm import tqdm

import numpy as np
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENRICHED_DIR = BASE_DIR / "data" / "enriched"
OUTPUT_FILE = ENRICHED_DIR / "corpus_segmented.json"
REPORT_DIR = BASE_DIR / "reports"
REPORT_FILE = REPORT_DIR / "user_segments_report.json"

# Graceful fallback: use best available enriched file
_FALLBACK_INPUTS = [
    ENRICHED_DIR / "corpus_themed.json",
    ENRICHED_DIR / "corpus_journey.json",
    ENRICHED_DIR / "corpus_sentiment.json",
    ENRICHED_DIR / "corpus_classified.json",
]
INPUT_FILE = next((f for f in _FALLBACK_INPUTS if f.exists()), _FALLBACK_INPUTS[0])

# Number of segments to try
K_RANGE = range(3, 10)


def load_records():
    if not INPUT_FILE.exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        sys.exit(1)
    with open(INPUT_FILE, "r") as f:
        records = json.load(f)
    print(f"Loaded {len(records)} records.")
    return records


def extract_features(records):
    """
    Extract a feature matrix from records for clustering.
    Combines categorical (one-hot) and numerical features.
    """
    # Categorical features
    categorical_data = []
    numerical_data = []

    for r in records:
        meta = r.get("metadata", {})
        sa = r.get("sentiment_analysis", {})
        jm = r.get("journey_mapping", {})
        arch = r.get("archetype_classification", {})

        # Categorical
        cat_row = [
            meta.get("photo_category", "unknown"),
            meta.get("search_strategy_used", "unknown"),
            meta.get("frustration_level", "unknown"),
            meta.get("outcome", "unknown"),
            jm.get("primary_breakdown_stage", "UNKNOWN"),
            sa.get("sentiment_label", "neutral"),
        ]

        # Primary archetype (treat as categorical)
        archetypes = arch.get("archetypes", [])
        primary_arch = "NONE"
        if archetypes:
            primary_arch = max(archetypes, key=lambda a: a.get("confidence", 0)).get("code", "NONE")
        cat_row.append(primary_arch)

        categorical_data.append(cat_row)

        # Numerical
        num_row = [
            sa.get("sentiment_polarity", 0.0),
            sa.get("urgency_score", 0.0),
            sa.get("user_effort_score", 0.0),
            jm.get("journey_depth", 0),
            jm.get("retry_count_indicator", 0),
            r.get("relevance_score", 0.0),
            r.get("engagement_score", 0) or 0,
        ]
        numerical_data.append(num_row)

    # Encode categorical features
    cat_array = np.array(categorical_data)
    encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
    cat_encoded = encoder.fit_transform(cat_array)

    # Scale numerical features
    num_array = np.array(numerical_data, dtype=float)
    scaler = StandardScaler()
    num_scaled = scaler.fit_transform(num_array)

    # Combine
    features = np.hstack([cat_encoded, num_scaled])

    print(f"Feature matrix: {features.shape} ({cat_encoded.shape[1]} categorical + {num_scaled.shape[1]} numerical)")

    return features, encoder


def find_optimal_k(features):
    """Find optimal number of clusters using silhouette score."""
    print("\nSearching for optimal K...")
    best_k = 5
    best_score = -1

    scores = {}
    for k in K_RANGE:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10, max_iter=300)
        labels = kmeans.fit_predict(features)
        score = silhouette_score(features, labels, sample_size=min(5000, len(features)))
        scores[k] = round(score, 4)
        print(f"  K={k}: silhouette={score:.4f}")
        if score > best_score:
            best_score = score
            best_k = k

    print(f"  Optimal K={best_k} (silhouette={best_score:.4f})")
    return best_k, scores


def run_clustering(features, k):
    """Run K-Means with optimal K."""
    print(f"\nRunning K-Means with K={k}...")
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10, max_iter=300)
    labels = kmeans.fit_predict(features)
    return labels, kmeans


def generate_segment_profiles(records, labels, k):
    """
    Generate human-readable profiles for each segment.
    Analyzes the dominant characteristics of each cluster.
    """
    segments = {}

    for seg_id in range(k):
        mask = labels == seg_id
        seg_records = [records[i] for i in range(len(records)) if mask[i]]
        seg_size = len(seg_records)

        if seg_size == 0:
            continue

        # Aggregate characteristics
        profile = {
            "size": seg_size,
            "percentage": round(seg_size / len(records) * 100, 1),
            "photo_category": Counter(),
            "search_strategy": Counter(),
            "frustration_level": Counter(),
            "outcome": Counter(),
            "primary_archetype": Counter(),
            "journey_stage": Counter(),
            "sentiment_label": Counter(),
            "avg_polarity": 0.0,
            "avg_urgency": 0.0,
            "avg_effort": 0.0,
            "avg_journey_depth": 0.0,
            "avg_retries": 0.0,
            "sources": Counter(),
            "emotions": Counter(),
        }

        for r in seg_records:
            meta = r.get("metadata", {})
            sa = r.get("sentiment_analysis", {})
            jm = r.get("journey_mapping", {})
            arch = r.get("archetype_classification", {})

            profile["photo_category"][meta.get("photo_category", "unknown")] += 1
            profile["search_strategy"][meta.get("search_strategy_used", "unknown")] += 1
            profile["frustration_level"][meta.get("frustration_level", "unknown")] += 1
            profile["outcome"][meta.get("outcome", "unknown")] += 1
            profile["journey_stage"][jm.get("primary_breakdown_stage", "UNKNOWN")] += 1
            profile["sentiment_label"][sa.get("sentiment_label", "neutral")] += 1
            profile["sources"][r.get("source", "unknown")] += 1

            profile["avg_polarity"] += sa.get("sentiment_polarity", 0)
            profile["avg_urgency"] += sa.get("urgency_score", 0)
            profile["avg_effort"] += sa.get("user_effort_score", 0)
            profile["avg_journey_depth"] += jm.get("journey_depth", 0)
            profile["avg_retries"] += jm.get("retry_count_indicator", 0)

            archetypes = arch.get("archetypes", [])
            if archetypes:
                primary = max(archetypes, key=lambda a: a.get("confidence", 0)).get("code", "NONE")
                profile["primary_archetype"][primary] += 1

            for emotion in sa.get("emotion_signals", {}):
                profile["emotions"][emotion] += 1

        # Compute averages
        profile["avg_polarity"] = round(profile["avg_polarity"] / seg_size, 4)
        profile["avg_urgency"] = round(profile["avg_urgency"] / seg_size, 4)
        profile["avg_effort"] = round(profile["avg_effort"] / seg_size, 4)
        profile["avg_journey_depth"] = round(profile["avg_journey_depth"] / seg_size, 2)
        profile["avg_retries"] = round(profile["avg_retries"] / seg_size, 2)

        # Generate persona label
        persona = generate_persona(profile)

        # Convert counters to dicts with top values
        segments[seg_id] = {
            "persona_label": persona["label"],
            "persona_description": persona["description"],
            "size": profile["size"],
            "percentage": profile["percentage"],
            "dominant_photo_category": dict(profile["photo_category"].most_common(3)),
            "dominant_search_strategy": dict(profile["search_strategy"].most_common(3)),
            "dominant_frustration": dict(profile["frustration_level"].most_common(3)),
            "dominant_outcome": dict(profile["outcome"].most_common(3)),
            "dominant_archetype": dict(profile["primary_archetype"].most_common(3)),
            "dominant_journey_stage": dict(profile["journey_stage"].most_common(3)),
            "dominant_sentiment": dict(profile["sentiment_label"].most_common(3)),
            "dominant_emotions": dict(profile["emotions"].most_common(3)),
            "sources": dict(profile["sources"].most_common()),
            "averages": {
                "sentiment_polarity": profile["avg_polarity"],
                "urgency": profile["avg_urgency"],
                "effort": profile["avg_effort"],
                "journey_depth": profile["avg_journey_depth"],
                "retries": profile["avg_retries"],
            },
        }

    return segments


def generate_persona(profile):
    """
    Generate a human-readable persona label from the segment profile.
    """
    # Determine the dominant characteristics
    top_category = profile["photo_category"].most_common(1)[0][0] if profile["photo_category"] else "general"
    top_frustration = profile["frustration_level"].most_common(1)[0][0] if profile["frustration_level"] else "unknown"
    top_outcome = profile["outcome"].most_common(1)[0][0] if profile["outcome"] else "unknown"
    top_archetype = profile["primary_archetype"].most_common(1)[0][0] if profile["primary_archetype"] else "NONE"
    top_stage = profile["journey_stage"].most_common(1)[0][0] if profile["journey_stage"] else "UNKNOWN"

    # Generate label based on dominant traits
    # Frustration-based prefix
    if top_frustration == "extreme":
        prefix = "Furious"
    elif top_frustration == "high":
        prefix = "Frustrated"
    elif top_frustration == "medium":
        prefix = "Struggling"
    elif top_frustration == "low":
        prefix = "Mild"
    else:
        prefix = "Neutral"

    # Outcome-based middle
    if top_outcome == "not_found":
        middle = "Failed"
    elif top_outcome == "gave_up":
        middle = "Abandoned"
    elif top_outcome == "found":
        middle = "Successful"
    elif top_outcome == "used_workaround":
        middle = "Workaround"
    else:
        middle = "Searching"

    # Category-based suffix
    category_labels = {
        "travel": "Traveler",
        "people": "People-Searcher",
        "document": "Document-Finder",
        "event": "Event-Recaller",
        "screenshot": "Screenshot-Hunter",
        "medical": "Medical-Retriever",
        "receipt": "Receipt-Tracker",
        "food": "Food-Logger",
        "pet": "Pet-Parent",
        "other": "General-User",
        "unknown": "User",
    }
    suffix = category_labels.get(top_category, "User")

    label = f"The {prefix} {middle} {suffix}"

    # Generate description
    archetype_names = {
        "TEMPORAL_DECAY": "time-faded memories",
        "SPATIAL_AMBIGUITY": "vague location recall",
        "KEYWORD_MISMATCH": "search term frustration",
        "CONTEXT_WITHOUT_CONTENT": "contextual memories without content details",
        "PEOPLE_WITHOUT_NAMES": "unnamed people in photos",
        "VISUAL_MEMORY_ONLY": "visual-only recall",
        "ALBUM_FRAGMENTATION": "scattered albums/libraries",
        "VOLUME_OVERWHELM": "too many photos to browse",
        "NONE": "general retrieval difficulty",
    }
    arch_desc = archetype_names.get(top_archetype, "mixed retrieval problems")

    description = (
        f"Primarily searches for {top_category} photos with {top_frustration} frustration. "
        f"Main challenge: {arch_desc}. "
        f"Typically breaks down at the {top_stage.lower()} stage. "
        f"Average urgency: {profile['avg_urgency']:.2f}, "
        f"average journey depth: {profile['avg_journey_depth']:.1f}."
    )

    return {"label": label, "description": description}


def assign_segments_to_records(records, labels, segments):
    """Assign segment info to each record."""
    for i, record in enumerate(records):
        seg_id = int(labels[i])
        if seg_id in segments:
            record["user_segment"] = {
                "segment_id": seg_id,
                "persona_label": segments[seg_id]["persona_label"],
            }
        else:
            record["user_segment"] = {
                "segment_id": seg_id,
                "persona_label": "Unclassified",
            }
    return records


# --- Main ---

def main():
    print("=" * 60)
    print("Phase 6.2: User Segment Clustering")
    print("=" * 60)

    records = load_records()

    # Extract features
    print("\n--- Feature Extraction ---")
    features, encoder = extract_features(records)

    # Find optimal K
    optimal_k, silhouette_scores = find_optimal_k(features)

    # Run clustering
    labels, kmeans = run_clustering(features, optimal_k)

    # Generate segment profiles
    print("\nGenerating segment personas...")
    segments = generate_segment_profiles(records, labels, optimal_k)

    # Assign to records
    records = assign_segments_to_records(records, labels, segments)

    # Save output
    ENRICHED_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(records, f, indent=2)
    print(f"\nSaved segmented data to: {OUTPUT_FILE}")

    # Save report
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "total_records": len(records),
        "num_segments": optimal_k,
        "silhouette_scores": {str(k): v for k, v in silhouette_scores.items()},
        "optimal_k": optimal_k,
        "segments": {str(k): v for k, v in segments.items()},
    }
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print(f"\n{'=' * 60}")
    print("User Segmentation Complete.")
    print(f"{'=' * 60}")
    for seg_id, seg_info in sorted(segments.items()):
        print(f"\n  Segment {seg_id}: {seg_info['persona_label']}")
        print(f"    Size: {seg_info['size']} ({seg_info['percentage']}%)")
        print(f"    {seg_info['persona_description'][:120]}")


if __name__ == "__main__":
    main()
