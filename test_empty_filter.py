from src.rag.query_engine import QueryEngine
engine = QueryEngine()
print(engine.process_query("Album organization issues", filters={}))
