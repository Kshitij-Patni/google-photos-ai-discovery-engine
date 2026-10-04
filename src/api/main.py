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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGINS", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(insights.router, prefix="/api/v1")
app.include_router(query.router, prefix="/api/v1")
app.include_router(data.router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "healthy", "chromadb": "connected"}
