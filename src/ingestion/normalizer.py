import os
import json
import logging
import uuid
from glob import glob
from datetime import datetime
from collections import Counter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def validate_and_normalize_record(record: dict) -> dict:
    """
    Ensures every record conforms to the schema and has a valid UUID.
    """
    if 'id' not in record or not record['id']:
        record['id'] = str(uuid.uuid4())
        
    # Ensure standard schema fields exist
    normalized = {
        'id': record.get('id'),
        'source': record.get('source', 'unknown'),
        'raw_text': str(record.get('raw_text', '')),
        'rating': record.get('rating') or record.get('metadata', {}).get('rating'),
        'engagement_score': record.get('engagement_score') or record.get('metadata', {}).get('engagement_score', 0),
        'date': record.get('date', datetime.utcnow().isoformat()),
        'metadata': record.get('metadata', {})
    }
    
    return normalized

def merge_sources(raw_dir: str) -> list:
    """
    Finds all JSON files in the raw directories and merges them.
    """
    merged_corpus = []
    
    # Find all .json files in subdirectories of data/raw
    search_pattern = os.path.join(raw_dir, '*', '*.json')
    json_files = [f for f in glob(search_pattern) if 'corpus_raw.json' not in f and 'ingestion_report.json' not in f]
    
    logger.info(f"Found {len(json_files)} raw data files to merge.")
    
    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for record in data:
                        merged_corpus.append(validate_and_normalize_record(record))
                elif isinstance(data, dict):
                    # Handle case where file might contain a single record dict
                    merged_corpus.append(validate_and_normalize_record(data))
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            
    return merged_corpus

def generate_ingestion_report(corpus: list) -> dict:
    """
    Generates summary statistics for the merged corpus.
    """
    sources = [r['source'] for r in corpus]
    
    dates = []
    for r in corpus:
        try:
            dt = datetime.fromisoformat(r['date'].replace('Z', '+00:00'))
            dt = dt.replace(tzinfo=None)
            dates.append(dt)
        except:
            pass
            
    report = {
        "total_records": len(corpus),
        "by_source": dict(Counter(sources)),
        "date_range": {
            "earliest": min(dates).isoformat() if dates else None,
            "latest": max(dates).isoformat() if dates else None
        },
        "language_distribution": {
            "en": len(corpus), # Language detection happens in Phase 3
            "other": 0
        },
        "generated_at": datetime.utcnow().isoformat()
    }
    
    return report

def main():
    raw_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw')
    corpus_path = os.path.join(raw_dir, 'corpus_raw.json')
    report_path = os.path.join(raw_dir, 'ingestion_report.json')
    
    logger.info("Starting Data Normalization & Merging (Phase 2.7)...")
    
    # Merge
    corpus = merge_sources(raw_dir)
    
    # Report
    report = generate_ingestion_report(corpus)
    logger.info(f"Ingestion Report:\n{json.dumps(report, indent=2)}")
    
    # Save
    with open(corpus_path, 'w', encoding='utf-8') as f:
        json.dump(corpus, f, indent=2, ensure_ascii=False)
        
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        
    logger.info(f"Successfully generated {corpus_path} and {report_path}")

if __name__ == "__main__":
    main()
