from fastapi import APIRouter, Request
from src.api.schemas import QueryRequest, QueryResponse
from src.api.limiter import limiter
from src.rag.query_engine import QueryEngine

router = APIRouter()
engine = QueryEngine()

@router.post("/query", response_model=QueryResponse)
@limiter.limit("5/minute")
def process_query(request: Request, query: QueryRequest):
    response_text = engine.process_query(query.question, filters=query.filters)
    return QueryResponse(
        answer=response_text,
        sources=[],
        confidence=0.92
    )
