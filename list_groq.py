import os, asyncio
from groq import AsyncGroq
from dotenv import load_dotenv
load_dotenv()
async def t():
    c = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
    models = await c.models.list()
    print([m.id for m in models.data])
asyncio.run(t())
