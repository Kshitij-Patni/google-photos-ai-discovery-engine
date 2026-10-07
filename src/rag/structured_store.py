import sqlite3
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

import os

# Resolve absolute path: structured_store.py is at src/rag/structured_store.py
# Project root is 3 levels up
import shutil

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_BUNDLED_DB = _PROJECT_ROOT / "data" / "discovery_engine.db"
_ENV_DB = os.environ.get("SQLITE_PATH")

if _ENV_DB:
    env_path = Path(_ENV_DB)
    if not env_path.is_file():
        logger.info(f"Populating empty persistent volume at {env_path} from bundled db...")
        env_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_BUNDLED_DB, env_path)
    DB_PATH = str(env_path)
else:
    DB_PATH = str(_BUNDLED_DB)

def init_db(db_path=DB_PATH):
    """Initializes the SQLite database with the required schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # Core feedback table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        id TEXT PRIMARY KEY,
        source TEXT,
        rating INTEGER,
        date TEXT,
        cleaned_text TEXT,
        word_count INTEGER,
        relevance_classification TEXT,
        relevance_score REAL
    )
    ''')
    
    # Enriched metadata
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS metadata (
        feedback_id TEXT PRIMARY KEY REFERENCES feedback(id),
        photo_category TEXT,
        frustration_level TEXT,
        outcome TEXT,
        search_strategy TEXT,
        memory_cues TEXT,
        memory_gaps TEXT,
        emotional_context TEXT,
        usage_frequency TEXT,
        device_context TEXT,
        sharing_intent TEXT,
        collection_size TEXT,
        time_since_photo TEXT,
        workaround_used TEXT,
        feature_mentioned TEXT
    )
    ''')
    
    # Archetypes
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS archetypes (
        feedback_id TEXT REFERENCES feedback(id),
        archetype TEXT,
        confidence REAL,
        PRIMARY KEY (feedback_id, archetype)
    )
    ''')
    
    # Sentiment
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sentiment (
        feedback_id TEXT PRIMARY KEY REFERENCES feedback(id),
        polarity REAL,
        label TEXT,
        urgency REAL,
        effort REAL,
        anger REAL,
        fear REAL,
        disgust REAL,
        joy REAL
    )
    ''')
    
    # Journey mapping
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS journey (
        feedback_id TEXT PRIMARY KEY REFERENCES feedback(id),
        primary_stage TEXT,
        journey_depth INTEGER,
        retry_count INTEGER
    )
    ''')
    
    # Emergent themes
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS themes (
        feedback_id TEXT PRIMARY KEY REFERENCES feedback(id),
        cluster_id INTEGER,
        theme_label TEXT,
        theme_description TEXT
    )
    ''')
    
    # User segments
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS segments (
        feedback_id TEXT PRIMARY KEY REFERENCES feedback(id),
        segment_id INTEGER,
        persona_label TEXT
    )
    ''')
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_source ON feedback(source);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metadata_frustration ON metadata(frustration_level);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_archetypes_archetype ON archetypes(archetype);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sentiment_label ON sentiment(label);")
    
    conn.commit()
    conn.close()
    logger.info(f"Database initialized at {db_path}")

def build_database(enriched_json_path: str, db_path: str = DB_PATH):
    """Parses the enriched JSON and populates the database."""
    init_db(db_path)
    
    logger.info(f"Loading data from {enriched_json_path}...")
    try:
        with open(enriched_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {enriched_json_path}")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    logger.info(f"Inserting {len(data)} records into database...")
    
    for r in data:
        fid = r.get("id")
        if not fid:
            continue
            
        # 1. feedback
        # calculate word count if not present
        cleaned_text = r.get("cleaned_text", "")
        word_count = r.get("word_count", len(cleaned_text.split()))
        
        cursor.execute('''
        INSERT OR REPLACE INTO feedback 
        (id, source, rating, date, cleaned_text, word_count, relevance_classification, relevance_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            fid,
            r.get("source"),
            r.get("rating"),
            r.get("date"),
            cleaned_text,
            word_count,
            r.get("relevance_classification"),
            r.get("relevance_score")
        ))
        
        # 2. metadata
        md = r.get("metadata", {})
        cursor.execute('''
        INSERT OR REPLACE INTO metadata 
        (feedback_id, photo_category, frustration_level, outcome, search_strategy, memory_cues, memory_gaps,
         emotional_context, usage_frequency, device_context, sharing_intent, collection_size, 
         time_since_photo, workaround_used, feature_mentioned)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            fid,
            md.get("photo_category"),
            md.get("frustration_level"),
            md.get("outcome"),
            md.get("search_strategy_used", md.get("search_strategy")),
            json.dumps(md.get("memory_cues_mentioned", [])),
            json.dumps(md.get("memory_gaps_mentioned", [])),
            md.get("emotional_context"),
            md.get("usage_frequency"),
            md.get("device_context"),
            md.get("sharing_intent"),
            md.get("collection_size"),
            md.get("time_since_photo"),
            md.get("workaround_used"),
            md.get("feature_mentioned")
        ))
        
        # 3. archetypes
        arch_data = r.get("archetype_classification", {})
        archetypes_list = arch_data.get("archetypes", [])
        
        # Clear existing archetypes for this feedback_id to handle updates cleanly
        cursor.execute("DELETE FROM archetypes WHERE feedback_id = ?", (fid,))
        
        for arch in archetypes_list:
            if isinstance(arch, dict):
                a_name = arch.get("code", arch.get("archetype"))
                a_conf = arch.get("confidence_score", arch.get("confidence", 1.0))
            else:
                a_name = arch
                a_conf = 1.0
                
            if a_name:
                cursor.execute('''
                INSERT OR IGNORE INTO archetypes (feedback_id, archetype, confidence)
                VALUES (?, ?, ?)
                ''', (fid, a_name, a_conf))
                
        # 4. sentiment
        sent_data = r.get("sentiment_analysis", {})
        emotion_signals = sent_data.get("emotion_signals", {}) or {}
        cursor.execute('''
        INSERT OR REPLACE INTO sentiment
        (feedback_id, polarity, label, urgency, effort, anger, fear, disgust, joy)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            fid,
            sent_data.get("sentiment_polarity"),
            sent_data.get("sentiment_label"),
            sent_data.get("urgency_score"),
            sent_data.get("user_effort_score"),
            emotion_signals.get("anger"),
            emotion_signals.get("fear"),
            emotion_signals.get("disgust"),
            emotion_signals.get("joy")
        ))
        
        # 5. journey
        journey_data = r.get("journey_mapping", {})
        cursor.execute('''
        INSERT OR REPLACE INTO journey
        (feedback_id, primary_stage, journey_depth, retry_count)
        VALUES (?, ?, ?, ?)
        ''', (
            fid,
            journey_data.get("primary_breakdown_stage"),
            journey_data.get("journey_depth"),
            journey_data.get("retry_count_indicator")
        ))
        
        # 6. themes
        theme_data = r.get("emergent_theme", {})
        cursor.execute('''
        INSERT OR REPLACE INTO themes
        (feedback_id, cluster_id, theme_label, theme_description)
        VALUES (?, ?, ?, ?)
        ''', (
            fid,
            theme_data.get("cluster_id"),
            theme_data.get("theme_label"),
            theme_data.get("theme_description")
        ))
        
        # 7. segments
        seg_data = r.get("user_segment", {})
        cursor.execute('''
        INSERT OR REPLACE INTO segments
        (feedback_id, segment_id, persona_label)
        VALUES (?, ?, ?)
        ''', (
            fid,
            seg_data.get("segment_id"),
            seg_data.get("persona_label")
        ))

    conn.commit()
    conn.close()
    logger.info("Database build complete.")

def run_query(sql: str, params: tuple = (), db_path: str = DB_PATH) -> list:
    """Executes a parameterized SQL query and returns results as dicts."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(sql, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

def get_count(table: str, where_clause: str = None, params: tuple = (), db_path: str = DB_PATH) -> int:
    """Shorthand for COUNT queries."""
    sql = f"SELECT COUNT(*) as count FROM {table}"
    if where_clause:
        sql += f" WHERE {where_clause}"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(sql, params)
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_distribution(table: str, column: str, db_path: str = DB_PATH) -> dict:
    """Returns {value: count} dict for a column."""
    sql = f"SELECT {column}, COUNT(*) as cnt FROM {table} GROUP BY {column} ORDER BY cnt DESC"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(sql)
    results = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return results

def main():
    build_database("data/enriched/corpus_segmented.json", "data/discovery_engine.db")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build SQLite structured store")
    parser.add_argument("--input", default="data/enriched/corpus_segmented.json", help="Path to enriched JSON")
    parser.add_argument("--db", default="data/discovery_engine.db", help="Path to output SQLite DB")
    parser.add_argument("--build", action="store_true", help="Build the database")
    parser.add_argument("--test", action="store_true", help="Run test queries")
    args = parser.parse_args()
    
    if args.build or (not args.build and not args.test):
        build_database(args.input, args.db)
        
    if args.test:
        print("--- Testing Queries ---")
        
        # Total comments
        total = get_count("feedback", db_path=args.db)
        print(f"Total feedback records: {total}")
        
        # Negative comments
        negative = get_count("sentiment", "label = ?", ("negative",), db_path=args.db)
        print(f"Negative comments: {negative}")
        
        # Distribution of outcomes
        outcomes = get_distribution("metadata", "outcome", db_path=args.db)
        print("Outcome distribution:")
        for k, v in outcomes.items():
            print(f"  {k}: {v}")
            
        # Cross-tabulation test
        sql = '''
        SELECT a.archetype, m.frustration_level, COUNT(*) as cnt
        FROM archetypes a JOIN metadata m ON a.feedback_id = m.feedback_id
        GROUP BY a.archetype, m.frustration_level
        ORDER BY cnt DESC
        LIMIT 5
        '''
        results = run_query(sql, db_path=args.db)
        print("Top archetype x frustration level:")
        for r in results:
            print(f"  {r['archetype']} - {r['frustration_level']}: {r['cnt']}")
