# Google Photos Retrieval Discovery Engine

This project is an AI-powered data pipeline that ingests user feedback from public sources, processes it through AI-powered analysis layers, and produces structured, evidence-grounded insights about photo retrieval failures.

## Setup Instructions

1.  **Clone the repository and set up a virtual environment**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure environment variables**
    Create a `.env` file and fill in your API keys:
    ```env
    GOOGLE_API_KEY=your-gemini-api-key
    YOUTUBE_API_KEY=your-youtube-api-key
    ```

## How to Run the Pipeline

The `src/pipeline_runner.py` acts as the orchestrator for all phases of analysis.

**To run the full pipeline (Ingestion to Insights):**
```bash
python src/pipeline_runner.py --full-run
```

**To run only the analysis phases (skip scraping and cleaning):**
```bash
python src/pipeline_runner.py --analysis-only
```

**To run from a specific phase onward (e.g., from semantic vector store creation):**
```bash
python src/pipeline_runner.py --from vector_store
```

## How to use the Interactive Q&A

A Hybrid Query Engine using a combination of SQL (SQLite) and semantic search (ChromaDB) lets you ask questions in natural language.
```bash
python src/output/interactive_qa.py
```
> Example Queries:
> - "How many total comments are there?"
> - "How many negative comments?"
> - "What do users say about forgetting dates?"

## Summary of Key Findings

1. **Keyword Mismatch and Temporal Decay** dominate the failure archetypes, driving a significant portion of user frustration.
2. Users frequently recall visual cues (people, aesthetics) or loose timelines, but lack the precise text-based keywords expected by the current search implementation.
3. RAG-based analysis uncovered emergent theme clusters mapping to exact retrieval hurdles and highlighted strong negative sentiment in cross-source platforms for these issues.

## Reports & Deliverables

- [Validation Report](reports/validation_report.md)
- [Opportunity Matrix](reports/opportunity_matrix.md)
- [Archetype Report](reports/archetype_report.md)
- [Memory Cue Analysis](reports/memory_cue_analysis.md)
- [Interactive Q&A Script](src/output/interactive_qa.py)
- [Raw Data Checksums](data/raw_data_checksums.txt)

Visualizations:
- [Archetype Distribution](reports/charts/archetype_distribution.html)
- [Theme Clusters UMAP](reports/charts/theme_clusters_umap.html)
- *(Additional charts available in `reports/charts/`)*
