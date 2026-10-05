from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from src.api.schemas import PaginatedEvidence, EvidenceRecord
import sqlite3
import os
from pathlib import Path

router = APIRouter()
# Resolve DB path relative to project root (4 levels up from this file: routes → api → src → project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DB_PATH = str(os.environ.get("SQLITE_PATH") or _PROJECT_ROOT / "data" / "discovery_engine.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@router.get("/evidence", response_model=PaginatedEvidence)
async def get_evidence(
    source: Optional[str] = None,
    archetype: Optional[str] = None,
    frustration_level: Optional[str] = None,
    sort_by: Optional[str] = Query("newest", description="newest, most_engaged, highest_frustration"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100)
):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Base queries
        where_clauses = ["1=1"]
        params = []
        
        if source:
            source_map = {
                "play_store": "google_play_store",
                "app_store": "apple_app_store",
                "youtube": "youtube",
                "support_forums": "google_support_forums"
            }
            db_source = source_map.get(source, source)
            where_clauses.append("f.source = ?")
            params.append(db_source)
            
        if frustration_level:
            where_clauses.append("m.frustration_level = ?")
            params.append(frustration_level)
            
        if archetype:
            # We filter for records that have this archetype
            where_clauses.append("f.id IN (SELECT feedback_id FROM archetypes WHERE archetype = ?)")
            params.append(archetype)
            
        where_sql = " AND ".join(where_clauses)
        
        # Count total
        count_query = f"""
            SELECT COUNT(DISTINCT f.id) as total 
            FROM feedback f 
            LEFT JOIN metadata m ON f.id = m.feedback_id 
            WHERE {where_sql}
        """
        cursor.execute(count_query, params)
        total = cursor.fetchone()["total"]
        
        # Sorting
        order_by = "f.date DESC"
        if sort_by == "most_engaged":
            order_by = "engagement_score DESC"
        elif sort_by == "highest_frustration":
            # Map frustration level string to number for sorting (if possible) or just text sort
            # For simplicity:
            order_by = "CASE m.frustration_level WHEN 'extreme' THEN 4 WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 ELSE 0 END DESC"
            
        # Select data
        query = f"""
            SELECT 
                f.id,
                f.source,
                f.cleaned_text as raw_text,
                f.cleaned_text,
                m.frustration_level,
                m.photo_category,
                f.date,
                COALESCE(f.rating, 0) as engagement_score,
                GROUP_CONCAT(a.archetype) as archetypes_str
            FROM feedback f
            LEFT JOIN metadata m ON f.id = m.feedback_id
            LEFT JOIN archetypes a ON f.id = a.feedback_id
            WHERE {where_sql}
            GROUP BY f.id
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
        """
        
        query_params = list(params) + [size, (page - 1) * size]
        cursor.execute(query, query_params)
        rows = cursor.fetchall()
        
        inverse_source_map = {
            "google_play_store": "play_store",
            "apple_app_store": "app_store",
            "youtube": "youtube",
            "google_support_forums": "support_forums"
        }
        
        items = []
        for row in rows:
            # archetypes_str comes as comma-separated
            arch_list = []
            if row["archetypes_str"]:
                # deduplicate if GROUP_CONCAT returns duplicates
                arch_list = list(set(row["archetypes_str"].split(",")))
                
            out_source = inverse_source_map.get(row["source"], row["source"] or "unknown")
                
            items.append(EvidenceRecord(
                id=str(row["id"]),
                source=out_source,
                raw_text=row["raw_text"] or "",
                cleaned_text=row["cleaned_text"] or "",
                frustration_level=row["frustration_level"] or "low",
                archetypes=arch_list,
                photo_category=row["photo_category"] or "other",
                date=row["date"] or "",
                engagement_score=row["engagement_score"]
            ))
            
        conn.close()
        
        return PaginatedEvidence(
            items=items,
            total=total,
            page=page,
            size=size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
