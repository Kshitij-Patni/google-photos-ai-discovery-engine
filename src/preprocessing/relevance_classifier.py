"""
Relevance Classifier — Local Zero-Shot Classification

Uses facebook/bart-large-mnli (via HuggingFace transformers) to classify
whether each feedback record is about photo search/retrieval.

This replaces the previous Gemini API-based approach to avoid rate limits
on free-tier API keys. The local model runs entirely on-device, with zero
API calls, zero cost, and no rate limiting.

Pipeline position: cleaner.py → deduplicator.py → relevance_classifier.py
Input:  data/processed/corpus_deduped.json
Output: data/processed/relevant/corpus_relevant.json
        data/processed/excluded/corpus_excluded.json
        data/processed/relevance_report.json
"""

import os
import json
from tqdm import tqdm
from transformers import pipeline
from src.utils.config_loader import load_config


# --- Classification Configuration ---

# Candidate labels for zero-shot classification
RETRIEVAL_LABEL = "searching for, finding, or retrieving photos"
NOT_RETRIEVAL_LABEL = "general complaint about storage, billing, syncing, sharing, or UI design"

CANDIDATE_LABELS = [RETRIEVAL_LABEL, NOT_RETRIEVAL_LABEL]

# Threshold: if P(retrieval_label) >= this, classify as RELEVANT
# If between PARTIAL_THRESHOLD and RELEVANT_THRESHOLD, classify as PARTIALLY_RELEVANT
RELEVANT_THRESHOLD = 0.65
PARTIAL_THRESHOLD = 0.45


def classify_records(records, classifier, batch_size=32):
    """
    Classify a list of records using the zero-shot classification pipeline.

    Args:
        records: List of record dicts with 'cleaned_text' or 'raw_text'.
        classifier: HuggingFace zero-shot-classification pipeline.
        batch_size: Number of records to process per batch.

    Returns:
        Tuple of (relevant_records, excluded_records, stats_dict)
    """
    relevant_records = []
    excluded_records = []

    stats = {
        "total": len(records),
        "RELEVANT": 0,
        "PARTIALLY_RELEVANT": 0,
        "NOT_RELEVANT": 0,
        "failed_classification": 0
    }

    # Process in batches for efficiency
    for i in tqdm(range(0, len(records), batch_size), desc="Classifying Records"):
        batch = records[i:i + batch_size]
        texts = [
            r.get("cleaned_text", r.get("raw_text", ""))
            for r in batch
        ]

        # Skip empty texts
        valid_indices = [j for j, t in enumerate(texts) if t.strip()]
        valid_texts = [texts[j] for j in valid_indices]

        if not valid_texts:
            stats["failed_classification"] += len(batch)
            continue

        try:
            # Run zero-shot classification on the batch
            results = classifier(
                valid_texts,
                candidate_labels=CANDIDATE_LABELS,
                batch_size=min(batch_size, len(valid_texts))
            )

            # If only one result, wrap in list for uniform handling
            if isinstance(results, dict):
                results = [results]

            # Map results back to valid records
            result_map = {}
            for idx, result in zip(valid_indices, results):
                result_map[idx] = result

            for j, record in enumerate(batch):
                if j in result_map:
                    result = result_map[j]

                    # Get score for the retrieval label
                    label_scores = dict(zip(result["labels"], result["scores"]))
                    retrieval_score = label_scores.get(RETRIEVAL_LABEL, 0.0)

                    # Classify based on thresholds
                    if retrieval_score >= RELEVANT_THRESHOLD:
                        classification = "RELEVANT"
                    elif retrieval_score >= PARTIAL_THRESHOLD:
                        classification = "PARTIALLY_RELEVANT"
                    else:
                        classification = "NOT_RELEVANT"

                    record["relevance_classification"] = classification
                    record["relevance_score"] = round(retrieval_score, 4)
                    record["relevance_justification"] = (
                        f"Zero-shot retrieval relevance score: {retrieval_score:.4f}"
                    )

                    if classification in ["RELEVANT", "PARTIALLY_RELEVANT"]:
                        relevant_records.append(record)
                        stats[classification] += 1
                    else:
                        excluded_records.append(record)
                        stats["NOT_RELEVANT"] += 1
                else:
                    # Text was empty or invalid
                    record["relevance_classification"] = "NOT_RELEVANT"
                    record["relevance_score"] = 0.0
                    record["relevance_justification"] = "Empty or invalid text"
                    excluded_records.append(record)
                    stats["failed_classification"] += 1

        except Exception as e:
            print(f"Error processing batch {i // batch_size + 1}: {e}")
            stats["failed_classification"] += len(batch)

    return relevant_records, excluded_records, stats


def main():
    print("Starting Relevance Classification (Local Zero-Shot Model)...")
    print("Model: valhalla/distilbart-mnli-12-1")
    print("=" * 60)

    config = load_config()
    batch_size = config.get('preprocessing', {}).get('classification_batch_size', 32)

    # --- Setup paths ---
    processed_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'processed')
    relevant_dir = os.path.join(processed_dir, 'relevant')
    excluded_dir = os.path.join(processed_dir, 'excluded')

    os.makedirs(relevant_dir, exist_ok=True)
    os.makedirs(excluded_dir, exist_ok=True)

    deduped_corpus_path = os.path.join(processed_dir, 'corpus_deduped.json')
    relevant_corpus_path = os.path.join(relevant_dir, 'corpus_relevant.json')
    excluded_corpus_path = os.path.join(excluded_dir, 'corpus_excluded.json')
    report_path = os.path.join(processed_dir, 'relevance_report.json')

    # --- Load data ---
    try:
        with open(deduped_corpus_path, 'r', encoding='utf-8') as f:
            records = json.load(f)
    except FileNotFoundError:
        print(f"Error: {deduped_corpus_path} not found. Run deduplicator.py first.")
        return

    print(f"Loaded {len(records)} deduplicated records.")
    print(f"Thresholds: RELEVANT >= {RELEVANT_THRESHOLD}, "
          f"PARTIAL >= {PARTIAL_THRESHOLD}")
    print()

    # --- Load model ---
    print("Loading zero-shot classification model...")
    print("(This may take a minute on first run to download the model)")
    classifier = pipeline(
        "zero-shot-classification",
        model="valhalla/distilbart-mnli-12-1",
        device=-1  # CPU; use 0 for GPU
    )
    print("Model loaded successfully!\n")

    # --- Classify ---
    relevant_records, excluded_records, stats = classify_records(
        records, classifier, batch_size=batch_size
    )

    # --- Save outputs ---
    with open(relevant_corpus_path, 'w', encoding='utf-8') as f:
        json.dump(relevant_records, f, indent=2)

    with open(excluded_corpus_path, 'w', encoding='utf-8') as f:
        json.dump(excluded_records, f, indent=2)

    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)

    # --- Summary ---
    print(f"\n{'=' * 60}")
    print(f"Relevance Classification Complete.")
    print(f"{'=' * 60}")
    print(f"Total starting records:  {stats['total']}")
    print(f"RELEVANT:                {stats['RELEVANT']}")
    print(f"PARTIALLY_RELEVANT:      {stats['PARTIALLY_RELEVANT']}")
    print(f"NOT_RELEVANT:            {stats['NOT_RELEVANT']}")
    print(f"Failed to classify:      {stats['failed_classification']}")
    print(f"{'=' * 60}")
    print(f"Pass rate:               "
          f"{(stats['RELEVANT'] + stats['PARTIALLY_RELEVANT']) / max(stats['total'], 1) * 100:.1f}%")
    print(f"\nOutputs saved:")
    print(f"  Relevant:  {relevant_corpus_path}")
    print(f"  Excluded:  {excluded_corpus_path}")
    print(f"  Report:    {report_path}")


if __name__ == "__main__":
    main()
