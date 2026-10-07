import sys
from pathlib import Path
from typing import Dict, Any

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.utils.gemini_client import GeminiClient

ROUTER_PROMPT = """
You are a Query Router for a user feedback analysis system.
The system has two databases:
1. SQLite (Structured Store): Best for quantitative questions (how many, distribution, counts, percentage, top frustrations).
2. ChromaDB (Semantic Vector Store): Best for qualitative questions (why, examples of, quotes, describing an experience, what does it feel like).

Your job is to analyze the user's query and classify it into one of three routing decisions:
- "quantitative": If the query only requires counts, aggregations, or structured data (e.g., "How many users complained about albums?", "What is the breakdown of frustration levels?").
- "qualitative": If the query requires fetching textual examples, quotes, or semantic search (e.g., "Why are users frustrated with sharing?", "Give me examples of storage issues.").
- "hybrid": If the query requires BOTH counting and semantic context (e.g., "How many users mentioned X, and what were their main complaints?", "Find the top 3 issues and give examples for each."). Prefer "hybrid" for open-ended 'what do users ... most / commonly / top' questions, since they need both frequencies and real quotes.

You must also extract any obvious filtering parameters mentioned in the query (e.g., archetype, frustration_level).

Valid archetypes: ['ALBUM_FRAGMENTATION', 'CONTEXT_WITHOUT_CONTENT', 'KEYWORD_MISMATCH', 'PEOPLE_WITHOUT_NAMES', 'SPATIAL_AMBIGUITY', 'TEMPORAL_DECAY', 'VISUAL_MEMORY_ONLY', 'VOLUME_OVERWHELM', 'unknown']
Valid frustration levels: ['extreme', 'high', 'medium', 'low', 'unknown']

User Query: {query}
"""

ROUTER_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "routing_decision": {
            "type": "STRING",
            "description": "Must be one of: quantitative, qualitative, hybrid",
            "enum": ["quantitative", "qualitative", "hybrid"]
        },
        "reasoning": {
            "type": "STRING",
            "description": "Brief explanation of why this routing decision was made."
        },
        "extracted_parameters": {
            "type": "OBJECT",
            "description": "Optional parameters extracted from the query to help with filtering.",
            "properties": {
                "archetype": {"type": "STRING"},
                "frustration_level": {"type": "STRING"},
                "keywords": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"}
                }
            }
        }
    },
    "required": ["routing_decision", "reasoning"]
}

class QueryRouter:
    def __init__(self, model_name: str = "gemini-flash-lite-latest"):
        # The user prefers Gemini 3.1 Pro (High), but for fast routing 3.8 flash is okay, 
        # or we can use 3.1-pro if specified.
        self.client = GeminiClient(model_name=model_name, temperature=0.1)

    def route_query(self, query: str) -> Dict[str, Any]:
        prompt = ROUTER_PROMPT.format(query=query)
        result = self.client.generate_json(prompt, schema=ROUTER_SCHEMA)
        
        if not result:
            # Fallback
            return {
                "routing_decision": "hybrid",
                "reasoning": "Fallback due to API error.",
                "extracted_parameters": {}
            }
            
        return result

if __name__ == "__main__":
    import dotenv
    dotenv.load_dotenv()
    
    router = QueryRouter()
    
    test_queries = [
        "How many total negative comments do we have?",
        "Why do users hate the album sharing feature?",
        "What is the breakdown of frustration levels for ALBUM_FRAGMENTATION?",
        "How many users complained about storage limits, and what did they say?",
        "Give me 5 examples of TEMPORAL_DECAY"
    ]
    
    for q in test_queries:
        print(f"\nQuery: {q}")
        res = router.route_query(q)
        print(f"Decision: {res['routing_decision']}")
        print(f"Reasoning: {res['reasoning']}")
        print(f"Params: {res.get('extracted_parameters', {})}")
