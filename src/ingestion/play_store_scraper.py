import os
import json
import logging
from datetime import datetime
from collections import Counter
from google_play_scraper import Sort, reviews

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fetch_play_store_reviews(app_id: str, max_reviews: int = 10000) -> list:
    """
    Fetches reviews from the Google Play Store with pagination and rate limiting.
    """
    logger.info(f"Starting to fetch up to {max_reviews} reviews for {app_id}...")
    
    all_reviews = {}
    
    # Fetch NEWEST reviews
    logger.info("Fetching NEWEST reviews...")
    continuation_token = None
    fetched_count = 0
    
    while fetched_count < max_reviews // 2:
        result, continuation_token = reviews(
            app_id,
            lang='en',
            country='us',
            sort=Sort.NEWEST,
            count=199, # Max is usually 200 per page, using 199 to be safe
            continuation_token=continuation_token
        )
        
        for r in result:
            all_reviews[r['reviewId']] = r
            
        fetched_count += len(result)
        logger.info(f"Fetched {len(result)} NEWEST reviews. Total NEWEST: {fetched_count}")
        
        if not continuation_token:
            break
            
    # Fetch MOST_RELEVANT reviews
    logger.info("Fetching MOST_RELEVANT reviews...")
    continuation_token = None
    fetched_count = 0
    
    while fetched_count < max_reviews // 2:
        result, continuation_token = reviews(
            app_id,
            lang='en',
            country='us',
            sort=Sort.MOST_RELEVANT,
            count=199,
            continuation_token=continuation_token
        )
        
        for r in result:
            all_reviews[r['reviewId']] = r
            
        fetched_count += len(result)
        logger.info(f"Fetched {len(result)} MOST_RELEVANT reviews. Total RELEVANT: {fetched_count}")
        
        if not continuation_token:
            break
            
    logger.info(f"Total unique reviews collected: {len(all_reviews)}")
    return list(all_reviews.values())

def normalize_reviews(raw_reviews: list) -> list:
    """
    Normalizes the raw Google Play reviews into a unified schema.
    """
    normalized = []
    
    for r in raw_reviews:
        # Skip empty reviews
        if not r.get('content') or str(r.get('content')).strip() == "":
            continue
            
        record = {
            "id": f"playstore_{r['reviewId']}",
            "source": "google_play_store",
            "raw_text": r['content'],
            "date": r['at'].isoformat() if isinstance(r['at'], datetime) else str(r['at']),
            "metadata": {
                "rating": r.get('score'),
                "engagement_score": r.get('thumbsUpCount', 0),
                "app_version": r.get('reviewCreatedVersion', 'unknown')
            }
        }
        normalized.append(record)
        
    return normalized

def generate_summary(normalized_reviews: list) -> dict:
    """
    Generates summary statistics for the collected reviews.
    """
    if not normalized_reviews:
        return {}
        
    dates = [datetime.fromisoformat(r['date']) for r in normalized_reviews]
    ratings = [r['metadata']['rating'] for r in normalized_reviews]
    
    summary = {
        "total_count": len(normalized_reviews),
        "date_range": {
            "start": min(dates).isoformat() if dates else None,
            "end": max(dates).isoformat() if dates else None
        },
        "rating_distribution": dict(Counter(ratings))
    }
    
    return summary

def main():
    app_id = 'com.google.android.apps.photos'
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw', 'play_store')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'play_store_reviews.json')
    
    # Scrape reviews
    raw_reviews = fetch_play_store_reviews(app_id, max_reviews=10000)
    
    # Normalize to unified schema
    normalized = normalize_reviews(raw_reviews)
    
    # Log summary
    summary = generate_summary(normalized)
    logger.info(f"Summary Statistics:\n{json.dumps(summary, indent=2)}")
    
    # Save to file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(normalized, f, indent=2, ensure_ascii=False)
        
    logger.info(f"Saved {len(normalized)} normalized reviews to {output_path}")
    
    # Validation checkpoint output
    print("\n--- Validation Checkpoint (First 3 records) ---")
    for r in normalized[:3]:
        print(json.dumps(r, indent=2))
        print("-" * 50)

if __name__ == "__main__":
    main()
