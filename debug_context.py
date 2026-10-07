import asyncio
from src.rag.query_engine import QueryEngine
from src.rag.vector_store import search_similar

async def run():
    engine = QueryEngine()
    q = "What kinds of old photos do users struggle to retrieve?"
    rewritten = engine._rewrite_for_retrieval(q)
    print(f"Rewritten: {rewritten}")
    vec = search_similar(rewritten, n=8)
    for i, doc in enumerate(vec['documents'][0]):
        print(f"Doc {i}: {doc}")

if __name__ == "__main__":
    asyncio.run(run())
