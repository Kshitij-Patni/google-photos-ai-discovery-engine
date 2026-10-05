import sys
import os
import json
import numpy as np
import chromadb
from pathlib import Path
import logging
from collections import defaultdict

# Suppress tokenizer parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add src to path so we can import bge_embedder
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.utils.bge_embedder import BGEEmbedder

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = os.environ.get("CHROMADB_PATH") or str(_PROJECT_ROOT / "data" / "chroma_db")
COLLECTION_NAME = "retrieval_feedback"

def get_chroma_collection(db_path=DB_PATH, name=COLLECTION_NAME):
    client = chromadb.PersistentClient(path=db_path)
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"}
    )

def chunk_and_prepare(records: list, original_embeddings: np.ndarray):
    """Tiered chunking: short -> composite, standard -> 1:1, long -> split."""
    chunks = []
    short_groups = defaultdict(list)
    
    embedder = None 
    def get_embedder():
        nonlocal embedder
        if embedder is None:
            logger.info("Initializing BGE Embedder for Tier 1 and Tier 3 chunks...")
            embedder = BGEEmbedder()
        return embedder

    for i, r in enumerate(records):
        cleaned_text = r.get("cleaned_text", "")
        word_count = len(cleaned_text.split())
        
        # Build metadata (safely handle Nones for ChromaDB)
        md = r.get("metadata", {})
        arch_data = r.get("archetype_classification", {})
        archetypes_list = arch_data.get("archetypes", [])
        primary_archetype = "unknown"
        if archetypes_list:
            arch = archetypes_list[0]
            primary_archetype = arch.get("code", arch.get("archetype", "unknown")) if isinstance(arch, dict) else arch

        sent_data = r.get("sentiment_analysis", {})
        journey_data = r.get("journey_mapping", {})
        
        # Ensure all metadata values are strings, ints, or floats
        chunk_metadata = {
            "source": str(r.get("source", "unknown")),
            "photo_category": str(md.get("photo_category", "unknown")),
            "frustration_level": str(md.get("frustration_level", "unknown")),
            "primary_archetype": str(primary_archetype),
            "outcome": str(md.get("outcome", "unknown")),
            "sentiment_label": str(sent_data.get("sentiment_label", "unknown")),
            "journey_stage": str(journey_data.get("primary_breakdown_stage", "unknown")),
            "rating": float(r.get("rating", -1) or -1)
        }
        
        if word_count < 50:
            # Tier 1
            key = (chunk_metadata["primary_archetype"], chunk_metadata["source"])
            short_groups[key].append({
                "record": r,
                "metadata": chunk_metadata
            })
        elif word_count <= 300:
            # Tier 2 (Standard, use precomputed embedding)
            meta = chunk_metadata.copy()
            meta["chunk_type"] = "individual"
            meta["parent_ids"] = json.dumps([r["id"]])
            
            chunks.append({
                "id": str(r["id"]),
                "text": cleaned_text,
                "embedding": original_embeddings[i].tolist(),
                "metadata": meta
            })
        else:
            # Tier 3 (Long, split into sub-chunks)
            words = cleaned_text.split()
            overlap = 50
            target = 250
            start = 0
            sub_idx = 0
            while start < len(words):
                end = min(start + target, len(words))
                sub_text = " ".join(words[start:end])
                
                meta = chunk_metadata.copy()
                meta["chunk_type"] = "sub_chunk"
                meta["parent_ids"] = json.dumps([r["id"]])
                
                chunks.append({
                    "id": f"{r['id']}_sub_{sub_idx}",
                    "text": sub_text,
                    "embedding": None, # Will compute later
                    "metadata": meta
                })
                
                if end == len(words):
                    break
                start += (target - overlap)
                sub_idx += 1

    # Process Tier 1 groups
    for (archetype, source), group in short_groups.items():
        for i in range(0, len(group), 8):
            batch = group[i:i+8]
            composite_text = " | ".join([item["record"].get("cleaned_text", "") for item in batch])
            
            meta = batch[0]["metadata"].copy()
            meta["chunk_type"] = "composite"
            meta["parent_ids"] = json.dumps([item["record"]["id"] for item in batch])
            
            chunks.append({
                "id": f"composite_{archetype}_{source}_{i//8}",
                "text": composite_text,
                "embedding": None,
                "metadata": meta
            })

    # Find chunks needing embeddings
    needs_embedding = [c for c in chunks if c["embedding"] is None]
    if needs_embedding:
        emb = get_embedder()
        texts = [c["text"] for c in needs_embedding]
        logger.info(f"Computing embeddings for {len(texts)} composite/sub-chunks...")
        # compute in batches
        for i in range(0, len(texts), 64):
            batch_texts = texts[i:i+64]
            new_embs = emb.embed_documents(batch_texts)
            for j, e in enumerate(new_embs):
                needs_embedding[i+j]["embedding"] = e
                
    return chunks

def build_index(enriched_json_path: str, embeddings_cache_path: str, db_path: str = DB_PATH):
    """Builds the ChromaDB vector index from the enriched JSON."""
    logger.info(f"Loading data from {enriched_json_path}...")
    try:
        with open(enriched_json_path, 'r', encoding='utf-8') as f:
            records = json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {enriched_json_path}")
        return
        
    logger.info(f"Loading embeddings from {embeddings_cache_path}...")
    original_embeddings = np.load(embeddings_cache_path)
    
    if len(records) != len(original_embeddings):
        logger.error(f"Length mismatch: {len(records)} records vs {len(original_embeddings)} embeddings")
        return
        
    logger.info("Applying tiered chunking strategy...")
    chunks = chunk_and_prepare(records, original_embeddings)
    
    # Log chunk distribution
    type_counts = defaultdict(int)
    for c in chunks:
        type_counts[c["metadata"]["chunk_type"]] += 1
    logger.info(f"Chunk distribution: {dict(type_counts)}")
    
    collection = get_chroma_collection(db_path)
    
    logger.info(f"Upserting {len(chunks)} chunks into ChromaDB...")
    
    # Batch upsert
    batch_size = 500
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        collection.upsert(
            ids=[c["id"] for c in batch],
            embeddings=[c["embedding"] for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[c["metadata"] for c in batch]
        )
        logger.info(f"Upserted {min(i+batch_size, len(chunks))}/{len(chunks)}")
        
    logger.info("Indexing complete.")

def search_similar(query_text: str, n: int = 10, filters: dict = None, db_path: str = DB_PATH):
    """Semantic search with optional metadata filters."""
    embedder = BGEEmbedder()
    query_embedding = embedder.embed_query(query_text)
    
    collection = get_chroma_collection(db_path)
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n,
        where=filters
    )
    
    return results

def get_by_archetype(archetype: str, n: int = 20, db_path: str = DB_PATH):
    """Retrieve records by archetype."""
    collection = get_chroma_collection(db_path)
    return collection.get(
        where={"primary_archetype": archetype},
        limit=n
    )

def resolve_parent_ids(chunk_metadata: dict) -> list:
    """Trace composite/sub_chunk back to original record IDs."""
    parent_ids_str = chunk_metadata.get("parent_ids", "[]")
    try:
        return json.loads(parent_ids_str)
    except:
        return []

def main():
    build_index("data/enriched/corpus_segmented.json", "data/enriched/embeddings_cache.npy", "data/chroma_db")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build ChromaDB vector store")
    parser.add_argument("--input", default="data/enriched/corpus_segmented.json", help="Path to enriched JSON")
    parser.add_argument("--embeddings", default="data/enriched/embeddings_cache.npy", help="Path to cached embeddings")
    parser.add_argument("--db", default="data/chroma_db", help="Path to output ChromaDB directory")
    parser.add_argument("--build", action="store_true", help="Build the index")
    parser.add_argument("--test", action="store_true", help="Run test queries")
    args = parser.parse_args()
    
    if args.build or (not args.build and not args.test):
        build_index(args.input, args.embeddings, args.db)
        
    if args.test:
        print("\n--- Testing ChromaDB Retrieval ---")
        
        print("\nQuery: 'I forget the exact date I took the photo'")
        results = search_similar("I forget the exact date I took the photo", n=3, db_path=args.db)
        
        for i, (doc, meta, dist) in enumerate(zip(results['documents'][0], results['metadatas'][0], results['distances'][0])):
            print(f"\nResult {i+1} (Dist: {dist:.4f})")
            print(f"Type: {meta['chunk_type']}, Archetype: {meta['primary_archetype']}")
            print(f"Text: {doc[:150]}...")
            print(f"Parent IDs: {resolve_parent_ids(meta)}")
