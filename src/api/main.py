import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import insights, query, data

import time
import logging
import os
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from src.api.limiter import limiter

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Photo Retrieval Discovery Engine API",
    version="1.0.0",
    description="REST API for the AI-Powered Photo Retrieval Discovery Engine"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.middleware("http")
async def log_requests(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"Request: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.4f}s")
    return response

# CORS for Vercel frontend
cors_origins_str = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,https://google-photos-ai-discovery-engine-mu.vercel.app,https://*.vercel.app"
)
origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

# If wildcard is in origins, allow all
if "*" in origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(insights.router, prefix="/api/v1")
app.include_router(query.router, prefix="/api/v1")
app.include_router(data.router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    logger.info("Pre-loading BGEEmbedder and ChromaDB on startup...")
    try:
        from src.rag.vector_store import get_embedder, get_chroma_collection
        get_chroma_collection()
        get_embedder()
        logger.info("Successfully pre-loaded models.")
    except Exception as e:
        logger.error(f"Failed to preload models: {e}")

@app.get("/health")
async def health():
    return {"status": "healthy", "chromadb": "connected"}

@app.get("/debug")
async def debug():
    """Diagnostic endpoint to check path resolution on Railway."""
    import os
    from pathlib import Path
    main_file = Path(__file__).resolve()
    project_root = main_file.parent.parent.parent
    db_path = project_root / "data" / "discovery_engine.db"
    chroma_path = project_root / "data" / "chroma_db"
    embeddings_path = project_root / "data" / "enriched" / "embeddings_cache.npy"

    chroma_count = 0
    chroma_error = None
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(chroma_path))
        col = client.get_or_create_collection("retrieval_feedback")
        chroma_count = col.count()
    except Exception as e:
        chroma_error = str(e)

    return {
        "cwd": os.getcwd(),
        "__file__": str(main_file),
        "project_root": str(project_root),
        "db_path": str(db_path),
        "db_exists": db_path.exists(),
        "db_size_bytes": db_path.stat().st_size if db_path.exists() else 0,
        "data_dir_contents": [str(p.name) for p in (project_root / "data").iterdir()] if (project_root / "data").exists() else [],
        "chroma_path": str(chroma_path),
        "chroma_exists": chroma_path.exists(),
        "chroma_doc_count": chroma_count,
        "chroma_error": chroma_error,
        "embeddings_cache_exists": embeddings_path.exists(),
        "embeddings_cache_size_bytes": embeddings_path.stat().st_size if embeddings_path.exists() else 0,
    }

@app.get("/debug/test")
async def debug_test():
    try:
        from src.rag.query_engine import QueryEngine
        engine = QueryEngine()
        sql_result = ""
        vec_result = ""
        
        try:
            sql_query = engine._generate_sql("Album organization issues", filters=None)
            sql_result = f"Query: {sql_query}"
            from src.rag.structured_store import run_query
            if sql_query:
                res = run_query(sql_query)
                sql_result += f" | Rows: {len(res)}"
        except Exception as e:
            sql_result = f"Error: {e}"
            
        try:
            from src.rag.vector_store import search_similar
            vec = search_similar("Album organization issues", n=2, filters=None)
            vec_result = f"Got {len(vec.get('documents', [[]])[0])} docs"
        except Exception as e:
            vec_result = f"Error: {e}"
            
        return {"sql_test": sql_result, "vec_test": vec_result}
    except Exception as e:
        return {"error": str(e)}
