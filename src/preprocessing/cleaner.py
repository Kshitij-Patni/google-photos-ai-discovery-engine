import os
import json
import re
from bs4 import BeautifulSoup
import ftfy
import emoji
from src.utils.config_loader import load_config
from tqdm import tqdm

def load_abbreviations():
    abbrev_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'abbreviations.json')
    try:
        with open(abbrev_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Abbreviations file not found at {abbrev_path}. Using empty dict.")
        return {}

def clean_text(text: str, abbreviations: dict) -> str:
    if not text:
        return ""
    
    # 1. HTML stripping
    text = BeautifulSoup(text, "html.parser").get_text()
    
    # 2. Unicode normalization
    text = ftfy.fix_text(text)
    
    # 3. Emoji conversion
    text = emoji.demojize(text, delimiters=(" :", ": "))
    
    # 4. Abbreviation expansion
    # Use word boundaries to only replace full words
    words = text.split()
    expanded_words = []
    for word in words:
        clean_word = word.lower().strip('.,!?()[]{}"\'')
        if clean_word in abbreviations:
            # Try to preserve original punctuation if possible, but for simplicity we'll just replace the word
            expanded_words.append(abbreviations[clean_word])
        else:
            expanded_words.append(word)
    text = " ".join(expanded_words)
    
    # 5. Whitespace normalization
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def main():
    print("Starting Text Cleaning Pipeline...")
    config = load_config()
    min_word_count = config.get('preprocessing', {}).get('min_word_count', 15)
    
    raw_corpus_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw', 'corpus_raw.json')
    processed_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'processed')
    os.makedirs(processed_dir, exist_ok=True)
    cleaned_corpus_path = os.path.join(processed_dir, 'corpus_cleaned.json')
    
    abbreviations = load_abbreviations()
    
    try:
        with open(raw_corpus_path, 'r', encoding='utf-8') as f:
            records = json.load(f)
    except FileNotFoundError:
        print(f"Error: {raw_corpus_path} not found. Run ingestion first.")
        return

    cleaned_records = []
    stats = {
        'total_raw': len(records),
        'dropped_length': 0,
        'passed': 0
    }
    
    for record in tqdm(records, desc="Cleaning Records"):
        raw_text = record.get('raw_text', '')
        cleaned = clean_text(raw_text, abbreviations)
        
        # 6. Minimum length check
        word_count = len(cleaned.split())
        if word_count < min_word_count:
            stats['dropped_length'] += 1
            continue
            
        # Create a new record with cleaned text
        cleaned_record = record.copy()
        cleaned_record['cleaned_text'] = cleaned
        cleaned_records.append(cleaned_record)
        stats['passed'] += 1
        
    with open(cleaned_corpus_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned_records, f, indent=2)
        
    print(f"\nCleaning Complete.")
    print(f"Total raw records: {stats['total_raw']}")
    print(f"Dropped (length < {min_word_count} words): {stats['dropped_length']}")
    print(f"Cleaned records saved: {stats['passed']}")

if __name__ == "__main__":
    main()
