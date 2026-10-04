import os
import json
import logging
import time
import requests
from datetime import datetime
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

def fetch_social_media_posts(queries: list, max_total_tweets: int = 200) -> list:
    """
    Scrape Social Media (X/Twitter) using the Official Twitter API v2.
    Built to respect Free Tier usage limits (15 requests/15 mins, limited monthly cap).
    """
    if not TWITTER_BEARER_TOKEN:
        logger.warning("TWITTER_BEARER_TOKEN not found in .env. Social media scraping is disabled.")
        return []
        
    all_records = []
    
    headers = {
        "Authorization": f"Bearer {TWITTER_BEARER_TOKEN}",
        "User-Agent": "GooglePhotosRetrievalEngine/1.0"
    }

    # Twitter API v2 recent search endpoint (searches last 7 days)
    url = "https://api.twitter.com/2/tweets/search/recent"

    for query in queries:
        if len(all_records) >= max_total_tweets:
            logger.info("Reached maximum requested tweets for free tier run. Stopping.")
            break
            
        logger.info(f"Scraping official Twitter API for query: {query}")
        
        # Max 100 per request, but don't fetch more than we need
        fetch_count = min(100, max_total_tweets - len(all_records))
        # Ensure we request at least 10 (Twitter API minimum limit for max_results)
        fetch_count = max(10, fetch_count)
        
        params = {
            'query': f"{query} -is:retweet",
            'max_results': fetch_count,
            'tweet.fields': 'created_at,public_metrics',
            'expansions': 'author_id',
            'user.fields': 'username'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            
            # Handle rate limits gracefully to avoid burning through free quota
            if response.status_code == 429:
                logger.warning("Twitter API Rate limit exceeded (429). Exiting early to respect free tier limits.")
                break # Exit the loop to avoid waiting 15 mins
                
            response.raise_for_status()
            data = response.json()
            
            if 'data' not in data:
                logger.info(f"No tweets found for query: {query}")
                continue
                
            tweets = data['data']
            users = {u['id']: u['username'] for u in data.get('includes', {}).get('users', [])}
            
            for tweet in tweets:
                author_id = tweet.get('author_id')
                author = users.get(author_id, 'unknown')
                
                metrics = tweet.get('public_metrics', {})
                engagement = metrics.get('like_count', 0) + metrics.get('retweet_count', 0) + metrics.get('reply_count', 0)
                
                record = {
                    'id': f"social_media_{tweet['id']}",
                    'source': 'social_media',
                    'raw_text': tweet['text'],
                    'date': tweet.get('created_at', datetime.utcnow().isoformat()),
                    'metadata': {
                        'engagement_score': engagement,
                        'platform': 'x_twitter',
                        'author': author
                    }
                }
                
                if not any(r['id'] == record['id'] for r in all_records):
                    all_records.append(record)
                    
            # Polite delay between API calls
            time.sleep(3)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error communicating with Twitter API for query '{query}': {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
        except Exception as e:
            logger.error(f"Unexpected error processing query '{query}': {e}")

    logger.info(f"Total unique social media records collected: {len(all_records)}")
    return all_records

def generate_summary(normalized_records: list) -> dict:
    if not normalized_records:
        return {}
        
    dates = []
    for r in normalized_records:
        try:
            if r['date'] and r['date'] != 'unknown':
                d = datetime.fromisoformat(r['date'].replace('Z', '+00:00'))
                dates.append(d)
        except Exception:
            continue
            
    platforms = [r['metadata'].get('platform', 'unknown') for r in normalized_records]
    
    summary = {
        "total_count": len(normalized_records),
        "date_range": {
            "start": min(dates).isoformat() if dates else None,
            "end": max(dates).isoformat() if dates else None
        },
        "platform_distribution": dict(Counter(platforms))
    }
    return summary

def main():
    queries = [
        "\"google photos\" \"can't find\"",
        "\"google photos search\" broken"
    ]
    
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw', 'social_media')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'social_media_posts.json')
    
    records = fetch_social_media_posts(queries)
    
    summary = generate_summary(records)
    if summary:
        logger.info(f"Summary Statistics:\n{json.dumps(summary, indent=2)}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
        
    logger.info(f"Saved {len(records)} Social Media records to {output_path}")

if __name__ == "__main__":
    main()
