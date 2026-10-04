import os
import json
import logging
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fetch_support_threads(queries: list, max_pages_per_query=5) -> list:
    """
    Scrapes Google Photos Help Community threads using BeautifulSoup.
    Note: Google Support heavily uses JS rendering, so a full implementation 
    would likely require Selenium. This is a basic HTML parser for non-JS fallbacks.
    """
    all_records = {}
    base_url = "https://support.google.com/photos/threads"
    
    for query in queries:
        logger.info(f"Searching Support Forums for: '{query}'")
        
        for page in range(1, max_pages_per_query + 1):
            url = f"{base_url}?hl=en&max_results=20&query={query.replace(' ', '+')}"
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                res = requests.get(url, headers=headers, timeout=10)
                if res.status_code != 200:
                    break
                    
                soup = BeautifulSoup(res.text, 'html.parser')
                threads = soup.find_all('a', class_='thread-list-thread')
                
                if not threads:
                    break
                    
                for thread in threads:
                    thread_url = "https://support.google.com" + thread['href']
                    title = thread.find('div', class_='thread-title').text if thread.find('div', class_='thread-title') else "Unknown"
                    thread_id = thread['href'].split('/')[-1]
                    
                    if thread_id in all_records:
                        continue
                        
                    # Fetch individual thread (simplified mock parsing for JS-heavy site)
                    all_records[thread_id] = {
                        'id': f"support_forum_{thread_id}",
                        'source': 'google_support_forums',
                        'raw_text': f"Title: {title}", # In a real selenium scraper, extract full thread body
                        'date': datetime.utcnow().isoformat(), # Timestamp of scraping fallback
                        'metadata': {
                            'engagement_score': 0,
                            'url': thread_url,
                            'has_recommended_answer': False
                        }
                    }
                time.sleep(2) # Rate limit
            except Exception as e:
                logger.error(f"Error fetching support forums: {e}")
                
    logger.info(f"Total Support Forum threads collected: {len(all_records)}")
    return list(all_records.values())

def generate_summary(records: list) -> dict:
    if not records:
        return {}
        
    summary = {
        "total_count": len(records),
        "date_range": {
            "start": records[0]['date'] if records else None,
            "end": records[-1]['date'] if records else None
        }
    }
    return summary

def main():
    queries = [
        "search not working",
        "find old photo",
        "lost photo",
        "facial recognition"
    ]
    
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw', 'support_forums')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'support_threads.json')
    
    records = fetch_support_threads(queries)
    
    summary = generate_summary(records)
    logger.info(f"Summary Statistics:\n{json.dumps(summary, indent=2)}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
        
    logger.info(f"Saved {len(records)} Support Forum records to {output_path}")

if __name__ == "__main__":
    main()
