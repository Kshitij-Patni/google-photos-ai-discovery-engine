import os
import json
from dotenv import load_dotenv
from src.rag.structured_store import run_query, get_count
from src.utils.gemini_client import GeminiClient

def map_frustration(level):
    m = {'low': 1, 'medium': 2, 'high': 3, 'extreme': 4}
    return m.get(level.lower() if level else '', 0)

def format_frustration(score):
    if score >= 3.5: return "extreme"
    if score >= 2.5: return "high"
    if score >= 1.5: return "medium"
    return "low"

def main():
    load_dotenv()
    
    # Check reports directory
    os.makedirs("reports", exist_ok=True)
    
    client = GeminiClient(model_name="gemini-3.5-flash-lite")
    
    # 1. Get total corpus size
    total_records = get_count("feedback")
    
    # 2. Get list of archetypes
    archetypes = [r['archetype'] for r in run_query("SELECT DISTINCT archetype FROM archetypes")]
    
    all_reports = {}
    md_lines = ["# Archetype Reports\n\n"]
    
    for arch in archetypes:
        print(f"Processing {arch}...")
        
        # Frequency
        count = get_count("archetypes", "archetype = ?", (arch,))
        pct = round((count / total_records) * 100, 2) if total_records else 0
        
        # Severity
        meta_query = """
            SELECT m.frustration_level, m.photo_category, m.search_strategy, m.outcome
            FROM archetypes a
            JOIN metadata m ON a.feedback_id = m.feedback_id
            WHERE a.archetype = ?
        """
        meta_results = run_query(meta_query, (arch,))
        
        frustration_scores = []
        categories = {}
        strategies = {}
        outcomes = {}
        
        for r in meta_results:
            fl = r['frustration_level']
            if fl:
                frustration_scores.append(map_frustration(fl))
                
            cat = r['photo_category']
            if cat:
                categories[cat] = categories.get(cat, 0) + 1
                
            strat = r['search_strategy']
            if strat:
                strategies[strat] = strategies.get(strat, 0) + 1
                
            out = r['outcome']
            if out:
                outcomes[out] = outcomes.get(out, 0) + 1
                
        avg_score = sum(frustration_scores) / len(frustration_scores) if frustration_scores else 0
        avg_score_rounded = round(avg_score, 1)
        severity_label = format_frustration(avg_score)
        
        top_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]
        top_cats_str = ", ".join([k for k, v in top_cats]) if top_cats else "N/A"
        
        top_strat = sorted(strategies.items(), key=lambda x: x[1], reverse=True)[0][0] if strategies else "N/A"
        top_out = sorted(outcomes.items(), key=lambda x: x[1], reverse=True)[0][0] if outcomes else "N/A"
        
        # Evidence Quotes
        quote_query = """
            SELECT f.cleaned_text, f.source, f.rating
            FROM archetypes a
            JOIN feedback f ON a.feedback_id = f.id
            WHERE a.archetype = ?
            ORDER BY f.rating ASC, f.word_count DESC
            LIMIT 5
        """
        quotes_results = run_query(quote_query, (arch,))
        
        quotes_formatted = ""
        quotes_list = []
        for i, q in enumerate(quotes_results, 1):
            quotes_formatted += f"{i}. \"{q['cleaned_text']}\" — {q['source']} (Rating: {q['rating']})\n"
            quotes_list.append({
                "quote": q['cleaned_text'],
                "source": q['source'],
                "rating": q['rating']
            })
            
        metrics_text = f"""
Frequency: {count} records ({pct}%)
Severity: {severity_label} ({avg_score_rounded}/5)
Top Categories: {top_cats_str}
Top Strategy: {top_strat}
Top Outcome: {top_out}
"""

        prompt = f"""You are an expert product analyst for Google Photos.
I will provide you with statistics and user quotes for a specific user problem archetype: '{arch}'.

Metrics:
{metrics_text}

Evidence Quotes:
{quotes_formatted}

Please synthesize a product insight profile for this archetype.
Respond with a JSON object containing EXACTLY:
- "pattern": A 2-3 sentence narrative explaining the root cause of the user frustration and the behavioral pattern.
- "opportunity_signal": "strong", "moderate", or "weak" based on how impactful solving this issue would be.
"""
        schema = {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "opportunity_signal": {"type": "string", "enum": ["strong", "moderate", "weak"]}
            },
            "required": ["pattern", "opportunity_signal"]
        }
        
        response = client.generate_json(prompt, schema=schema)
        if response:
            pattern = response.get("pattern", "Analysis failed.")
            signal = response.get("opportunity_signal", "moderate")
        else:
            pattern = "Analysis failed."
            signal = "moderate"
            
        report_data = {
            "name": arch,
            "frequency": {
                "count": count,
                "percentage": pct
            },
            "severity": {
                "level": severity_label,
                "avg_score": avg_score_rounded
            },
            "most_affected_categories": [k for k, v in top_cats],
            "most_common_search_strategy": top_strat,
            "most_common_outcome": top_out,
            "pattern": pattern,
            "opportunity_signal": signal,
            "evidence": quotes_list
        }
        all_reports[arch] = report_data
        
        md = f"""### ARCHETYPE: {arch}

| Metric | Value |
|---|---|
| **Frequency** | {count} records ({pct}% of corpus) |
| **Severity** | {severity_label.capitalize()} (avg {avg_score_rounded}/5) |
| **Most Affected Categories** | {top_cats_str} |
| **Most Common Search Strategy** | {top_strat} |
| **Most Common Outcome** | {top_out} |

**Pattern**: {pattern}

**Key Evidence**:
"""
        for i, q in enumerate(quotes_list, 1):
            md += f"{i}. \"{q['quote']}\" — {q['source']}\n"
            
        md += f"\n**Opportunity Signal**: {signal.capitalize()}\n\n---\n\n"
        md_lines.append(md)
        
    with open("reports/archetype_report.json", "w") as f:
        json.dump(all_reports, f, indent=2)
        
    with open("reports/archetype_report.md", "w") as f:
        f.writelines(md_lines)
        
    print("Reports generated in reports/ directory.")

if __name__ == "__main__":
    main()
