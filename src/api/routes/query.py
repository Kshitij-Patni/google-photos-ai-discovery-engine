from fastapi import APIRouter, Request
from src.api.schemas import QueryRequest, QueryResponse
from src.api.limiter import limiter
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Lazy-initialize the engine to avoid crashing startup if dependencies are missing
_engine = None

def get_engine():
    global _engine
    if _engine is None:
        try:
            from src.rag.query_engine import QueryEngine
            _engine = QueryEngine()
        except Exception as e:
            logger.error(f"Failed to initialize QueryEngine: {e}")
    return _engine

@router.post("/query", response_model=QueryResponse)
@limiter.limit("5/minute")
def process_query(request: Request, query: QueryRequest):
    try:
        engine = get_engine()
        if engine is None:
            return QueryResponse(
                answer="The query engine is currently unavailable. Please try again later.",
                sources=[],
                confidence=0.0
            )
        response_text = engine.process_query(query.question, filters=query.filters)
        return QueryResponse(
            answer=response_text,
            sources=[],
            confidence=0.92
        )
    except Exception as e:
        logger.error(f"Query processing error: {e}")
        return QueryResponse(
            answer=f"An error occurred while processing your question: {str(e)[:200]}",
            sources=[],
            confidence=0.0
        )

@router.get("/debug/chroma")
def debug_chroma():
    try:
        import chromadb
        from src.rag.vector_store import DB_PATH, COLLECTION_NAME
        client = chromadb.PersistentClient(path=DB_PATH)
        collection = client.get_collection(COLLECTION_NAME)
        count = collection.count()
        return {"count": count, "db_path": DB_PATH}
    except Exception as e:
        return {"error": str(e)}
