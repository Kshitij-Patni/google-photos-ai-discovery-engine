"""
Enhanced Pipeline Runner — Orchestrates ALL analysis phases.

Usage:
  # Run only the new analysis phases (5-7) on existing classified data:
  python src/pipeline_runner.py --analysis-only

  # Run the full pipeline from scratch (ingestion → preprocessing → analysis):
  python src/pipeline_runner.py --full-run

  # Run a specific phase:
  python src/pipeline_runner.py --phase sentiment
  python src/pipeline_runner.py --phase journey
  python src/pipeline_runner.py --phase themes
  python src/pipeline_runner.py --phase correlations
  python src/pipeline_runner.py --phase segments
  python src/pipeline_runner.py --phase insights

  # Run from a specific phase onward:
  python src/pipeline_runner.py --from sentiment
"""

import sys
import os
import argparse
import time

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def run_phase(phase_name, module_path, is_async=False):
    """Run a single pipeline phase with timing and error handling."""
    print(f"\n{'━' * 70}")
    print(f"  Starting: {phase_name}")
    print(f"{'━' * 70}\n")

    start = time.time()
    try:
        if is_async:
            import asyncio
            module = __import__(module_path, fromlist=['main', 'async_main'])
            if hasattr(module, 'async_main'):
                asyncio.run(module.async_main())
            elif hasattr(module, 'main'):
                module.main()
        else:
            module = __import__(module_path, fromlist=['main'])
            module.main()

        elapsed = time.time() - start
        print(f"\n✅ {phase_name} completed in {elapsed:.1f}s")
        return True
    except Exception as e:
        elapsed = time.time() - start
        print(f"\n❌ {phase_name} FAILED after {elapsed:.1f}s: {e}")
        import traceback
        traceback.print_exc()
        return False


# Define all pipeline phases in order
PIPELINE_PHASES = {
    # Phase 1-3: Preprocessing (existing)
    "clean": {
        "name": "Phase 1: Text Cleaning",
        "module": "src.preprocessing.cleaner",
        "async": False,
    },
    "dedup": {
        "name": "Phase 2: Deduplication",
        "module": "src.preprocessing.deduplicator",
        "async": False,
    },
    "relevance": {
        "name": "Phase 3: Relevance Classification",
        "module": "src.preprocessing.relevance_classifier",
        "async": False,
    },

    # Phase 4: Core Analysis (existing, now expanded)
    "enrich": {
        "name": "Phase 4.1: Metadata Enrichment (16 fields)",
        "module": "src.analysis.metadata_enricher",
        "async": True,
    },
    "archetypes": {
        "name": "Phase 4.2: Archetype Classification (predefined)",
        "module": "src.analysis.archetype_classifier",
        "async": True,
    },

    # Phase 5: Enhanced Analysis (NEW)
    "sentiment": {
        "name": "Phase 5.1: Sentiment & Emotion Analysis",
        "module": "src.analysis.sentiment_analyzer",
        "async": False,
    },
    "journey": {
        "name": "Phase 5.2: Retrieval Journey Mapping",
        "module": "src.analysis.journey_mapper",
        "async": False,
    },
    "themes": {
        "name": "Phase 5.3: Emergent Theme Discovery",
        "module": "src.analysis.theme_discoverer",
        "async": True,
    },

    # Phase 6: Statistical Analysis (NEW)
    "correlations": {
        "name": "Phase 6.1: Cross-Correlation Engine",
        "module": "src.analysis.correlation_engine",
        "async": False,
    },
    "segments": {
        "name": "Phase 6.2: User Segmentation",
        "module": "src.analysis.user_segmenter",
        "async": False,
    },

    # Phase 7: Synthesis (NEW)
    "insights": {
        "name": "Phase 7: Root Cause Synthesis & Insights",
        "module": "src.analysis.insight_synthesizer",
        "async": False,
    },
    "structured_store": {
        "name": "Phase 8.1: Structured Store Generation",
        "module": "src.rag.structured_store",
        "async": False,
    },
    "vector_store": {
        "name": "Phase 8.2: Semantic Vector Store Generation",
        "module": "src.rag.vector_store",
        "async": False,
    },
    "archetype_report": {
        "name": "Phase 9.1: Archetype Report Generation",
        "module": "src.output.archetype_report",
        "async": False,
    },
    "priority_matrix": {
        "name": "Phase 9.2: Opportunity Matrix Generation",
        "module": "src.output.priority_matrix",
        "async": False,
    },
    "visualizations": {
        "name": "Phase 9.3: Visualizations Generation",
        "module": "src.output.visualizations",
        "async": False,
    },
}

# Phase ordering
PHASE_ORDER = [
    "clean", "dedup", "relevance",
    "enrich", "archetypes",
    "sentiment", "journey", "themes",
    "correlations", "segments",
    "insights",
    "structured_store", "vector_store",
    "archetype_report", "priority_matrix", "visualizations"
]

# New analysis phases only (skip preprocessing & core enrichment)
ANALYSIS_ONLY_PHASES = [
    "sentiment", "journey", "themes",
    "correlations", "segments",
    "insights",
    "structured_store", "vector_store",
    "archetype_report", "priority_matrix", "visualizations"
]


def main():
    parser = argparse.ArgumentParser(description="Google Photos Discovery Engine Pipeline")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--full-run", action="store_true",
                       help="Run the full pipeline from ingestion to insights")
    group.add_argument("--analysis-only", action="store_true",
                       help="Run only the new analysis phases (5-7) on existing classified data")
    group.add_argument("--phase", type=str, choices=PIPELINE_PHASES.keys(),
                       help="Run a specific phase only")
    group.add_argument("--from", dest="from_phase", type=str, choices=PIPELINE_PHASES.keys(),
                       help="Run from a specific phase onward")

    args = parser.parse_args()

    print("=" * 70)
    print("  Google Photos Retrieval Discovery Engine")
    print("  Enhanced Pipeline (11 Analysis Phases)")
    print("=" * 70)

    total_start = time.time()
    results = {}

    if args.full_run:
        phases = PHASE_ORDER
    elif args.analysis_only:
        phases = ANALYSIS_ONLY_PHASES
    elif args.phase:
        phases = [args.phase]
    elif args.from_phase:
        start_idx = PHASE_ORDER.index(args.from_phase)
        phases = PHASE_ORDER[start_idx:]
    else:
        phases = PHASE_ORDER

    print(f"\nPhases to run: {' → '.join(phases)}\n")

    for phase_key in phases:
        phase = PIPELINE_PHASES[phase_key]
        success = run_phase(phase["name"], phase["module"], phase["async"])
        results[phase_key] = success

        if not success:
            print(f"\n⚠️  Phase '{phase_key}' failed. Continue anyway? (y/n) ", end="")
            # In non-interactive mode, continue
            print("Continuing...")

    total_elapsed = time.time() - total_start

    # Final summary
    print(f"\n\n{'=' * 70}")
    print(f"  PIPELINE COMPLETE — {total_elapsed:.1f}s total")
    print(f"{'=' * 70}")
    for phase_key, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status}  {PIPELINE_PHASES[phase_key]['name']}")

    failed = sum(1 for s in results.values() if not s)
    if failed:
        print(f"\n⚠️  {failed} phase(s) failed. Check output above for details.")
    else:
        print(f"\n🎉 All {len(results)} phases completed successfully!")
        print(f"\nOutput files:")
        print(f"  data/enriched/corpus_segmented.json   ← Final enriched dataset")
        print(f"  reports/insight_synthesis_report.json  ← Key insights & root causes")
        print(f"  reports/top_problems_ranked.json       ← Ranked problem list")
        print(f"  reports/factor_importance.json         ← Factor importance rankings")
        print(f"  reports/correlation_report.json        ← Statistical correlations")
        print(f"  reports/user_segments_report.json      ← User segment personas")
        print(f"  reports/emergent_themes_report.json    ← Data-driven themes")
        print(f"  reports/journey_report.json            ← Journey stage analysis")
        print(f"  reports/sentiment_report.json          ← Sentiment analysis")


if __name__ == "__main__":
    main()
