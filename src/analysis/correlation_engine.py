"""
Phase 6.1: Cross-Correlation & Factor Importance Engine

Computes statistical correlations, co-occurrence matrices, and factor
importance rankings across ALL enriched dimensions:
  - Archetypes × Frustration
  - Photo category × Outcome
  - Search strategy × Success rate
  - Journey stage × Sentiment
  - Source × Problem type
  - Memory cues × Success
  - Emergent themes × Archetypes

Outputs quantified, ranked insights about which factors matter most.

Pipeline position: runs AFTER theme_discoverer
Input:  data/enriched/corpus_themed.json
Output: reports/correlation_report.json
        reports/factor_importance.json
"""

import json
import sys
import math
from pathlib import Path
from collections import Counter, defaultdict
from itertools import combinations
from tqdm import tqdm

import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENRICHED_DIR = BASE_DIR / "data" / "enriched"
REPORT_DIR = BASE_DIR / "reports"
CORRELATION_REPORT = REPORT_DIR / "correlation_report.json"
FACTOR_REPORT = REPORT_DIR / "factor_importance.json"

# Graceful fallback: use best available enriched file
_FALLBACK_INPUTS = [
    ENRICHED_DIR / "corpus_themed.json",
    ENRICHED_DIR / "corpus_journey.json",
    ENRICHED_DIR / "corpus_sentiment.json",
    ENRICHED_DIR / "corpus_classified.json",
]
INPUT_FILE = next((f for f in _FALLBACK_INPUTS if f.exists()), _FALLBACK_INPUTS[0])


# --- Statistical Utilities ---

def cramers_v(contingency_table):
    """
    Compute Cramér's V for a contingency table (2D dict or list-of-lists).
    Measures association strength between two categorical variables.
    Returns value between 0 (no association) and 1 (perfect association).
    """
    # Convert to numpy array
    if isinstance(contingency_table, dict):
        rows = sorted(contingency_table.keys())
        cols = sorted({c for r in contingency_table.values() for c in r})
        matrix = np.array([
            [contingency_table.get(r, {}).get(c, 0) for c in cols]
            for r in rows
        ], dtype=float)
    else:
        matrix = np.array(contingency_table, dtype=float)

    n = matrix.sum()
    if n == 0:
        return 0.0

    # Chi-squared statistic
    row_sums = matrix.sum(axis=1, keepdims=True)
    col_sums = matrix.sum(axis=0, keepdims=True)
    expected = row_sums * col_sums / n

    # Avoid division by zero
    mask = expected > 0
    chi2 = np.sum((matrix[mask] - expected[mask]) ** 2 / expected[mask])

    r, c = matrix.shape
    phi2 = chi2 / n
    k = min(r, c)

    if k <= 1:
        return 0.0

    # Bias correction
    phi2_corrected = max(0, phi2 - (r - 1) * (c - 1) / (n - 1))
    r_corrected = r - (r - 1) ** 2 / (n - 1)
    c_corrected = c - (c - 1) ** 2 / (n - 1)

    denom = min(r_corrected - 1, c_corrected - 1)
    if denom <= 0:
        return 0.0

    return round(math.sqrt(phi2_corrected / denom), 4)


def build_contingency(records, field_a_fn, field_b_fn, filter_fn=None):
    """
    Build a contingency table (2D counter) from two field extraction functions.
    """
    table = defaultdict(Counter)
    for r in records:
        if filter_fn and not filter_fn(r):
            continue
        a = field_a_fn(r)
        b = field_b_fn(r)
        if a and b and a != "unknown" and b != "unknown":
            table[a][b] += 1
    return dict(table)


def conditional_probability(contingency, target_col):
    """
    Given a contingency table, compute P(target_col | row) for each row.
    """
    probs = {}
    for row, col_counts in contingency.items():
        total = sum(col_counts.values())
        if total > 0:
            probs[row] = round(col_counts.get(target_col, 0) / total, 4)
    return probs


def mutual_information(records, field_a_fn, field_b_fn):
    """
    Compute mutual information between two categorical variables.
    Higher MI = more predictive relationship.
    """
    n = len(records)
    if n == 0:
        return 0.0

    joint = Counter()
    margin_a = Counter()
    margin_b = Counter()

    for r in records:
        a = field_a_fn(r)
        b = field_b_fn(r)
        if a and b and a != "unknown" and b != "unknown":
            joint[(a, b)] += 1
            margin_a[a] += 1
            margin_b[b] += 1

    total = sum(joint.values())
    if total == 0:
        return 0.0

    mi = 0.0
    for (a, b), count in joint.items():
        p_joint = count / total
        p_a = margin_a[a] / total
        p_b = margin_b[b] / total
        if p_joint > 0 and p_a > 0 and p_b > 0:
            mi += p_joint * math.log2(p_joint / (p_a * p_b))

    return round(mi, 4)


# --- Field Extractors ---

def get_archetype_primary(r):
    archs = r.get("archetype_classification", {}).get("archetypes", [])
    if archs:
        return max(archs, key=lambda a: a.get("confidence", 0)).get("code", "NONE")
    return None

def get_all_archetypes(r):
    return [a.get("code") for a in r.get("archetype_classification", {}).get("archetypes", []) if a.get("code")]

def get_photo_category(r):
    return r.get("metadata", {}).get("photo_category")

def get_search_strategy(r):
    return r.get("metadata", {}).get("search_strategy_used")

def get_frustration(r):
    return r.get("metadata", {}).get("frustration_level")

def get_outcome(r):
    return r.get("metadata", {}).get("outcome")

def get_source(r):
    return r.get("source")

def get_sentiment_label(r):
    return r.get("sentiment_analysis", {}).get("sentiment_label")

def get_journey_stage(r):
    return r.get("journey_mapping", {}).get("primary_breakdown_stage")

def get_theme(r):
    return r.get("emergent_theme", {}).get("theme_label")

def get_journey_depth(r):
    depth = r.get("journey_mapping", {}).get("journey_depth", 0)
    if depth <= 1:
        return "shallow"
    elif depth <= 3:
        return "moderate"
    else:
        return "deep"


# --- Analysis Functions ---

def compute_archetype_cooccurrence(records):
    """Which archetypes frequently appear together?"""
    cooccurrence = Counter()
    for r in records:
        archetypes = get_all_archetypes(r)
        if len(archetypes) >= 2:
            for a, b in combinations(sorted(archetypes), 2):
                cooccurrence[(a, b)] += 1

    # Convert to serializable format
    result = [
        {"pair": [a, b], "count": count}
        for (a, b), count in cooccurrence.most_common(20)
    ]
    return result


def compute_success_rates(records):
    """Success rate by different dimensions."""
    dimensions = {
        "by_photo_category": get_photo_category,
        "by_search_strategy": get_search_strategy,
        "by_archetype": get_archetype_primary,
        "by_source": get_source,
        "by_journey_stage": get_journey_stage,
    }

    results = {}
    for dim_name, field_fn in dimensions.items():
        contingency = build_contingency(records, field_fn, get_outcome)
        success_rates = conditional_probability(contingency, "found")
        failure_rates = conditional_probability(contingency, "not_found")

        results[dim_name] = {
            "success_rate": dict(sorted(success_rates.items(), key=lambda x: x[1], reverse=True)),
            "failure_rate": dict(sorted(failure_rates.items(), key=lambda x: x[1], reverse=True)),
            "sample_sizes": {k: sum(v.values()) for k, v in contingency.items()},
        }

    return results


def compute_frustration_correlations(records):
    """What dimensions correlate most with high frustration?"""
    dimensions = {
        "archetype": get_archetype_primary,
        "photo_category": get_photo_category,
        "search_strategy": get_search_strategy,
        "journey_stage": get_journey_stage,
        "source": get_source,
    }

    results = {}
    for dim_name, field_fn in dimensions.items():
        contingency = build_contingency(records, field_fn, get_frustration)
        v = cramers_v(contingency)

        # Also compute P(extreme | value) for each value
        extreme_rates = conditional_probability(contingency, "extreme")
        high_rates = conditional_probability(contingency, "high")

        # Combined high+extreme rate
        combined_high = {}
        for val in set(list(extreme_rates.keys()) + list(high_rates.keys())):
            combined_high[val] = round(extreme_rates.get(val, 0) + high_rates.get(val, 0), 4)

        results[dim_name] = {
            "cramers_v": v,
            "extreme_frustration_rate": dict(sorted(extreme_rates.items(), key=lambda x: x[1], reverse=True)),
            "high_or_extreme_rate": dict(sorted(combined_high.items(), key=lambda x: x[1], reverse=True)),
        }

    return results


def compute_factor_importance(records):
    """
    Rank all factors by how predictive they are of outcome (found vs not_found).
    Uses mutual information as the measure.
    """
    factors = {
        "archetype": get_archetype_primary,
        "photo_category": get_photo_category,
        "search_strategy": get_search_strategy,
        "frustration_level": get_frustration,
        "journey_stage": get_journey_stage,
        "sentiment_label": get_sentiment_label,
        "source": get_source,
        "emergent_theme": get_theme,
        "journey_depth": get_journey_depth,
    }

    importance_scores = {}
    for factor_name, field_fn in factors.items():
        mi = mutual_information(records, field_fn, get_outcome)
        cramers = cramers_v(build_contingency(records, field_fn, get_outcome))
        importance_scores[factor_name] = {
            "mutual_information": mi,
            "cramers_v": cramers,
            "combined_score": round((mi + cramers) / 2, 4),
        }

    # Sort by combined score
    ranked = sorted(importance_scores.items(), key=lambda x: x[1]["combined_score"], reverse=True)
    return [{"factor": k, **v} for k, v in ranked]


def compute_memory_cue_analysis(records):
    """Which memory cues are associated with successful retrieval?"""
    cue_outcomes = defaultdict(Counter)

    for r in records:
        cues = r.get("metadata", {}).get("memory_cues_mentioned", [])
        outcome = get_outcome(r)
        if not outcome or outcome == "unknown":
            continue
        for cue in cues:
            cue_lower = cue.lower().strip()
            if cue_lower:
                cue_outcomes[cue_lower][outcome] += 1

    # Compute success rate per cue (only for cues with sufficient data)
    cue_analysis = []
    for cue, outcomes in cue_outcomes.items():
        total = sum(outcomes.values())
        if total >= 5:  # Minimum sample size
            success_rate = outcomes.get("found", 0) / total
            cue_analysis.append({
                "cue": cue,
                "total_mentions": total,
                "success_rate": round(success_rate, 4),
                "failure_rate": round(outcomes.get("not_found", 0) / total, 4),
                "outcomes": dict(outcomes),
            })

    return sorted(cue_analysis, key=lambda x: x["total_mentions"], reverse=True)


def compute_source_comparison(records):
    """Do different sources (Play Store, Reddit, etc.) report different problems?"""
    source_profiles = defaultdict(lambda: {
        "archetype_dist": Counter(),
        "frustration_dist": Counter(),
        "outcome_dist": Counter(),
        "journey_stage_dist": Counter(),
        "count": 0,
    })

    for r in records:
        source = get_source(r)
        if not source:
            continue

        profile = source_profiles[source]
        profile["count"] += 1

        arch = get_archetype_primary(r)
        if arch:
            profile["archetype_dist"][arch] += 1

        frust = get_frustration(r)
        if frust and frust != "unknown":
            profile["frustration_dist"][frust] += 1

        outcome = get_outcome(r)
        if outcome and outcome != "unknown":
            profile["outcome_dist"][outcome] += 1

        stage = get_journey_stage(r)
        if stage and stage != "UNKNOWN":
            profile["journey_stage_dist"][stage] += 1

    # Normalize to percentages
    result = {}
    for source, profile in source_profiles.items():
        total = profile["count"]
        result[source] = {
            "count": total,
            "top_archetypes": dict(Counter(profile["archetype_dist"]).most_common(5)),
            "frustration_profile": {
                k: round(v / max(sum(profile["frustration_dist"].values()), 1), 3)
                for k, v in profile["frustration_dist"].most_common()
            },
            "outcome_profile": {
                k: round(v / max(sum(profile["outcome_dist"].values()), 1), 3)
                for k, v in profile["outcome_dist"].most_common()
            },
            "journey_stage_profile": {
                k: round(v / max(sum(profile["journey_stage_dist"].values()), 1), 3)
                for k, v in profile["journey_stage_dist"].most_common()
            },
        }

    return result


# --- Main ---

def main():
    print("=" * 60)
    print("Phase 6.1: Cross-Correlation & Factor Importance Engine")
    print("=" * 60)

    if not INPUT_FILE.exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        sys.exit(1)

    with open(INPUT_FILE, "r") as f:
        records = json.load(f)
    print(f"Loaded {len(records)} records.\n")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # --- 1. Archetype Co-occurrence ---
    print("Computing archetype co-occurrence...")
    cooccurrence = compute_archetype_cooccurrence(records)

    # --- 2. Success Rates ---
    print("Computing success rates across dimensions...")
    success_rates = compute_success_rates(records)

    # --- 3. Frustration Correlations ---
    print("Computing frustration correlations...")
    frustration_corr = compute_frustration_correlations(records)

    # --- 4. Memory Cue Analysis ---
    print("Analyzing memory cue effectiveness...")
    cue_analysis = compute_memory_cue_analysis(records)

    # --- 5. Source Comparison ---
    print("Comparing feedback sources...")
    source_comparison = compute_source_comparison(records)

    # --- Save Correlation Report ---
    correlation_report = {
        "archetype_cooccurrence": cooccurrence,
        "success_rates": success_rates,
        "frustration_correlations": frustration_corr,
        "memory_cue_analysis": cue_analysis[:30],  # Top 30
        "source_comparison": source_comparison,
    }

    with open(CORRELATION_REPORT, "w") as f:
        json.dump(correlation_report, f, indent=2)
    print(f"\nSaved correlation report to: {CORRELATION_REPORT}")

    # --- 6. Factor Importance Ranking ---
    print("\nRanking factor importance...")
    factor_importance = compute_factor_importance(records)

    with open(FACTOR_REPORT, "w") as f:
        json.dump(factor_importance, f, indent=2)
    print(f"Saved factor importance to: {FACTOR_REPORT}")

    # --- Print Summary ---
    print(f"\n{'=' * 60}")
    print("Correlation & Factor Analysis Complete.")
    print(f"{'=' * 60}")

    print(f"\n--- Factor Importance Ranking (predicting outcome) ---")
    for item in factor_importance:
        print(f"  {item['factor']:25s}  MI={item['mutual_information']:.4f}  "
              f"V={item['cramers_v']:.4f}  Combined={item['combined_score']:.4f}")

    print(f"\n--- Top Archetype Co-occurrences ---")
    for item in cooccurrence[:5]:
        print(f"  {item['pair'][0]} + {item['pair'][1]}: {item['count']}")

    print(f"\n--- Frustration Hotspots (Cramér's V) ---")
    for dim, data in sorted(frustration_corr.items(), key=lambda x: x[1]["cramers_v"], reverse=True):
        print(f"  {dim:25s}  V={data['cramers_v']:.4f}")


if __name__ == "__main__":
    main()
