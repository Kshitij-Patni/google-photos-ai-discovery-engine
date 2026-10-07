from src.rag.query_engine import QueryEngine
import asyncio

async def test():
    engine = QueryEngine()
    res = await engine.query("What kinds of old photos do users struggle to retrieve?")
    print(res)

if __name__ == "__main__":
    asyncio.run(test())
