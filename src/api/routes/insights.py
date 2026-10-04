import os
import json
import sqlite3
from fastapi import APIRouter
from typing import List, Optional
from src.api.schemas import (
    DashboardStats, ArchetypeSummary, ArchetypeDetail,
    ThemeCluster, MemoryCueMatrix, BehaviorPatterns, ChartData
)

router = APIRouter()
DB_PATH = "data/discovery_engine.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@router.get("/stats", response_model=DashboardStats)
async def get_stats():
    conn = get_db()
    cursor = conn.cursor()
    
    total = cursor.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
    relevant = cursor.execute("SELECT COUNT(*) FROM metadata").fetchone()[0]
    sources = cursor.execute("SELECT COUNT(DISTINCT source) FROM feedback").fetchone()[0]
    archetypes = cursor.execute("SELECT COUNT(DISTINCT archetype) FROM archetypes").fetchone()[0]
    
    conn.close()
    return DashboardStats(
        total_records=total,
        relevant_records=relevant,
        sources_covered=sources,
        archetypes_identified=archetypes
    )

@router.get("/archetypes", response_model=List[ArchetypeSummary])
async def get_archetypes():
    with open("reports/archetype_report.json", "r") as f:
        arch_data = json.load(f)
        
    result = []
    for k, v in arch_data.items():
        score = v.get("severity", {}).get("avg_score", 0) * v.get("frequency", {}).get("percentage", 0) / 10
        result.append(
            ArchetypeSummary(
                id=k.lower(),
                name=v["name"],
                frequency_pct=v["frequency"]["percentage"],
                severity=v["severity"]["level"].upper(),
                record_count=v["frequency"]["count"],
                top_categories=v["most_affected_categories"],
                opportunity_score=round(score, 2)
            )
        )
        
    return sorted(result, key=lambda x: x.opportunity_score, reverse=True)

@router.get("/archetypes/{id}", response_model=ArchetypeDetail)
async def get_archetype_detail(id: str):
    with open("reports/archetype_report.json", "r") as f:
        arch_data = json.load(f)
        
    data = None
    for k, v in arch_data.items():
        if k.lower() == id.lower():
            data = v
            break
            
    if not data:
        data = arch_data.get(list(arch_data.keys())[0])

    quotes = [q["quote"] for q in data.get("evidence", [])]
    
    score = data.get("severity", {}).get("avg_score", 0) * data.get("frequency", {}).get("percentage", 0) / 10
    
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
            "ux_gap": 0,
            "feasibility": 0
        }
    )

@router.get("/themes", response_model=List[ThemeCluster])
async def get_themes():
    with open("reports/emergent_themes_report.json", "r") as f:
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
    conn = get_db()
    cursor = conn.cursor()
    rows = cursor.execute("SELECT memory_cues, memory_gaps, photo_category FROM metadata").fetchall()
    conn.close()
    
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
    for r in rows:
        cues = parse_list(r['memory_cues']) if mode == "remembered" else parse_list(r['memory_gaps'])
        cat = r['photo_category'] or 'unknown'
        categories.add(cat)
        for c in cues:
            cues_set.add(c)
            data.append({"cue": c, "category": cat})
            
    cat_list = sorted(list(categories))
    cue_list = sorted(list(cues_set))
    
    if not cue_list:
        return MemoryCueMatrix(categories=[], cue_types=[], matrix=[])
        
    matrix = [[0 for _ in cat_list] for _ in cue_list]
    for d in data:
        c_idx = cue_list.index(d['cue'])
        cat_idx = cat_list.index(d['category'])
        matrix[c_idx][cat_idx] += 1
        
    return MemoryCueMatrix(
        categories=cat_list,
        cue_types=cue_list,
        matrix=matrix
    )

@router.get("/behaviors", response_model=BehaviorPatterns)
async def get_behaviors():
    conn = get_db()
    cursor = conn.cursor()
    rows = cursor.execute("SELECT search_strategy, outcome, COUNT(*) as count FROM metadata WHERE search_strategy IS NOT NULL AND outcome IS NOT NULL GROUP BY search_strategy, outcome").fetchall()
    conn.close()
    
    strategies = set()
    outcomes = set()
    flow_data = []
    for r in rows:
        strategies.add(r['search_strategy'])
        outcomes.add(r['outcome'])
        flow_data.append({
            "strategy": r['search_strategy'],
            "outcome": r['outcome'],
            "count": r['count']
        })
        
    return BehaviorPatterns(
        strategies=list(strategies),
        outcomes=list(outcomes),
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
    path = f"reports/charts/{file_name}.json"
    
    if os.path.exists(path):
        with open(path, "r") as f:
            data = json.load(f)
            return ChartData(data=data.get("data", []), layout=data.get("layout", {}))
            
    return ChartData(data=[], layout={})
