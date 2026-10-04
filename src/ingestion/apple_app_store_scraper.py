import os
import json
import logging
import time
import requests
from datetime import datetime
from collections import Counter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fetch_app_store_reviews(app_id: int) -> list:
    """
    Fetches reviews from the Apple App Store using the public RSS feed.
    Queries multiple English-speaking countries to maximize review volume.
    Max 500 reviews per country (10 pages * 50).
    """
    logger.info(f"Starting to fetch reviews for app ID: {app_id} via RSS...")
    
    all_reviews = {}
    countries = ['us', 'gb', 'ca', 'au', 'nz']
    
    for country in countries:
        logger.info(f"Fetching reviews for region: {country.upper()}")
        for page in range(1, 11):
            url = f'https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/sortBy=mostRecent/page={page}/json'
            try:
                res = requests.get(url, timeout=10)
                if res.status_code != 200:
                    logger.warning(f"Failed to fetch page {page} for {country}. Status: {res.status_code}")
                    break
                
                data = res.json()
                entries = data.get('feed', {}).get('entry', [])
                
                # The first entry in page 1 is often metadata about the app itself, skip it if 'author' is missing rating
                for entry in entries:
                    if 'im:rating' not in entry:
                        continue
                        
                    review_id = entry.get('id', {}).get('label', '')
                    if not review_id:
                        continue
                        
                    all_reviews[review_id] = {
                        'id': review_id,
                        'review': entry.get('content', {}).get('label', ''),
                        'rating': int(entry.get('im:rating', {}).get('label', '0')),
                        'version': entry.get('im:version', {}).get('label', 'unknown'),
                        'date': entry.get('updated', {}).get('label', '')
                    }
                    
                time.sleep(1) # Rate limiting
                
            except Exception as e:
                logger.error(f"Error fetching page {page} for {country}: {e}")
                break
                
    logger.info(f"Total unique reviews collected from all regions: {len(all_reviews)}")
    return list(all_reviews.values())

def normalize_reviews(raw_reviews: list) -> list:
    """
    Normalizes the raw App Store reviews into the unified schema.
    """
    normalized = []
    
    for r in raw_reviews:
        if not r.get('review') or str(r.get('review')).strip() == "":
            continue
            
        record = {
            "id": f"appstore_{r['id']}",
            "source": "apple_app_store",
            "raw_text": r['review'],
            "date": r['date'],
            "metadata": {
                "rating": r['rating'],
                "engagement_score": 0, 
                "app_version": r['version']
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
        
    # Attempt to parse ISO dates, fallback to raw string if parsing fails
    dates = []
    for r in normalized_reviews:
        try:
            dates.append(datetime.fromisoformat(r['date'].replace('Z', '+00:00')))
        except:
            pass
            
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
    app_id = 962194608 # Google Photos App Store ID
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw', 'app_store')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'app_store_reviews.json')
    
    # Scrape reviews
    raw_reviews = fetch_app_store_reviews(app_id)
    
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
