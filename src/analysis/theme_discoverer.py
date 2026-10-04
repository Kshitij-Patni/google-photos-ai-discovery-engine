"""
Phase 5.3: Emergent Theme Discovery (Data-Driven Clustering)

Uses BGE embeddings + HDBSCAN to discover natural problem clusters from the data,
then uses Gemini to generate human-readable theme labels for each cluster.

This runs ALONGSIDE the predefined archetype classifier — it finds themes
the data reveals that the predefined archetypes might miss.

Pipeline position: runs AFTER journey_mapper
Input:  data/enriched/corpus_journey.json
Output: data/enriched/corpus_themed.json
        reports/emergent_themes_report.json
"""

import json
import os
import sys
import asyncio
import numpy as np
from pathlib import Path
from collections import Counter
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENRICHED_DIR = BASE_DIR / "data" / "enriched"
INPUT_FILE = ENRICHED_DIR / "corpus_journey.json"
OUTPUT_FILE = ENRICHED_DIR / "corpus_themed.json"
REPORT_DIR = BASE_DIR / "reports"
REPORT_FILE = REPORT_DIR / "emergent_themes_report.json"
EMBEDDINGS_CACHE = ENRICHED_DIR / "embeddings_cache.npy"

# Clustering config
MIN_CLUSTER_SIZE = 15      # HDBSCAN: minimum cluster size
MIN_SAMPLES = 5            # HDBSCAN: minimum samples for core point
CLUSTER_SELECTION_METHOD = "eom"  # Excess of Mass


def load_records():
    """Load the input records."""
    if not INPUT_FILE.exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        sys.exit(1)
    with open(INPUT_FILE, "r") as f:
        records = json.load(f)
    print(f"Loaded {len(records)} records.")
    return records


def compute_embeddings(records):
    """
    Compute BGE embeddings for all records.
    Uses cached embeddings if available.
    """
    if EMBEDDINGS_CACHE.exists():
        print("Loading cached embeddings...")
        embeddings = np.load(EMBEDDINGS_CACHE)
        if len(embeddings) == len(records):
            print(f"  Cached embeddings loaded: {embeddings.shape}")
            return embeddings
        else:
            print(f"  Cache size mismatch ({len(embeddings)} vs {len(records)}), recomputing...")

    # Import here to avoid slow import if cache exists
    from src.utils.bge_embedder import BGEEmbedder

    print("Computing BGE embeddings...")
    embedder = BGEEmbedder()

    texts = [r.get("cleaned_text", r.get("raw_text", "")) for r in records]

    # Batch encoding
    batch_size = 64
    all_embeddings = []
    for i in tqdm(range(0, len(texts), batch_size), desc="Embedding"):
        batch = texts[i:i + batch_size]
        batch_embs = embedder.embed_documents(batch)
        all_embeddings.extend(batch_embs)

    embeddings = np.array(all_embeddings, dtype=np.float32)

    # Cache for reuse
    ENRICHED_DIR.mkdir(parents=True, exist_ok=True)
    np.save(EMBEDDINGS_CACHE, embeddings)
    print(f"  Embeddings computed and cached: {embeddings.shape}")

    return embeddings


def run_clustering(embeddings):
    """
    Run HDBSCAN clustering on embeddings.
    Returns cluster labels (int array, -1 = noise).
    """
    import hdbscan

    print(f"\nRunning HDBSCAN clustering (min_cluster_size={MIN_CLUSTER_SIZE})...")

    # UMAP dimensionality reduction for better clustering
    try:
        from sklearn.decomposition import PCA
        print("  Reducing dimensions with PCA (768 → 50)...")
        pca = PCA(n_components=50, random_state=42)
        reduced = pca.fit_transform(embeddings)
        explained = sum(pca.explained_variance_ratio_) * 100
        print(f"  PCA explained variance: {explained:.1f}%")
    except Exception as e:
        print(f"  PCA failed ({e}), using raw embeddings")
        reduced = embeddings

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=MIN_CLUSTER_SIZE,
        min_samples=MIN_SAMPLES,
        cluster_selection_method=CLUSTER_SELECTION_METHOD,
        metric='euclidean',
        core_dist_n_jobs=-1,
    )

    labels = clusterer.fit_predict(reduced)
    probabilities = clusterer.probabilities_

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    noise_count = (labels == -1).sum()
    print(f"  Clusters found: {n_clusters}")
    print(f"  Noise points: {noise_count} ({noise_count / len(labels) * 100:.1f}%)")

    return labels, probabilities


def extract_cluster_representatives(records, labels, embeddings, top_n=10):
    """
    For each cluster, find representative samples:
    - Closest to centroid (most typical)
    - Highest engagement (most visible)
    """
    clusters = {}
    unique_labels = sorted(set(labels))

    for cluster_id in unique_labels:
        if cluster_id == -1:
            continue

        mask = labels == cluster_id
        cluster_indices = np.where(mask)[0]
        cluster_embeddings = embeddings[mask]

        # Centroid
        centroid = cluster_embeddings.mean(axis=0)

        # Distance to centroid
        distances = np.linalg.norm(cluster_embeddings - centroid, axis=1)
        closest_indices = distances.argsort()[:top_n]

        representatives = []
        for idx in closest_indices:
            global_idx = cluster_indices[idx]
            r = records[global_idx]
            representatives.append({
                "id": r.get("id", ""),
                "text": r.get("cleaned_text", r.get("raw_text", ""))[:300],
                "source": r.get("source", ""),
                "distance_to_centroid": float(distances[idx]),
            })

        clusters[int(cluster_id)] = {
            "size": int(mask.sum()),
            "representatives": representatives,
        }

    return clusters


def generate_cluster_labels_local(clusters, records, labels):
    """
    Generate human-readable theme labels using keyword frequency analysis.
    Falls back to this if no API key is available.
    """
    import re
    from collections import Counter

    # Common stop words to exclude
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "dare", "ought",
        "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "up", "about", "into", "through", "during", "before", "after", "above",
        "below", "between", "out", "off", "over", "under", "again", "further",
        "then", "once", "here", "there", "when", "where", "why", "how", "all",
        "both", "each", "few", "more", "most", "other", "some", "such", "no",
        "nor", "not", "only", "own", "same", "so", "than", "too", "very",
        "just", "because", "as", "until", "while", "that", "this", "these",
        "those", "am", "it", "its", "my", "your", "his", "her", "their",
        "what", "which", "who", "whom", "and", "but", "if", "or", "i", "me",
        "we", "you", "he", "she", "they", "them", "him", "us", "our",
        "application", "app", "google", "photos", "photo", "get", "like",
        "one", "also", "even", "still", "much", "well", "back", "know",
        "make", "way", "going", "thing", "things", "really", "think",
        "dont", "doesn", "didn", "won", "wouldn", "ive", "dont", "doesnt",
        "cant", "since", "now", "already",
    }

    labeled_clusters = {}

    for cluster_id, cluster_info in clusters.items():
        # Get all texts in this cluster
        mask = labels == cluster_id
        cluster_indices = np.where(mask)[0]
        cluster_texts = [
            records[i].get("cleaned_text", records[i].get("raw_text", ""))
            for i in cluster_indices
        ]

        # Word frequency in cluster
        word_freq = Counter()
        for text in cluster_texts:
            words = re.findall(r'\b[a-z]{3,}\b', text.lower())
            for w in words:
                if w not in stop_words:
                    word_freq[w] += 1

        # Bigram frequency
        bigram_freq = Counter()
        for text in cluster_texts:
            words = [w for w in re.findall(r'\b[a-z]{3,}\b', text.lower()) if w not in stop_words]
            for i in range(len(words) - 1):
                bigram_freq[f"{words[i]} {words[i+1]}"] += 1

        # Top keywords and bigrams
        top_words = [w for w, _ in word_freq.most_common(15)]
        top_bigrams = [b for b, c in bigram_freq.most_common(10) if c >= 3]

        # Get metadata distribution for the cluster
        meta_dist = {
            "photo_category": Counter(),
            "frustration_level": Counter(),
            "search_strategy": Counter(),
            "outcome": Counter(),
        }
        archetype_dist = Counter()

        for i in cluster_indices:
            r = records[i]
            meta = r.get("metadata", {})
            meta_dist["photo_category"][meta.get("photo_category", "unknown")] += 1
            meta_dist["frustration_level"][meta.get("frustration_level", "unknown")] += 1
            meta_dist["search_strategy"][meta.get("search_strategy_used", "unknown")] += 1
            meta_dist["outcome"][meta.get("outcome", "unknown")] += 1

            for arch in r.get("archetype_classification", {}).get("archetypes", []):
                archetype_dist[arch.get("code", "")] += 1

        # Generate label from keywords
        label_keywords = top_bigrams[:3] if top_bigrams else top_words[:4]
        auto_label = " / ".join(label_keywords).upper() if label_keywords else f"CLUSTER_{cluster_id}"

        labeled_clusters[cluster_id] = {
            "theme_label": auto_label,
            "theme_description": f"Cluster of {cluster_info['size']} records centered around: {', '.join(top_words[:8])}",
            "size": cluster_info["size"],
            "top_keywords": top_words[:15],
            "top_bigrams": top_bigrams[:10],
            "dominant_category": dict(meta_dist["photo_category"].most_common(3)),
            "dominant_frustration": dict(meta_dist["frustration_level"].most_common(3)),
            "dominant_strategy": dict(meta_dist["search_strategy"].most_common(3)),
            "dominant_outcome": dict(meta_dist["outcome"].most_common(3)),
            "dominant_archetypes": dict(archetype_dist.most_common(5)),
            "representatives": cluster_info["representatives"][:5],
        }

    return labeled_clusters


async def generate_cluster_labels_llm(clusters, records, labels):
    """
    Use Gemini to generate human-readable theme labels for each cluster.
    Falls back to local analysis if API unavailable.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("  No GOOGLE_API_KEY — using local keyword analysis for labels.")
        return generate_cluster_labels_local(clusters, records, labels)

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    # First get local analysis as context
    local_labels = generate_cluster_labels_local(clusters, records, labels)

    print(f"  Generating LLM labels for {len(clusters)} clusters...")

    for cluster_id, cluster_info in tqdm(local_labels.items(), desc="Labeling Clusters"):
        # Build prompt with representatives
        sample_texts = "\n".join([
            f"  - \"{rep['text'][:200]}\"" for rep in cluster_info["representatives"][:5]
        ])

        prompt = (
            f"Analyze these user complaints about Google Photos and generate a concise theme label.\n\n"
            f"Top keywords: {', '.join(cluster_info['top_keywords'][:10])}\n"
            f"Top bigrams: {', '.join(cluster_info['top_bigrams'][:5])}\n"
            f"Dominant archetypes: {cluster_info['dominant_archetypes']}\n"
            f"Sample feedback:\n{sample_texts}\n\n"
            f"Return JSON: {{\"theme_label\": \"SHORT_LABEL_WITH_UNDERSCORES\", "
            f"\"theme_description\": \"One sentence describing the core user problem in this cluster.\"}}"
        )

        try:
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model="gemini-2.0-flash-lite",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        response_mime_type="application/json",
                    ),
                ),
                timeout=15.0,
            )
            parsed = json.loads(response.text)
            if "theme_label" in parsed:
                cluster_info["theme_label"] = parsed["theme_label"]
            if "theme_description" in parsed:
                cluster_info["theme_description"] = parsed["theme_description"]
        except asyncio.TimeoutError:
            print(f"  Warning: LLM labeling timed out for cluster {cluster_id}, using local label.")
        except Exception as e:
            print(f"  Warning: LLM labeling failed for cluster {cluster_id}: {str(e)[:100]}")

        await asyncio.sleep(4.5)  # Rate limit

    return local_labels


def compare_with_predefined_archetypes(labeled_clusters, records, labels):
    """
    Compare emergent themes with predefined archetypes to find:
    - Confirmed: themes that match existing archetypes
    - Novel: themes not captured by any archetype
    - Merged: archetypes that cluster together
    """
    predefined = {
        "TEMPORAL_DECAY", "SPATIAL_AMBIGUITY", "KEYWORD_MISMATCH",
        "CONTEXT_WITHOUT_CONTENT", "PEOPLE_WITHOUT_NAMES",
        "VISUAL_MEMORY_ONLY", "ALBUM_FRAGMENTATION", "VOLUME_OVERWHELM",
    }

    comparison = {
        "confirmed_archetypes": [],
        "novel_themes": [],
        "low_coverage_archetypes": [],
    }

    # Track archetype coverage
    archetype_covered_by = {a: [] for a in predefined}

    for cluster_id, info in labeled_clusters.items():
        dominant_archs = info.get("dominant_archetypes", {})
        total_in_cluster = info["size"]

        if dominant_archs:
            top_arch = max(dominant_archs, key=dominant_archs.get)
            top_arch_pct = dominant_archs[top_arch] / total_in_cluster

            if top_arch_pct > 0.3:
                comparison["confirmed_archetypes"].append({
                    "cluster": cluster_id,
                    "theme_label": info["theme_label"],
                    "matches_archetype": top_arch,
                    "coverage": round(top_arch_pct, 3),
                })
                if top_arch in archetype_covered_by:
                    archetype_covered_by[top_arch].append(cluster_id)
            else:
                comparison["novel_themes"].append({
                    "cluster": cluster_id,
                    "theme_label": info["theme_label"],
                    "description": info["theme_description"],
                    "size": total_in_cluster,
                    "closest_archetype": top_arch if dominant_archs else "NONE",
                })
        else:
            comparison["novel_themes"].append({
                "cluster": cluster_id,
                "theme_label": info["theme_label"],
                "description": info["theme_description"],
                "size": total_in_cluster,
                "closest_archetype": "NONE",
            })

    # Check which archetypes have low coverage in clusters
    for arch, covering_clusters in archetype_covered_by.items():
        if not covering_clusters:
            comparison["low_coverage_archetypes"].append(arch)

    return comparison


def assign_themes_to_records(records, labels, labeled_clusters):
    """Assign the emergent theme to each record."""
    for i, record in enumerate(records):
        cluster_id = int(labels[i])
        if cluster_id == -1:
            record["emergent_theme"] = {
                "cluster_id": -1,
                "theme_label": "NOISE",
                "theme_description": "Record did not cluster with any emergent theme.",
            }
        elif cluster_id in labeled_clusters:
            info = labeled_clusters[cluster_id]
            record["emergent_theme"] = {
                "cluster_id": cluster_id,
                "theme_label": info["theme_label"],
                "theme_description": info["theme_description"],
            }
        else:
            record["emergent_theme"] = {
                "cluster_id": cluster_id,
                "theme_label": f"CLUSTER_{cluster_id}",
                "theme_description": "Theme label not generated.",
            }
    return records


# --- Main ---

async def async_main():
    print("=" * 60)
    print("Phase 5.3: Emergent Theme Discovery")
    print("=" * 60)

    records = load_records()

    # Step 1: Compute embeddings
    embeddings = compute_embeddings(records)

    # Step 2: Cluster
    labels, probabilities = run_clustering(embeddings)

    # Step 3: Extract representatives
    clusters = extract_cluster_representatives(records, labels, embeddings)

    # Step 4: Generate labels
    labeled_clusters = await generate_cluster_labels_llm(clusters, records, labels)

    # Step 5: Compare with predefined archetypes
    comparison = compare_with_predefined_archetypes(labeled_clusters, records, labels)

    # Step 6: Assign themes to records
    records = assign_themes_to_records(records, labels, labeled_clusters)

    # Save output
    ENRICHED_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(records, f, indent=2)
    print(f"\nSaved themed data to: {OUTPUT_FILE}")

    # Generate report
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "total_records": len(records),
        "num_clusters": len(labeled_clusters),
        "noise_records": int((labels == -1).sum()),
        "clusters": {str(k): {
            "theme_label": v["theme_label"],
            "theme_description": v["theme_description"],
            "size": v["size"],
            "top_keywords": v["top_keywords"][:10],
            "dominant_archetypes": v["dominant_archetypes"],
            "dominant_frustration": v["dominant_frustration"],
            "dominant_outcome": v["dominant_outcome"],
        } for k, v in labeled_clusters.items()},
        "archetype_comparison": comparison,
    }
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print(f"\n{'=' * 60}")
    print("Emergent Theme Discovery Complete.")
    print(f"{'=' * 60}")
    print(f"Total records:    {len(records)}")
    print(f"Clusters found:   {len(labeled_clusters)}")
    print(f"Noise records:    {int((labels == -1).sum())}")
    print(f"\n--- Discovered Themes ---")
    for cid, info in sorted(labeled_clusters.items(), key=lambda x: x[1]["size"], reverse=True):
        print(f"  [{cid:3d}] {info['theme_label']:40s} (n={info['size']})")
    print(f"\n--- Archetype Comparison ---")
    print(f"  Confirmed archetypes: {len(comparison['confirmed_archetypes'])}")
    print(f"  Novel themes:         {len(comparison['novel_themes'])}")
    print(f"  Low-coverage archetypes: {comparison['low_coverage_archetypes']}")


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
