import os
import json
from dotenv import load_dotenv
from src.rag.structured_store import run_query, get_count
from src.utils.gemini_client import GeminiClient

def main():
    load_dotenv()
    
    os.makedirs("reports", exist_ok=True)
    
    print("Loading emergent themes report...")
    with open("reports/emergent_themes_report.json", "r") as f:
        data = json.load(f)
        
    client = GeminiClient(model_name="gemini-3.5-flash-lite")
    
    md_lines = ["# Emergent Themes Report\n\n"]
    md_lines.append("This report details dynamically discovered problem clusters (emergent themes) organically formed from user feedback.\n\n---\n\n")
    
    clusters = data.get("clusters", {})
    
    for cluster_id, cluster_data in clusters.items():
        theme_label = cluster_data.get("theme_label", f"Cluster {cluster_id}")
        print(f"Processing Theme: {theme_label}...")
        
        size = cluster_data.get("size", 0)
        desc = cluster_data.get("theme_description", "")
        keywords = ", ".join(cluster_data.get("top_keywords", []))
        
        # Get quotes for this cluster
        quote_query = """
            SELECT f.cleaned_text, f.source, f.rating
            FROM themes t
            JOIN feedback f ON t.feedback_id = f.id
            WHERE t.cluster_id = ?
            ORDER BY f.rating ASC, f.word_count DESC
            LIMIT 5
        """
        quotes_results = run_query(quote_query, (int(cluster_id),))
        
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
Theme Label: {theme_label}
Size: {size} records
Description: {desc}
Top Keywords: {keywords}
"""

        prompt = f"""You are an expert product analyst for Google Photos.
I will provide you with statistics and user quotes for a dynamically discovered "emergent theme" of user feedback: '{theme_label}'.

Metrics:
{metrics_text}

Evidence Quotes:
{quotes_formatted}

Please synthesize a product insight profile for this emergent theme.
Respond with a JSON object containing EXACTLY:
- "pattern": A 2-3 sentence narrative explaining the root cause of this emergent theme and why it groups together.
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
            pattern = response.get("pattern", "Analysis failed (rate limited).")
            signal = response.get("opportunity_signal", "moderate")
        else:
            pattern = "Analysis failed (rate limited)."
            signal = "moderate"
            
        md = f"### THEME: {theme_label}\n\n"
        md += f"**Cluster ID**: {cluster_id}  \n"
        md += f"**Size**: {size} records  \n"
        md += f"**Description**: {desc}  \n"
        md += f"**Top Keywords**: {keywords}  \n\n"
        
        md += f"**Pattern**: {pattern}\n\n"
        md += "**Key Evidence**:\n"
        for i, q in enumerate(quotes_list, 1):
            md += f"{i}. \"{q['quote']}\" — {q['source']}\n"
            
        md += f"\n**Opportunity Signal**: {signal.capitalize()}\n\n---\n\n"
        md_lines.append(md)
        
    with open("reports/emergent_themes_report.md", "w") as f:
        f.writelines(md_lines)
        
    print("Reports generated: reports/emergent_themes_report.md")

if __name__ == "__main__":
    main()
