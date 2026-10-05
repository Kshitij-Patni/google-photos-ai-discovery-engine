import os
import json
from dotenv import load_dotenv
from src.utils.gemini_client import GeminiClient

def generate_priority_matrix():
    load_dotenv()
    os.makedirs("reports", exist_ok=True)
    
    # Load data
    with open("reports/archetype_report.json", "r") as f:
        archetype_data = json.load(f)
        
    with open("reports/emergent_themes_report.json", "r") as f:
        themes_data = json.load(f)
        
    # We will use the default model for the GeminiClient as gemini-2.0-pro is not available
    client = GeminiClient()
    
    schema = {
        "type": "OBJECT",
        "properties": {
            "rationale": {"type": "STRING"}
        },
        "required": ["rationale"]
    }

    # Highest archetype frequency %, used to build the Frequency Index (0-10)
    max_freq = max(
        (a["frequency"]["percentage"] for a in archetype_data.values()
         if isinstance(a, dict) and "frequency" in a),
        default=0,
    )

    results = []
    print("Evaluating archetypes...")
    for arch_name, arch_info in archetype_data.items():
        if not isinstance(arch_info, dict) or "frequency" not in arch_info:
            continue
            
        print(f"Assessing {arch_name}...")
        pct = arch_info["frequency"]["percentage"]
        severity_score = arch_info["severity"]["avg_score"]
        pattern = arch_info.get("pattern", "Unknown problem")
        
        # Feasibility (0-10) is assessed once per archetype and stored in the archetype report
        feasibility = arch_info.get("feasibility", 0)

        prompt = f"""
        Evaluate the following user problem in Google Photos:
        Archetype: {arch_name}
        Pattern: {pattern}
        Feasibility of fixing it (0-10, 10 = easy quick win): {feasibility}

        In 2-3 sentences, explain why this problem matters and how feasible it is to fix.
        """

        gemini_res = client.generate_json(prompt, schema=schema)
        rationale = gemini_res.get("rationale", "") if gemini_res else "Assessment failed."

        # Opportunity Score (0-10) = (Frequency Index x 0.4) + (Severity Index x 0.4) + (Feasibility x 0.2)
        freq_index = (pct / max_freq * 10) if max_freq else 0
        severity_index = severity_score / 4 * 10
        priority_score = (freq_index * 0.4) + (severity_index * 0.4) + (feasibility * 0.2)
        
        results.append({
            "archetype": arch_name,
            "frequency": pct,
            "severity": severity_score,
            "feasibility": feasibility,
            "score": priority_score,
            "rationale": rationale
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    
    # Assign P0, P1, P2, P3
    for i, r in enumerate(results):
        if i == 0:
            r["priority"] = "P0"
        elif i < 3:
            r["priority"] = "P1"
        elif i < 6:
            r["priority"] = "P2"
        else:
            r["priority"] = "P3"
            
    # Process problem clusters for quadrant map
    clusters = themes_data.get("clusters", {})
    quadrant_data = []
    
    # Calculate min/max for scaling to 0-1 for mermaid
    for c_id, c_info in clusters.items():
        size = c_info.get("size", 0)
        frustrations = c_info.get("dominant_frustration", {})
        
        low = frustrations.get("low", 0)
        med = frustrations.get("medium", 0)
        high = frustrations.get("high", 0)
        ext = frustrations.get("extreme", 0)
        
        total = low + med + high + ext
        if total > 0:
            avg_severity = (low*1 + med*2 + high*3 + ext*4) / total
        else:
            avg_severity = 0
            
        quadrant_data.append({
            "label": c_info.get("theme_label", f"Cluster {c_id}")[:30],
            "freq": size,
            "sev": avg_severity
        })
        
    if quadrant_data:
        max_freq = max(q["freq"] for q in quadrant_data)
        max_sev = max(q["sev"] for q in quadrant_data)
        min_freq = min(q["freq"] for q in quadrant_data)
        min_sev = min(q["sev"] for q in quadrant_data)
        
        for q in quadrant_data:
            # Scale to 0.1 - 0.9 for display
            q["freq_scaled"] = 0.1 + 0.8 * ((q["freq"] - min_freq) / (max_freq - min_freq or 1))
            q["sev_scaled"] = 0.1 + 0.8 * ((q["sev"] - min_sev) / (max_sev - min_sev or 1))

    # Generate Markdown
    md = "# Opportunity Prioritization Matrix\n\n"
    
    md += "## Frequency vs. Severity Quadrant Map (Dynamic Problem Clusters)\n\n"
    md += "```mermaid\n"
    md += "quadrantChart\n"
    md += "    title Problem Clusters: Frequency vs Severity\n"
    md += "    x-axis Low Frequency --> High Frequency\n"
    md += "    y-axis Low Severity --> High Severity\n"
    md += "    quadrant-1 High Priority\n"
    md += "    quadrant-2 Focus Here\n"
    md += "    quadrant-3 Low Priority\n"
    md += "    quadrant-4 Quick Wins\n"
    
    for q in quadrant_data:
        # Mermaid has issues with special characters in labels, keep it simple
        clean_label = "".join(c if c.isalnum() or c.isspace() else "" for c in q["label"]).strip()
        md += f"    {clean_label}: [{q['freq_scaled']:.2f}, {q['sev_scaled']:.2f}]\n"
    md += "```\n\n"

    md += "## Prioritized Archetypes\n\n"
    md += "**Opportunity Score (0-10) = (Frequency Index × 0.4) + (Severity Index × 0.4) + (Feasibility × 0.2)**\n\n"
    md += "Frequency Index = frequency % ÷ highest archetype frequency % × 10; Severity Index = avg severity (1-4) ÷ 4 × 10; Feasibility = 0-10 (10 = easy fix).\n\n"
    md += "| Priority | Archetype | Score | Frequency (%) | Severity (1-4) | Feasibility (0-10) | Rationale |\n"
    md += "|---|---|---|---|---|---|---|\n"
    
    for r in results:
        clean_rationale = r['rationale'].replace('\n', ' ')
        md += f"| **{r['priority']}** | {r['archetype']} | **{r['score']:.2f}** | {r['frequency']} | {r['severity']:.1f} | {r['feasibility']} | {clean_rationale} |\n"

    with open("reports/opportunity_matrix.md", "w") as f:
        f.write(md)
        
    print("reports/opportunity_matrix.md generated successfully.")

def main():
    generate_priority_matrix()

if __name__ == "__main__":
    main()
