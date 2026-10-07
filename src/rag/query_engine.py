import sys
from pathlib import Path
import json
import logging
from typing import Dict, Any, List
import dotenv

dotenv.load_dotenv()

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.utils.gemini_client import GeminiClient
from src.rag.query_router import QueryRouter
from src.rag.structured_store import run_query
from src.rag.vector_store import search_similar, resolve_parent_ids

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

SCHEMA_CONTEXT = """
SQLite Schema for `data/discovery_engine.db`:

Table: feedback
- id (TEXT PRIMARY KEY)
- source (TEXT)
- rating (INTEGER)
- date (TEXT)
- cleaned_text (TEXT)
- word_count (INTEGER)

Table: metadata
- feedback_id (TEXT PRIMARY KEY REFERENCES feedback(id))
- photo_category (TEXT)
- frustration_level (TEXT) ['high', 'medium', 'low', 'unknown']
- outcome (TEXT) ['found', 'not_found', 'gave_up', 'used_workaround', 'unknown']

Table: archetypes
- feedback_id (TEXT REFERENCES feedback(id))
- archetype (TEXT) ['ALBUM_FRAGMENTATION', 'SHARE_FRICTION', 'VOLUME_OVERWHELM', 'STORAGE_ANXIETY', 'TEMPORAL_DECAY', 'SOCIAL_PRESSURE', 'unknown']
- confidence (REAL)

Table: sentiment
- feedback_id (TEXT PRIMARY KEY REFERENCES feedback(id))
- label (TEXT) ['negative', 'neutral', 'positive']
- polarity (REAL)
"""

SQL_GENERATOR_PROMPT = """
You are an expert SQL generator for a user feedback database.
Below is the SQLite schema:
{schema}

User Query: {query}

Generate a valid, read-only SQLite SELECT query to answer the user's question. 
Return ONLY the raw SQL query string, with no markdown formatting or explanations.
"""

SYNTHESIS_PROMPT = """
You are a UX Researcher analyzing user feedback for Google Photos.

=== Conversation History ===
{chat_history}

You have been asked the following question:
{query}

To help you answer, we queried our databases and retrieved the following context:

=== Quantitative Data (SQL Results) ===
{sql_context}

=== Qualitative Data (Semantic Search Results) ===
{semantic_context}

Synthesize a comprehensive, professional, and clear response. 
- Answer quantitative questions using exact numbers if provided.
- Answer qualitative questions using examples and insights.
- If the question requires both, blend the numbers with the quotes.
- Always cite your sources by referencing the quote if you use qualitative data.

Response format: Markdown.
"""

class SQLGenerator:
    def __init__(self, model_name: str = "gemini-flash-lite-latest"):
        self.client = GeminiClient(model_name=model_name, temperature=0.0)
        
    def generate_sql(self, query: str) -> str:
        prompt = SQL_GENERATOR_PROMPT.format(schema=SCHEMA_CONTEXT, query=query)
        # We can't use generate_json since we want a raw string
        # Let's use a simple text generation if available, but GeminiClient only has generate_json.
        # We'll update the prompt to ask for JSON.
        pass

class QueryEngine:
    def __init__(self):
        self.router = QueryRouter()
        self.sql_client = GeminiClient(model_name="gemini-flash-lite-latest", temperature=0.0)
        self.synthesis_client = GeminiClient(model_name="gemini-flash-lite-latest", temperature=0.3)
        
    def _generate_sql(self, query: str, filters: dict = None) -> str:
        schema = {
            "type": "OBJECT",
            "properties": {
                "sql_query": {"type": "STRING"}
            },
            "required": ["sql_query"]
        }
        filter_str = f"\nApply these metadata filters: {json.dumps(filters)}" if filters else ""
        prompt = SQL_GENERATOR_PROMPT.format(schema=SCHEMA_CONTEXT, query=query + filter_str)
        prompt += "\nOutput a JSON object with a single key 'sql_query' containing the query."
        
        result = self.sql_client.generate_json(prompt, schema=schema)
        if result and "sql_query" in result:
            sql_query = result["sql_query"]
            # Strip markdown code blocks if the model wrapped it
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
            return sql_query
        return ""

    def process_query(self, query: str, chat_history: str = "None", filters: dict = None) -> str:
        logger.info(f"\n[Engine] Routing query...")
        # Include chat history in the router prompt to handle follow-ups properly
        route_info = self.router.route_query(f"Chat History: {chat_history}\n\nQuery: {query}")
        decision = route_info.get("routing_decision", "hybrid").lower()
        logger.info(f"[Engine] Decision: {decision.upper()} ({route_info.get('reasoning')})")
        
        sql_context = "No quantitative data queried."
        semantic_context = "No qualitative data queried."
        
        if decision in ["quantitative", "hybrid"]:
            logger.info("[Engine] Generating SQL...")
            sql = self._generate_sql(query, filters=filters)
            logger.info(f"[Engine] Executing SQL: {sql}")
            try:
                sql_results = run_query(sql)
                sql_context = json.dumps(sql_results, indent=2)
            except Exception as e:
                logger.error(f"[Engine] SQL Error: {e}")
                sql_context = f"Error executing SQL: {e}"
                
        if decision in ["qualitative", "hybrid"]:
            logger.info("[Engine] Searching vector store...")
            try:
                vec_results = search_similar(query, n=5, filters=filters)
                # Format vector results
                formatted_results = []
                for doc, meta in zip(vec_results['documents'][0], vec_results['metadatas'][0]):
                    formatted_results.append({
                        "text": doc,
                        "archetype": meta.get("primary_archetype"),
                        "frustration": meta.get("frustration_level")
                    })
                semantic_context = json.dumps(formatted_results, indent=2)
            except Exception as e:
                logger.error(f"[Engine] ChromaDB Error: {e}")
                semantic_context = f"Error retrieving semantic context: {e}"
                
        logger.info("[Engine] Synthesizing final response...")
        prompt = SYNTHESIS_PROMPT.format(
            query=query,
            chat_history=chat_history,
            sql_context=sql_context,
            semantic_context=semantic_context
        )
        
        # We need a text response, but GeminiClient only has generate_json. 
        # I'll update the schema to request a 'response' field.
        schema = {
            "type": "OBJECT",
            "properties": {
                "response": {"type": "STRING"}
            },
            "required": ["response"]
        }
        
        result = self.synthesis_client.generate_json(prompt, schema=schema)
        if result and "response" in result:
            return result["response"]
        return "Failed to synthesize response."

def interactive_cli():
    print("=====================================================")
    print("🔍 Google Photos Discovery Engine — Interactive Query")
    print("=====================================================")
    print("Type your question (or 'quit' to exit):")
    
    engine = QueryEngine()
    
    while True:
        try:
            query = input("\n> ")
            if query.lower() in ['quit', 'exit', 'q']:
                break
            
            if not query.strip():
                continue
                
            response = engine.process_query(query)
            print("\n" + "="*50)
            print(response)
            print("="*50)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", type=str, help="Single query to run")
    args = parser.parse_args()
    
    if args.query:
        engine = QueryEngine()
        print(engine.process_query(args.query))
    else:
        interactive_cli()
