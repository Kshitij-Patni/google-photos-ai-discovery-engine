# Example Q&A Sessions

The following are example queries executed using the interactive Q&A loop (`src/output/interactive_qa.py`). The interface utilizes the Gemini API for natural language synthesis, querying the SQLite database for quantitative insights and the ChromaDB vector store for qualitative context. It also supports chat history and metadata filters.

---

## Session 1: General Quantitative & Qualitative Synthesis

**PM (User)**: `How many complaints do we have about people forgetting the exact date they took a photo?`

**Agent (Query Router)**: *Routed as HYBRID. Generating SQL and querying vector DB...*

**Agent (Synthesis)**:
📊 **Answer:**
Based on the database records, there are 217 feedback records explicitly classified under the `KEYWORD_MISMATCH` archetype, which often overlaps with forgetting exact dates. Additionally, semantic searches reveal that users frequently struggle to recall exactly when an event happened.

For example, users state:
*   *"I forget the exact date I took the photo, but I know it was around last Thanksgiving, and I can't just search 'Thanksgiving' to find it easily."* (Source: play_store)
*   *"It's frustrating when you don't remember the exact month. The scroll bar is useless if you're guessing."* (Source: reddit)

---

## Session 2: Follow-up & Chat History

**PM (User)**: `What are the main frustrations for the ALBUM_FRAGMENTATION archetype?`

**Agent (Synthesis)**:
📊 **Answer:**
The `ALBUM_FRAGMENTATION` archetype accounts for 14.5% of total feedback. The primary frustration is the inability to search across multiple albums or nested folders simultaneously. Users complain that Google Photos forces them to remember exactly which album a photo was manually placed in.

**PM (User)**: `How many of those users abandoned the app as a result?` *(Follow-up testing chat history)*

**Agent (Synthesis)**:
📊 **Answer:**
Of the users experiencing `ALBUM_FRAGMENTATION` issues, approximately 28% of them reported an outcome of `gave_up` (abandoning the search or the app temporarily). The data shows this is the second highest abandonment rate across all archetypes, only behind `STORAGE_ANXIETY`.

---

## Session 3: Metadata Filters

**PM (User)**: `/filter source=reddit`
✅ *Filters updated: {'source': 'reddit'}*

**PM (User)**: `What do they complain about regarding search?`

**Agent (Synthesis)**:
📊 **Answer:**
Focusing specifically on Reddit discussions, the primary complaints regarding search center around the lack of boolean operators (AND/OR) and the inability to exclude terms (NOT). Reddit users, who tend to be more power-users, frequently ask for features like:
*   *"Why can't I search for 'dog AND beach NOT 2021'? The AI search is too simple."*
*   *"Trying to find screenshots of recipes but excluding memes is impossible with the current search bar."*

**PM (User)**: `/filter clear`
✅ *Filters cleared.*
