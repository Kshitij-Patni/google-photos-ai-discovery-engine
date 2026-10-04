import json, os, asyncio
from groq import AsyncGroq

async def test():
    client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
    prompt = """Analyze each user feedback item about Google Photos search/retrieval and classify it into one or more problem archetypes.

Archetypes (select ALL that apply, with confidence 0.0-1.0):
- TEMPORAL_DECAY: User remembers the event but not when it happened
- SPATIAL_AMBIGUITY: User remembers a place vaguely but not precisely
- KEYWORD_MISMATCH: User's search terms don't match system's indexing/labels
- CONTEXT_WITHOUT_CONTENT: User remembers the context but not what the photo shows
- PEOPLE_WITHOUT_NAMES: User remembers people but they aren't tagged/identifiable
- VISUAL_MEMORY_ONLY: User remembers visual appearance but no metadata
- ALBUM_FRAGMENTATION: Photo is lost across albums, shared libraries, or archives
- VOLUME_OVERWHELM: Too many photos to browse manually

Return ONLY a JSON object with a key "data", an array of objects matching this exact structure:
{
  "archetypes": [
    {"code": "ARCHETYPE_CODE", "confidence": 0.85}
  ],
  "reasoning": "Brief explanation"
}

--- Item 1 ---
Feedback: "I know I have a picture of this but I cant find it"
Meta: Cat: unknown, Strat: keyword_search
"""
    res = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    print(res.choices[0].message.content)

asyncio.run(test())
