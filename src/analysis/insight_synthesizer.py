"""
Phase 7: Root Cause Synthesis & Insight Report Generator

Takes ALL analysis layers and produces:
  1. Top user problems, ranked by frequency × severity × solvability
  2. Root cause chains: Problem → Why → User Behavior → What Should Happen
  3. Opportunity sizing per problem
  4. Cross-referenced evidence with user quotes + statistics

This is the capstone module that synthesizes all upstream analyses into
actionable product insights for the fellowship project.

Pipeline position: runs LAST (after all other analysis modules)
Input:  data/enriched/corpus_segmented.json
        reports/*.json (all upstream reports)
Output: reports/insight_synthesis_report.json
        reports/top_problems_ranked.json
"""

import json
import sys
import os
import asyncio
from pathlib import Path
from collections import Counter, defaultdict
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENRICHED_DIR = BASE_DIR / "data" / "enriched"
REPORT_DIR = BASE_DIR / "reports"
SYNTHESIS_REPORT = REPORT_DIR / "insight_synthesis_report.json"
RANKED_PROBLEMS = REPORT_DIR / "top_problems_ranked.json"

# Graceful fallback: use best available enriched file
_FALLBACK_INPUTS = [
    ENRICHED_DIR / "corpus_segmented.json",
    ENRICHED_DIR / "corpus_themed.json",
    ENRICHED_DIR / "corpus_journey.json",
    ENRICHED_DIR / "corpus_sentiment.json",
    ENRICHED_DIR / "corpus_classified.json",
]
INPUT_FILE = next((f for f in _FALLBACK_INPUTS if f.exists()), _FALLBACK_INPUTS[0])


def load_records():
    if not INPUT_FILE.exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        sys.exit(1)
    with open(INPUT_FILE, "r") as f:
        records = json.load(f)
    print(f"Loaded {len(records)} fully enriched records.")
    return records


def load_upstream_reports():
    """Load all upstream analysis reports for cross-referencing."""
    reports = {}
    report_files = {
        "archetype_distribution": REPORT_DIR / "archetype_distribution.json",
        "sentiment": REPORT_DIR / "sentiment_report.json",
        "journey": REPORT_DIR / "journey_report.json",
        "emergent_themes": REPORT_DIR / "emergent_themes_report.json",
        "correlations": REPORT_DIR / "correlation_report.json",
        "factor_importance": REPORT_DIR / "factor_importance.json",
        "user_segments": REPORT_DIR / "user_segments_report.json",
    }
    for name, path in report_files.items():
        if path.exists():
            with open(path, "r") as f:
                reports[name] = json.load(f)
            print(f"  Loaded: {name}")
        else:
            print(f"  Missing: {name} (skipping)")
            reports[name] = {}
    return reports


# --- Problem Extraction ---

def extract_problems_from_archetypes(records):
    """
    Extract problem instances from archetype classifications.
    Groups by archetype and computes aggregate metrics.
    """
    problems = defaultdict(lambda: {
        "count": 0,
        "high_frustration_count": 0,
        "extreme_frustration_count": 0,
        "not_found_count": 0,
        "gave_up_count": 0,
        "avg_polarity": 0.0,
        "avg_urgency": 0.0,
        "representative_quotes": [],
        "sources": Counter(),
        "journey_stages": Counter(),
        "segments": Counter(),
    })

    for r in records:
        archetypes = r.get("archetype_classification", {}).get("archetypes", [])
        meta = r.get("metadata", {})
        sa = r.get("sentiment_analysis", {})
        jm = r.get("journey_mapping", {})
        seg = r.get("user_segment", {})

        for arch in archetypes:
            code = arch.get("code", "")
            confidence = arch.get("confidence", 0)
            if not code or confidence < 0.5:
                continue

            p = problems[code]
            p["count"] += 1

            frust = meta.get("frustration_level", "unknown")
            if frust == "high":
                p["high_frustration_count"] += 1
            elif frust == "extreme":
                p["extreme_frustration_count"] += 1

            outcome = meta.get("outcome", "unknown")
            if outcome == "not_found":
                p["not_found_count"] += 1
            elif outcome == "gave_up":
                p["gave_up_count"] += 1

            p["avg_polarity"] += sa.get("sentiment_polarity", 0)
            p["avg_urgency"] += sa.get("urgency_score", 0)
            p["sources"][r.get("source", "unknown")] += 1
            p["journey_stages"][jm.get("primary_breakdown_stage", "UNKNOWN")] += 1
            p["segments"][seg.get("persona_label", "Unknown")] += 1

            # Collect high-confidence, high-effort quotes
            effort = sa.get("user_effort_score", 0)
            if effort > 0.4 and len(p["representative_quotes"]) < 5:
                text = r.get("cleaned_text", r.get("raw_text", ""))
                if len(text) > 50:
                    p["representative_quotes"].append({
                        "text": text[:300],
                        "source": r.get("source", ""),
                        "frustration": frust,
                        "confidence": confidence,
                    })

    return problems


def extract_problems_from_themes(records):
    """Extract problem instances from emergent themes (data-driven)."""
    problems = defaultdict(lambda: {
        "count": 0,
        "high_frustration_count": 0,
        "not_found_count": 0,
        "representative_quotes": [],
        "description": "",
    })

    for r in records:
        theme = r.get("emergent_theme", {})
        label = theme.get("theme_label", "NOISE")
        if label in ("NOISE", "UNKNOWN"):
            continue

        p = problems[label]
        p["count"] += 1
        p["description"] = theme.get("theme_description", "")

        meta = r.get("metadata", {})
        frust = meta.get("frustration_level", "unknown")
        if frust in ("high", "extreme"):
            p["high_frustration_count"] += 1

        if meta.get("outcome") == "not_found":
            p["not_found_count"] += 1

        sa = r.get("sentiment_analysis", {})
        if sa.get("user_effort_score", 0) > 0.4 and len(p["representative_quotes"]) < 3:
            text = r.get("cleaned_text", r.get("raw_text", ""))
            if len(text) > 50:
                p["representative_quotes"].append(text[:250])

    return problems


# --- Scoring & Ranking ---

def score_and_rank_problems(archetype_problems, theme_problems, total_records):
    """
    Score each problem by: frequency × severity × evidence_quality.
    Produces a final ranked list.
    """
    ranked = []

    # Score archetype-based problems
    for code, data in archetype_problems.items():
        if data["count"] < 5:  # Minimum evidence threshold
            continue

        # Finalize averages
        count = data["count"]
        data["avg_polarity"] = round(data["avg_polarity"] / max(count, 1), 4)
        data["avg_urgency"] = round(data["avg_urgency"] / max(count, 1), 4)

        # Frequency score (0-1): how prevalent is this problem?
        frequency = count / total_records

        # Severity score (0-1): how painful is it?
        pain_rate = (data["high_frustration_count"] + data["extreme_frustration_count"] * 2) / max(count, 1)
        failure_rate = (data["not_found_count"] + data["gave_up_count"] * 1.5) / max(count, 1)
        severity = min((pain_rate + failure_rate) / 2, 1.0)

        # Evidence quality (0-1): how well-supported?
        source_diversity = min(len(data["sources"]) / 3, 1.0)  # 3 sources = max
        quote_quality = min(len(data["representative_quotes"]) / 5, 1.0)
        evidence = (source_diversity + quote_quality) / 2

        # Combined score (weighted)
        combined = (frequency * 0.3) + (severity * 0.5) + (evidence * 0.2)

        ranked.append({
            "problem_id": code,
            "problem_type": "predefined_archetype",
            "count": count,
            "frequency_pct": round(frequency * 100, 2),
            "severity_score": round(severity, 4),
            "evidence_score": round(evidence, 4),
            "combined_score": round(combined, 4),
            "avg_sentiment_polarity": data["avg_polarity"],
            "avg_urgency": data["avg_urgency"],
            "failure_rate": round(failure_rate, 4),
            "high_frustration_pct": round(
                (data["high_frustration_count"] + data["extreme_frustration_count"]) / max(count, 1) * 100, 1),
            "top_journey_stages": dict(Counter(data["journey_stages"]).most_common(3)),
            "top_segments": dict(Counter(data["segments"]).most_common(3)),
            "sources": dict(data["sources"]),
            "representative_quotes": data["representative_quotes"][:3],
        })

    # Score theme-based problems (novel discoveries)
    for label, data in theme_problems.items():
        if data["count"] < 10:  # Higher threshold for emergent themes
            continue

        frequency = data["count"] / total_records
        pain_rate = data["high_frustration_count"] / max(data["count"], 1)
        failure_rate = data["not_found_count"] / max(data["count"], 1)
        severity = min((pain_rate + failure_rate) / 2, 1.0)
        evidence = min(len(data["representative_quotes"]) / 3, 1.0)

        combined = (frequency * 0.3) + (severity * 0.5) + (evidence * 0.2)

        ranked.append({
            "problem_id": label,
            "problem_type": "emergent_theme",
            "description": data["description"],
            "count": data["count"],
            "frequency_pct": round(frequency * 100, 2),
            "severity_score": round(severity, 4),
            "evidence_score": round(evidence, 4),
            "combined_score": round(combined, 4),
            "high_frustration_pct": round(pain_rate * 100, 1),
            "failure_rate": round(failure_rate, 4),
            "representative_quotes": data["representative_quotes"][:3],
        })

    # Sort by combined score
    ranked.sort(key=lambda x: x["combined_score"], reverse=True)

    # Add rank
    for i, item in enumerate(ranked, 1):
        item["rank"] = i

    return ranked


# --- Root Cause Chains ---

def generate_root_cause_chains(ranked_problems, upstream_reports):
    """
    For top problems, generate root cause analysis chains:
    Problem → Why it happens → User behavior → What should happen
    """
    # Archetype-specific root cause knowledge
    root_cause_templates = {
        "KEYWORD_MISMATCH": {
            "root_cause": "Users' mental model of their photos differs from Google's labeling/indexing. "
                         "Users search with descriptive, contextual, or emotional terms that don't match "
                         "the system's object-detection based labels.",
            "user_behavior": "Users type natural-language descriptions like 'that café in Goa' but the system "
                           "indexed it as 'restaurant, building, food'. Multiple failed searches lead to "
                           "frustration and eventual abandonment.",
            "ideal_state": "The system should understand contextual and fuzzy queries, bridging the gap "
                          "between how users remember and how photos are indexed.",
        },
        "VOLUME_OVERWHELM": {
            "root_cause": "Users with large libraries (10K+ photos) cannot effectively browse results. "
                         "Search returns too many results, and there's no progressive refinement or "
                         "intelligent grouping to narrow down.",
            "user_behavior": "Users scroll through hundreds or thousands of results manually, or give up "
                           "after the first screen of results. No effective filtering/narrowing tools.",
            "ideal_state": "Results should be intelligently grouped, ranked by likely relevance, "
                          "with progressive refinement options.",
        },
        "ALBUM_FRAGMENTATION": {
            "root_cause": "Photos are scattered across albums, shared libraries, archives, trash, and "
                         "partner accounts. Users don't remember which organizational structure contains "
                         "the target photo.",
            "user_behavior": "Users check multiple albums, shared libraries, and archived sections "
                           "manually. Cross-account and cross-device photos compound the problem.",
            "ideal_state": "Search should span all organizational boundaries by default, with clear "
                          "attribution of where the photo lives.",
        },
        "TEMPORAL_DECAY": {
            "root_cause": "Users remember events but not dates. The timeline-based organization becomes "
                         "useless when temporal memory fades. Old photos (1+ years) are especially "
                         "difficult to locate.",
            "user_behavior": "Users scroll through years of timeline, trying to remember when an event "
                           "happened. They may try date-range searches but can't narrow precisely enough.",
            "ideal_state": "The system should support event-based recall: 'that birthday party' rather "
                          "than requiring date knowledge.",
        },
        "PEOPLE_WITHOUT_NAMES": {
            "root_cause": "Face recognition only works for explicitly tagged faces. Users remember people "
                         "in photos but haven't tagged them, or the face isn't recognized by the system.",
            "user_behavior": "Users search by person name but the person isn't in their face groups. "
                           "They can't search for 'my friend from college' or 'the person in the red shirt'.",
            "ideal_state": "Support relational and descriptive people search beyond tagged face IDs.",
        },
        "SPATIAL_AMBIGUITY": {
            "root_cause": "Users remember a place vaguely ('that beach', 'the restaurant near the hotel') "
                         "but not the exact location name. Location metadata may be missing or inaccurate.",
            "user_behavior": "Users try location searches with vague terms, or browse the map view "
                           "hoping to spot the right cluster.",
            "ideal_state": "Support fuzzy location search with contextual understanding of spatial "
                          "relationships.",
        },
        "VISUAL_MEMORY_ONLY": {
            "root_cause": "Users remember what the photo looks like (colors, composition, setting) but "
                         "have no metadata cues (date, location, people, event).",
            "user_behavior": "Users can't formulate a text search because their memory is purely visual. "
                           "They resort to manual browsing, which is unsustainable with large libraries.",
            "ideal_state": "Support visual/sketch-based search: 'photo with blue water and a red boat'.",
        },
        "CONTEXT_WITHOUT_CONTENT": {
            "root_cause": "Users remember the circumstance (why they took the photo, what was happening) "
                         "but not the actual visual content. The photo might be of a document, receipt, "
                         "or detail that isn't self-descriptive.",
            "user_behavior": "Users can describe the situation but not the photo contents. Text search "
                           "fails because the query describes context, not visual content.",
            "ideal_state": "Support contextual search that connects activities and events to photos.",
        },
    }

    chains = []
    for problem in ranked_problems[:15]:  # Top 15
        pid = problem["problem_id"]
        template = root_cause_templates.get(pid, {})

        chain = {
            "problem_id": pid,
            "rank": problem["rank"],
            "problem_type": problem["problem_type"],
            "frequency_pct": problem["frequency_pct"],
            "severity_score": problem["severity_score"],
            "combined_score": problem["combined_score"],
            "root_cause": template.get("root_cause",
                problem.get("description", "Data-driven theme — root cause to be investigated via user research.")),
            "user_behavior": template.get("user_behavior",
                "Users exhibit this pattern frequently based on clustering analysis."),
            "ideal_state": template.get("ideal_state",
                "To be defined based on user research validation."),
            "evidence": {
                "record_count": problem["count"],
                "high_frustration_pct": problem.get("high_frustration_pct", 0),
                "failure_rate": problem.get("failure_rate", 0),
                "sample_quotes": [
                    q.get("text", q) if isinstance(q, dict) else q
                    for q in problem.get("representative_quotes", [])[:2]
                ],
            },
        }
        chains.append(chain)

    return chains


# --- Opportunity Sizing ---

def compute_opportunity_sizing(ranked_problems, total_records, upstream_reports):
    """
    Estimate the opportunity size for each problem.
    """
    opportunities = []

    for problem in ranked_problems[:10]:
        affected_users_pct = problem["frequency_pct"]
        severity = problem["severity_score"]
        failure_rate = problem.get("failure_rate", 0)

        # Impact score: how many users × how painful × how often they fail
        impact = round(affected_users_pct * severity * (1 + failure_rate), 2)

        # Solvability heuristic (higher = more solvable with AI)
        ai_solvable = {
            "KEYWORD_MISMATCH": 0.9,      # LLM-powered semantic search
            "VOLUME_OVERWHELM": 0.7,       # AI ranking/grouping
            "TEMPORAL_DECAY": 0.8,         # Event detection + AI recall
            "ALBUM_FRAGMENTATION": 0.6,    # Cross-boundary search
            "PEOPLE_WITHOUT_NAMES": 0.7,   # Descriptive people search
            "SPATIAL_AMBIGUITY": 0.7,      # Fuzzy location understanding
            "VISUAL_MEMORY_ONLY": 0.8,     # Multimodal search
            "CONTEXT_WITHOUT_CONTENT": 0.8, # Contextual AI search
        }
        solvability = ai_solvable.get(problem["problem_id"], 0.5)

        opportunities.append({
            "problem_id": problem["problem_id"],
            "rank": problem["rank"],
            "affected_users_pct": affected_users_pct,
            "severity": severity,
            "impact_score": impact,
            "ai_solvability": solvability,
            "opportunity_score": round(impact * solvability, 2),
        })

    # Re-rank by opportunity score
    opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)
    for i, opp in enumerate(opportunities, 1):
        opp["opportunity_rank"] = i

    return opportunities


# --- Key Insight Summaries ---

def generate_key_insights(ranked_problems, root_cause_chains, opportunities,
                          upstream_reports, records):
    """Generate the top-level insight summaries."""
    total = len(records)

    # Overall failure rate
    outcomes = Counter(r.get("metadata", {}).get("outcome", "unknown") for r in records)
    known_outcomes = sum(v for k, v in outcomes.items() if k != "unknown")
    overall_failure_rate = round(
        (outcomes.get("not_found", 0) + outcomes.get("gave_up", 0)) / max(known_outcomes, 1) * 100, 1
    ) if known_outcomes > 0 else None

    # Most affected segment
    segments = upstream_reports.get("user_segments", {}).get("segments", {})
    most_frustrated_segment = None
    worst_polarity = 999
    for sid, seg in segments.items():
        polarity = seg.get("averages", {}).get("sentiment_polarity", 0)
        if polarity < worst_polarity:
            worst_polarity = polarity
            most_frustrated_segment = seg.get("persona_label", f"Segment {sid}")

    # Journey breakdown hotspot
    journey = upstream_reports.get("journey", {})
    journey_dist = journey.get("primary_breakdown_distribution", {})
    top_breakdown_stage = max(journey_dist, key=journey_dist.get) if journey_dist else "Unknown"

    insights = {
        "headline_stats": {
            "total_feedback_analyzed": total,
            "overall_failure_rate_pct": overall_failure_rate,
            "top_problem": ranked_problems[0]["problem_id"] if ranked_problems else "N/A",
            "top_problem_affected_pct": ranked_problems[0]["frequency_pct"] if ranked_problems else 0,
            "most_frustrated_segment": most_frustrated_segment,
            "primary_journey_breakdown": top_breakdown_stage,
        },
        "key_findings": [
            f"The #1 retrieval problem is {ranked_problems[0]['problem_id']} affecting "
            f"{ranked_problems[0]['frequency_pct']}% of feedback, with {ranked_problems[0].get('high_frustration_pct', 0)}% "
            f"reporting high/extreme frustration."
            if ranked_problems else "No problems identified.",

            f"Users most commonly break down at the {top_breakdown_stage} stage of the retrieval journey."
            if top_breakdown_stage != "Unknown" else "Journey stage data unavailable.",

            f"The most frustrated user segment is '{most_frustrated_segment}' "
            f"(avg sentiment: {worst_polarity:.2f})."
            if most_frustrated_segment else "Segment data unavailable.",

            f"Overall, {overall_failure_rate}% of users with known outcomes failed to find their photo."
            if overall_failure_rate else "Outcome data has high unknown rate.",
        ],
        "recommendations_for_user_research": [
            "Validate the top 3 problems through user interviews — do users confirm these as their biggest pain points?",
            f"Focus interviews on the '{most_frustrated_segment}' segment for highest signal.",
            f"Design interview tasks around the {top_breakdown_stage} stage to observe the breakdown live.",
            "Ask users to demonstrate a real retrieval task to uncover workarounds and mental models.",
            "Probe for the gap between what users remember and what they can express as a search query.",
        ],
    }

    return insights


# --- Main ---

def main():
    print("=" * 60)
    print("Phase 7: Root Cause Synthesis & Insight Generation")
    print("=" * 60)

    records = load_records()

    print("\n--- Loading Upstream Reports ---")
    upstream_reports = load_upstream_reports()

    # Extract problems from both sources
    print("\n--- Extracting Problems ---")
    print("  From predefined archetypes...")
    archetype_problems = extract_problems_from_archetypes(records)
    print(f"  Found {len(archetype_problems)} archetype-based problems")

    print("  From emergent themes...")
    theme_problems = extract_problems_from_themes(records)
    print(f"  Found {len(theme_problems)} theme-based problems")

    # Score and rank
    print("\n--- Scoring & Ranking Problems ---")
    ranked = score_and_rank_problems(archetype_problems, theme_problems, len(records))
    print(f"  Ranked {len(ranked)} problems total")

    # Root cause chains
    print("\n--- Generating Root Cause Chains ---")
    chains = generate_root_cause_chains(ranked, upstream_reports)

    # Opportunity sizing
    print("\n--- Computing Opportunity Sizes ---")
    opportunities = compute_opportunity_sizing(ranked, len(records), upstream_reports)

    # Key insights
    print("\n--- Generating Key Insights ---")
    insights = generate_key_insights(ranked, chains, opportunities, upstream_reports, records)

    # Save reports
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    synthesis_report = {
        "key_insights": insights,
        "root_cause_chains": chains,
        "opportunity_sizing": opportunities,
        "methodology": {
            "scoring_formula": "combined = (frequency × 0.3) + (severity × 0.5) + (evidence × 0.2)",
            "severity_components": "frustration_rate + failure_rate, normalized",
            "evidence_components": "source_diversity + quote_quality",
            "total_records_analyzed": len(records),
            "analysis_layers": [
                "text_cleaning", "deduplication", "relevance_classification",
                "metadata_enrichment", "archetype_classification",
                "sentiment_analysis", "journey_mapping",
                "emergent_theme_discovery", "cross_correlation",
                "user_segmentation", "insight_synthesis"
            ],
        },
    }

    with open(SYNTHESIS_REPORT, "w") as f:
        json.dump(synthesis_report, f, indent=2)
    print(f"\nSaved synthesis report to: {SYNTHESIS_REPORT}")

    with open(RANKED_PROBLEMS, "w") as f:
        json.dump(ranked, f, indent=2)
    print(f"Saved ranked problems to: {RANKED_PROBLEMS}")

    # Print summary
    print(f"\n{'=' * 60}")
    print("INSIGHT SYNTHESIS COMPLETE")
    print(f"{'=' * 60}")

    print(f"\n📊 Headline Stats:")
    for k, v in insights["headline_stats"].items():
        print(f"  {k}: {v}")

    print(f"\n🔑 Key Findings:")
    for i, finding in enumerate(insights["key_findings"], 1):
        print(f"  {i}. {finding}")

    print(f"\n🏆 Top 10 Problems (Ranked):")
    for item in ranked[:10]:
        print(f"  #{item['rank']:2d}  {item['problem_id']:30s}  "
              f"n={item['count']:5d}  severity={item['severity_score']:.3f}  "
              f"combined={item['combined_score']:.3f}  [{item['problem_type']}]")

    print(f"\n💡 Top Opportunities (by AI solvability):")
    for opp in opportunities[:5]:
        print(f"  #{opp['opportunity_rank']}  {opp['problem_id']:30s}  "
              f"impact={opp['impact_score']:.2f}  solvability={opp['ai_solvability']:.1f}  "
              f"opportunity={opp['opportunity_score']:.2f}")

    print(f"\n🔬 Recommendations for User Research:")
    for rec in insights["recommendations_for_user_research"]:
        print(f"  • {rec}")


if __name__ == "__main__":
    main()
