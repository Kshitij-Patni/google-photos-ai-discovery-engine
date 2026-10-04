import os
import json
import logging
import time
from datetime import datetime
from collections import Counter
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_youtube_client():
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key or api_key == 'your-youtube-api-key':
        logger.warning("YOUTUBE_API_KEY not configured in .env. Scraper will fail or return empty.")
        return None
    return build('youtube', 'v3', developerKey=api_key)

def search_videos(youtube, queries, max_results_per_query=20) -> dict:
    videos = {}
    for query in queries:
        logger.info(f"Searching YouTube for: '{query}'")
        try:
            request = youtube.search().list(
                part="id,snippet",
                q=query,
                type="video",
                maxResults=max_results_per_query
            )
            response = request.execute()
            
            for item in response.get('items', []):
                vid = item['id']['videoId']
                videos[vid] = item['snippet']['title']
        except Exception as e:
            logger.error(f"Error searching for '{query}': {e}")
            
    return videos

def fetch_youtube_comments(youtube, videos: dict, max_comments_per_video=100) -> list:
    all_records = []
    
    for vid, title in videos.items():
        logger.info(f"Fetching comments for video: {title} ({vid})")
        try:
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=vid,
                maxResults=max_comments_per_video,
                textFormat="plainText"
            )
            response = request.execute()
            
            for item in response.get('items', []):
                comment = item['snippet']['topLevelComment']['snippet']
                record = {
                    'id': f"youtube_{item['id']}",
                    'source': 'youtube',
                    'raw_text': comment['textDisplay'],
                    'date': comment['publishedAt'],
                    'metadata': {
                        'engagement_score': comment['likeCount'],
                        'video_title': title,
                        'video_id': vid
                    }
                }
                all_records.append(record)
                
            time.sleep(0.5) # Rate limiting
        except Exception as e:
            logger.error(f"Error fetching comments for video {vid}: {e}")
            
    logger.info(f"Total YouTube comments collected: {len(all_records)}")
    return all_records

def generate_summary(records: list) -> dict:
    if not records:
        return {}
        
    dates = []
    for r in records:
        try:
            dates.append(datetime.fromisoformat(r['date'].replace('Z', '+00:00')))
        except:
            pass
            
    summary = {
        "total_count": len(records),
        "date_range": {
            "start": min(dates).isoformat() if dates else None,
            "end": max(dates).isoformat() if dates else None
        }
    }
    return summary

def main():
    queries = [
        "google photos search tips",
        "google photos tutorial",
        "find old photos google",
        "google photos smart search"
    ]
    
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw', 'youtube')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'youtube_comments.json')
    
    youtube = get_youtube_client()
    if youtube:
        videos = search_videos(youtube, queries)
        records = fetch_youtube_comments(youtube, videos)
        
        summary = generate_summary(records)
        logger.info(f"Summary Statistics:\n{json.dumps(summary, indent=2)}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Saved {len(records)} YouTube records to {output_path}")

if __name__ == "__main__":
    main()
