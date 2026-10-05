import os
import json
import sqlite3
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pathlib import Path
from src.api.schemas import (
    DashboardStats, ArchetypeSummary, ArchetypeDetail,
    ThemeCluster, MemoryCueMatrix, BehaviorPatterns, ChartData
)

router = APIRouter()
# Resolve paths relative to project root (4 levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_BUNDLED_DB = _PROJECT_ROOT / "data" / "discovery_engine.db"
_ENV_DB = os.environ.get("SQLITE_PATH")
# Use SQLITE_PATH only if the file really exists (e.g. populated Railway volume); else use bundled DB
DB_PATH = str(_ENV_DB if _ENV_DB and Path(_ENV_DB).is_file() else _BUNDLED_DB)
_REPORTS_DIR = _PROJECT_ROOT / "reports"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Opportunity Score (0-10) = (Frequency Index × 0.4) + (Severity Index × 0.4) + (Feasibility × 0.2)
#   Frequency Index = archetype frequency % / highest archetype frequency % × 10
#   Severity Index  = avg severity (1-4) / 4 × 10
#   Feasibility     = Gemini-assessed feasibility (0-10), rated for every archetype
def _opportunity_score(freq_pct, max_freq, sev_avg, feasibility):
    freq_idx = (freq_pct / max_freq * 10) if max_freq else 0
    sev_idx = sev_avg / 4 * 10
    return (freq_idx * 0.4) + (sev_idx * 0.4) + (feasibility * 0.2)

def _max_freq(arch_data):
    return max((v.get("frequency", {}).get("percentage", 0) for v in arch_data.values()), default=0)

@router.get("/stats", response_model=DashboardStats)
async def get_stats():
    try:
        conn = get_db()
        cursor = conn.cursor()
        # Total scraped records across all sources (see data/raw/ingestion_report.json)
        total = 15275
        relevant = cursor.execute("SELECT COUNT(*) FROM metadata").fetchone()[0]
        # 4 sources: Play Store, App Store, YouTube, Google Support Forums
        sources = 4
        archetypes = cursor.execute("SELECT COUNT(DISTINCT archetype) FROM archetypes").fetchone()[0]
        conn.close()
        return DashboardStats(
            total_records=total,
            relevant_records=relevant,
            sources_covered=sources,
            archetypes_identified=archetypes
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error in /stats: {e} | DB_PATH={DB_PATH}")

@router.get("/archetypes", response_model=List[ArchetypeSummary])
async def get_archetypes():
    with open(_REPORTS_DIR / "archetype_report.json", "r") as f:
        arch_data = json.load(f)
        
    max_freq = _max_freq(arch_data)
    result = []
    for k, v in arch_data.items():
        freq_pct = v.get("frequency", {}).get("percentage", 0)
        sev_score = v.get("severity", {}).get("avg_score", 0)
        feasibility = v.get("feasibility", 0)
        score = _opportunity_score(freq_pct, max_freq, sev_score, feasibility)
        
        result.append(
            ArchetypeSummary(
                id=k.lower(),
                name=v["name"],
                frequency_pct=freq_pct,
                severity=v["severity"]["level"].upper(),
                record_count=v["frequency"]["count"],
                top_categories=v["most_affected_categories"],
                opportunity_score=round(score, 2)
            )
        )
        
    return sorted(result, key=lambda x: x.opportunity_score, reverse=True)

@router.get("/archetypes/{id}", response_model=ArchetypeDetail)
async def get_archetype_detail(id: str):
    with open(_REPORTS_DIR / "archetype_report.json", "r") as f:
        arch_data = json.load(f)
        
    data = None
    for k, v in arch_data.items():
        if k.lower() == id.lower():
            data = v
            break
            
    if not data:
        data = arch_data.get(list(arch_data.keys())[0])

    quotes = [q["quote"] for q in data.get("evidence", [])]
    
    feasibility = data.get("feasibility", 0)
    score = _opportunity_score(
        data.get("frequency", {}).get("percentage", 0), _max_freq(arch_data),
        data.get("severity", {}).get("avg_score", 0), feasibility
    )
    
    return ArchetypeDetail(
        id=id,
        name=data["name"],
        frequency_pct=data["frequency"]["percentage"],
        severity=data["severity"]["level"].upper(),
        record_count=data["frequency"]["count"],
        top_categories=data["most_affected_categories"],
        description=data["pattern"],
        evidence_quotes=quotes,
        scorecard={
            "score": round(score, 2),
            "frequency": data["frequency"]["percentage"],
            "severity": data["severity"]["avg_score"],
            "feasibility": feasibility
        }
    )

@router.get("/themes", response_model=List[ThemeCluster])
async def get_themes():
    with open(_REPORTS_DIR / "emergent_themes_report.json", "r") as f:
        themes = json.load(f)
        
    result = []
    for cid, t in themes.get("clusters", {}).items():
        result.append(
            ThemeCluster(
                id=int(cid),
                label=t["theme_label"],
                description=t["theme_description"],
                record_count=t["size"]
            )
        )
    return result

@router.get("/memory-cues", response_model=MemoryCueMatrix)
async def get_memory_cues(mode: str = "remembered"):
    try:
        conn = get_db()
        cursor = conn.cursor()
        rows = cursor.execute("SELECT memory_cues, memory_gaps, photo_category FROM metadata").fetchall()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error in /memory-cues: {e} | DB_PATH={DB_PATH}")
    
    import ast
    def parse_list(l_str):
        if not l_str or l_str == 'None': return []
        try: return json.loads(l_str)
        except:
            try: return ast.literal_eval(l_str)
            except: return []

    categories = set()
    cues_set = set()
    data = []
    
    CUE_MAPPING = {
        "time": "Temporal", "date": "Temporal", "year": "Temporal", "months": "Temporal", "timeline": "Temporal", "years ago": "Temporal", 
        "exact date": "Temporal", "date/time": "Temporal", "10th last trip": "Temporal", "older photos": "Temporal", "old photos": "Temporal", 
        "past special moments": "Temporal", "old phone": "Temporal",
        "person": "People", "people": "People", "face": "People", "faces": "People", "family": "People",
        "person name": "People", "brother": "People", "aunt": "People", "baby": "People", "child": "People",
        "daughter": "People", "parents": "People", "grandmother": "People", "granddaughter": "People", 
        "particular friend or family": "People", "13 people": "People", "4 generation pictures": "People",
        "newborns baby photos": "People", "Krishna ji": "People",
        "visual detail": "Visual", "object": "Visual", "thing": "Visual", 
        "keyword": "Visual", "sweet treats": "Visual", "food": "Visual", 
        "artwork": "Visual", "dog": "Visual", "dog's face": "Visual", "pet": "Visual",
        "video screenshot": "Visual", "dental photo": "Visual", "hairstyles": "Visual",
        "place": "Spatial", "places": "Spatial", "location": "Spatial", "beach": "Spatial", "pool": "Spatial", 
        "Zakopane snow shots": "Spatial",
        "activity": "Activity", "event": "Activity", "events": "Activity", "travel": "Activity", "trips": "Activity",
        "wedding pictures": "Activity", "daughter's graduation": "Activity",
        "emotion": "Emotional",
        "album": "Content Type", "album name": "Content Type", "locked folder": "Content Type", 
        "selected images": "Content Type", "Spotlight videos": "Content Type", "best of highlights": "Content Type",
        "language": "Content Type", "unknown": "Content Type"
    }

    CUE_MAPPING_LOWER = {k.lower(): v for k, v in CUE_MAPPING.items()}

    def standardize_cue(c):
        c_lower = c.lower()
        if c_lower in CUE_MAPPING_LOWER:
            return CUE_MAPPING_LOWER[c_lower]
        if any(x in c_lower for x in ["time", "date", "year", "month", "ago", "old"]): return "Temporal"
        if any(x in c_lower for x in ["person", "people", "face", "family", "friend", "girl", "boy"]): return "People"
        if any(x in c_lower for x in ["place", "location", "city", "country", "beach", "pool"]): return "Spatial"
        if any(x in c_lower for x in ["event", "trip", "travel", "wedding", "graduation"]): return "Activity"
        if any(x in c_lower for x in ["album", "folder", "video"]): return "Content Type"
        return "Visual"

    for r in rows:
        cues = parse_list(r['memory_cues']) if mode == "remembered" else parse_list(r['memory_gaps'])
        cat = r['photo_category'] or 'unknown'
        categories.add(cat)
        for c in cues:
            std_c = standardize_cue(c)
            cues_set.add(std_c)
            data.append({"cue": std_c, "category": cat})
            
    cat_list = sorted(list(categories))
    
    # Custom order to match original design
    desired_order = ["Temporal", "Spatial", "People", "Emotional", "Visual", "Activity", "Content Type"]
    cue_list = []
    for c in desired_order:
        if c in cues_set:
            cue_list.append(c)
    # Add any remaining ones just in case
    for c in sorted(list(cues_set)):
        if c not in cue_list:
            cue_list.append(c)
    
    if not cue_list:
        return MemoryCueMatrix(categories=[], cue_types=[], matrix=[])
        
    matrix = [[0 for _ in cue_list] for _ in cat_list]
    for d in data:
        c_idx = cue_list.index(d['cue'])
        cat_idx = cat_list.index(d['category'])
        matrix[cat_idx][c_idx] += 1
        
    return MemoryCueMatrix(
        categories=cat_list,
        cue_types=cue_list,
        matrix=matrix
    )

@router.get("/behaviors", response_model=BehaviorPatterns)
async def get_behaviors():
    try:
        conn = get_db()
        cursor = conn.cursor()
        query = """
            SELECT search_strategy, outcome, COUNT(*) as count 
            FROM metadata 
            WHERE search_strategy IN ('timeline_scroll', 'album_browse', 'keyword_search', 'people_search', 'location_search') 
              AND outcome IN ('found', 'not_found', 'used_workaround', 'gave_up')
            GROUP BY search_strategy, outcome
            ORDER BY count DESC
        """
        rows = cursor.execute(query).fetchall()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error in /behaviors: {e} | DB_PATH={DB_PATH}")
    
    strategies = set()
    outcomes = set()
    flow_data = []
    
    # Optional: Map internal keys to clean labels if desired
    # But the frontend does `.replace(/_/g, ' ')`, so we can keep the raw keys.
    
    for r in rows:
        strategies.add(r['search_strategy'])
        outcomes.add(r['outcome'])
        flow_data.append({
            "strategy": r['search_strategy'],
            "outcome": r['outcome'],
            "count": r['count']
        })
        
    return BehaviorPatterns(
        strategies=sorted(list(strategies)),
        outcomes=sorted(list(outcomes)),
        flow_data=flow_data
    )

@router.get("/charts/{chart_name}", response_model=ChartData)
async def get_chart_data(chart_name: str):
    chart_map = {
        "archetype_distribution": "archetype_distribution",
        "sentiment_analysis": "sentiment_analysis",
        "source_distribution": "source_coverage",
        "engagement_vs_frustration": "impact_frequency_quadrant",
        "thematic_clustering": "frustration_by_source"
    }
    
    file_name = chart_map.get(chart_name, chart_name)
    path = _REPORTS_DIR / "charts" / f"{file_name}.json"
    
    if path.exists():
        with open(path, "r") as f:
            data = json.load(f)
            return ChartData(data=data.get("data", []), layout=data.get("layout", {}))
            
    return ChartData(data=[], layout={})
