import os
import json
import logging
import time
from datetime import datetime
from collections import Counter
import praw
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_reddit_instance():
    """Initialize PRAW Reddit instance."""
    client_id = os.getenv('REDDIT_CLIENT_ID')
    client_secret = os.getenv('REDDIT_CLIENT_SECRET')
    user_agent = os.getenv('REDDIT_USER_AGENT', 'google-photos-discovery-engine/1.0')
    
    if not client_id or client_id == 'your-reddit-client-id':
        logger.warning("REDDIT_CLIENT_ID not properly configured in .env. Scraper will fail or return empty.")
        return None
        
    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent
    )

def fetch_reddit_data(reddit, target_subreddits, search_queries, limit_per_query=50) -> list:
    """
    Search Reddit for relevant queries and extract posts + top-level comments.
    """
    if not reddit:
        return []
        
    all_records = {}
    
    for sub_name in target_subreddits:
        logger.info(f"Searching subreddit: r/{sub_name}")
        try:
            subreddit = reddit.subreddit(sub_name)
            
            for query in search_queries:
                logger.info(f"Query: '{query}' in r/{sub_name}")
                search_results = subreddit.search(query, limit=limit_per_query)
                
                for post in search_results:
                    if post.id in all_records:
                        continue
                        
                    # Add post record
                    all_records[post.id] = {
                        'id': f"reddit_post_{post.id}",
                        'source': 'reddit',
                        'raw_text': f"{post.title}\n\n{post.selftext}",
                        'date': datetime.fromtimestamp(post.created_utc).isoformat(),
                        'metadata': {
                            'engagement_score': post.score,
                            'subreddit': sub_name,
                            'type': 'post'
                        }
                    }
                    
                    # Add comment records
                    post.comments.replace_more(limit=0) # Only top-level comments, ignore 'load more'
                    for comment in post.comments:
                        if not hasattr(comment, 'body'):
                            continue
                            
                        # Add comment record
                        all_records[comment.id] = {
                            'id': f"reddit_comment_{comment.id}",
                            'source': 'reddit',
                            'raw_text': comment.body,
                            'date': datetime.fromtimestamp(comment.created_utc).isoformat(),
                            'metadata': {
                                'engagement_score': comment.score,
                                'subreddit': sub_name,
                                'type': 'comment',
                                'parent_id': post.id
                            }
                        }
                        
                time.sleep(1.5) # Rate limit compliance
        except Exception as e:
            logger.error(f"Error scraping r/{sub_name}: {e}")
            
    logger.info(f"Total unique Reddit records collected: {len(all_records)}")
    return list(all_records.values())

def generate_summary(normalized_records: list) -> dict:
    if not normalized_records:
        return {}
        
    dates = [datetime.fromisoformat(r['date']) for r in normalized_records]
    types = [r['metadata']['type'] for r in normalized_records]
    
    summary = {
        "total_count": len(normalized_records),
        "date_range": {
            "start": min(dates).isoformat() if dates else None,
            "end": max(dates).isoformat() if dates else None
        },
        "type_distribution": dict(Counter(types))
    }
    return summary

def main():
    search_queries = [
        "google photos search",
        "google photos can't find",
        "google photos lost photo",
        "find old photo google photos",
        "google photos search not working",
        "remember photo can't find"
    ]

    target_subreddits = [
        "googlephotos", "Google", "Android",
        "photography", "ios", "AskTechnology"
    ]
    
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw', 'reddit')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'reddit_posts.json')
    
    reddit = get_reddit_instance()
    records = fetch_reddit_data(reddit, target_subreddits, search_queries)
    
    summary = generate_summary(records)
    logger.info(f"Summary Statistics:\n{json.dumps(summary, indent=2)}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
        
    logger.info(f"Saved {len(records)} Reddit records to {output_path}")

if __name__ == "__main__":
    main()
