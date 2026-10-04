import os
import json
from rapidfuzz import fuzz
from src.utils.config_loader import load_config
from tqdm import tqdm

def main():
    print("Starting Deduplication Engine...")
    config = load_config()
    dedup_threshold = config.get('preprocessing', {}).get('fuzzy_dedup_threshold', 90)
    
    processed_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'processed')
    cleaned_corpus_path = os.path.join(processed_dir, 'corpus_cleaned.json')
    deduped_corpus_path = os.path.join(processed_dir, 'corpus_deduped.json')
    
    try:
        with open(cleaned_corpus_path, 'r', encoding='utf-8') as f:
            records = json.load(f)
    except FileNotFoundError:
        print(f"Error: {cleaned_corpus_path} not found. Run cleaner.py first.")
        return

    # 1. Sort records by cleaned_text length (descending) to start with longest, most detailed posts
    records.sort(key=lambda x: len(x.get('cleaned_text', '')), reverse=True)
    
    unique_records = []
    stats = {
        'total': len(records),
        'duplicates_removed': 0,
        'cross_source_duplicates': 0
    }
    
    # 2. Compare against existing unique records
    for record in tqdm(records, desc="Deduplicating"):
        text = record.get('cleaned_text', '')
        if not text:
            continue
            
        is_duplicate = False
        
        # Check against unique records
        for unique_idx, unique_rec in enumerate(unique_records):
            unique_text = unique_rec.get('cleaned_text', '')
            
            # Use ratio for similarity
            similarity = fuzz.ratio(text, unique_text)
            
            if similarity >= dedup_threshold:
                is_duplicate = True
                stats['duplicates_removed'] += 1
                
                # Check cross-source
                if record.get('source') != unique_rec.get('source'):
                    stats['cross_source_duplicates'] += 1
                
                # 3. Retain highest-engagement representative
                rec_engagement = record.get('engagement_score') or 0
                unique_engagement = unique_rec.get('engagement_score') or 0
                
                if rec_engagement > unique_engagement:
                    # Replace the existing unique record with this one since it has higher engagement
                    unique_records[unique_idx] = record
                
                break
                
        if not is_duplicate:
            unique_records.append(record)
            
    with open(deduped_corpus_path, 'w', encoding='utf-8') as f:
        json.dump(unique_records, f, indent=2)
        
    print(f"\nDeduplication Complete.")
    print(f"Total starting records: {stats['total']}")
    print(f"Duplicates removed: {stats['duplicates_removed']}")
    print(f"Cross-source duplicates: {stats['cross_source_duplicates']}")
    print(f"Final unique records: {len(unique_records)}")

if __name__ == "__main__":
    main()
