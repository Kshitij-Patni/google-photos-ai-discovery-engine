import os
import json
import ast
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from wordcloud import WordCloud

from src.rag.structured_store import run_query

def parse_list(l_str):
    if not l_str or l_str == 'None':
        return []
    try:
        return json.loads(l_str)
    except:
        try:
            return ast.literal_eval(l_str)
        except:
            return []

def main():
    os.makedirs("reports/charts", exist_ok=True)
    
    print("Generating visualizations...")

    # 1. Memory Cue Frequency Heatmap
    metadata = run_query("SELECT memory_cues, photo_category FROM metadata")
    data_cues = []
    for row in metadata:
        cues = parse_list(row['memory_cues'])
        cat = row['photo_category'] or 'unknown'
        for cue in cues:
            data_cues.append({"cue": cue, "category": cat})

    df_cues = pd.DataFrame(data_cues)
    if not df_cues.empty:
        heatmap_data = df_cues.groupby(["cue", "category"]).size().reset_index(name="count")
        # Pivot the data so px.imshow can make a proper heatmap, or use density_heatmap
        fig1 = px.density_heatmap(heatmap_data, x="category", y="cue", z="count", title="Memory Cue Frequency Heatmap")
        fig1.write_html("reports/charts/memory_cue_heatmap.html")
        fig1.write_json("reports/charts/memory_cue_heatmap.json")
    
    # 2. Archetype Distribution Pie Chart
    archs = run_query("SELECT archetype, COUNT(*) as count FROM archetypes GROUP BY archetype")
    df_archs = pd.DataFrame(archs)
    if not df_archs.empty:
        fig2 = px.pie(df_archs, names='archetype', values='count', title="Archetype Distribution")
        fig2.update_traces(textposition='inside')
        fig2.write_html("reports/charts/archetype_distribution.html")
        fig2.write_json("reports/charts/archetype_distribution.json")
    
    # 3. Frustration Level by Source Bar Chart
    frust = run_query("""
        SELECT f.source, m.frustration_level, COUNT(*) as count
        FROM metadata m
        JOIN feedback f ON m.feedback_id = f.id
        WHERE m.frustration_level IS NOT NULL
        GROUP BY f.source, m.frustration_level
    """)
    df_frust = pd.DataFrame(frust)
    if not df_frust.empty:
        fig3 = px.bar(df_frust, x="source", y="count", color="frustration_level", barmode="group", title="Frustration Level by Source")
        fig3.write_html("reports/charts/frustration_by_source.html")
        fig3.write_json("reports/charts/frustration_by_source.json")
    
    # 4. Search Strategy → Outcome Sankey Diagram
    strat_out = run_query("""
        SELECT search_strategy, outcome, COUNT(*) as count 
        FROM metadata 
        WHERE search_strategy IS NOT NULL AND outcome IS NOT NULL 
        GROUP BY search_strategy, outcome
    """)
    df_so = pd.DataFrame(strat_out)
    if not df_so.empty:
        all_nodes = list(pd.concat([df_so['search_strategy'], df_so['outcome']]).unique())
        node_dict = {node: i for i, node in enumerate(all_nodes)}
        source_idx = df_so['search_strategy'].map(node_dict)
        target_idx = df_so['outcome'].map(node_dict)
        fig4 = go.Figure(data=[go.Sankey(
            node = dict(label = all_nodes),
            link = dict(source = source_idx, target = target_idx, value = df_so['count'])
        )])
        fig4.update_layout(title_text="Search Strategy → Outcome", font_size=10)
        fig4.write_html("reports/charts/search_strategy_sankey.html")
        fig4.write_json("reports/charts/search_strategy_sankey.json")
    
    # 5. Sentiment Analysis
    sentiment_data = run_query("SELECT label, COUNT(*) as count FROM sentiment GROUP BY label")
    df_sent = pd.DataFrame(sentiment_data)
    if not df_sent.empty:
        # Standardize labels just in case
        df_sent['label'] = df_sent['label'].str.capitalize()
        fig_sent = px.pie(df_sent, names='label', values='count', title="User Sentiment Breakdown",
                          color='label', 
                          color_discrete_map={'Positive': '#34a853', 'Neutral': '#fbbc05', 'Negative': '#ea4335'})
        fig_sent.update_traces(textposition='inside', textinfo='percent+label')
        fig_sent.write_html("reports/charts/sentiment_analysis.html")
        fig_sent.write_json("reports/charts/sentiment_analysis.json")
        
    # 6. Word Cloud
    text_data = run_query("SELECT cleaned_text FROM feedback WHERE cleaned_text IS NOT NULL")
    if text_data:
        all_text = " ".join([r['cleaned_text'] for r in text_data])
        wc = WordCloud(width=800, height=400, background_color="white", colormap="viridis", max_words=100).generate(all_text)
        svg = wc.to_svg()
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; font-family: 'Inter', sans-serif; background: #fff; }}
                .wc-container {{ text-align: center; width: 100%; max-width: 800px; padding: 20px; }}
                svg {{ width: 100%; height: auto; }}
            </style>
        </head>
        <body>
            <div class="wc-container">
                {svg}
            </div>
        </body>
        </html>
        """
        with open("reports/charts/word_cloud.html", "w") as f:
            f.write(html_content)
    
    # 7. Theme Cluster UMAP Scatter Plot
    try:
        import umap
        has_umap = True
    except ImportError:
        has_umap = False
        print("umap-learn not installed. Skipping UMAP generation.")

    if has_umap and os.path.exists("data/enriched/embeddings_cache.npy") and os.path.exists("data/enriched/corpus_themed.json"):
        embeddings = np.load("data/enriched/embeddings_cache.npy")
        with open("data/enriched/corpus_themed.json", "r") as f:
            corpus = json.load(f)
        
        if len(embeddings) == len(corpus):
            print("Generating UMAP projection (this might take a few moments)...")
            reducer = umap.UMAP(n_components=2, random_state=42)
            umap_coords = reducer.fit_transform(embeddings)
            
            df_umap = pd.DataFrame({
                'x': umap_coords[:, 0],
                'y': umap_coords[:, 1],
                'cluster': [str(c.get('emergent_theme', {}).get('cluster_id', -1)) for c in corpus],
                'theme_label': [c.get('emergent_theme', {}).get('theme_label', 'Noise') for c in corpus]
            })
            
            # Filter out noise and the 'FAHHHHH' theme so the plot only shows the valid theme clusters
            df_umap_filtered = df_umap[
                (~df_umap['theme_label'].isin(['NOISE', 'Noise'])) & 
                (~df_umap['theme_label'].str.contains('FAHHHHH', na=False, case=False))
            ]
            
            fig5 = px.scatter(df_umap_filtered, x='x', y='y', color='theme_label', title="Theme Cluster UMAP Scatter Plot", hover_data=['cluster'])
            fig5.write_html("reports/charts/theme_clusters_umap.html")
            fig5.write_json("reports/charts/theme_clusters_umap.json")
        else:
            print("Embeddings length mismatch.")
    else:
        print("Skipping UMAP - missing dependencies or files.")
        
    # 6. Data Coverage by Source Treemap
    coverage = run_query("SELECT source, COUNT(*) as count FROM feedback GROUP BY source")
    df_cov = pd.DataFrame(coverage)
    if not df_cov.empty:
        df_cov['root'] = 'All Sources'
        fig6 = px.treemap(df_cov, path=['root', 'source'], values='count', title="Data Coverage by Source")
        fig6.write_html("reports/charts/source_coverage.html")
        fig6.write_json("reports/charts/source_coverage.json")
        
    # 7. Memory Cues Remembered vs. Forgotten Stacked Bar
    metadata_cues = run_query("SELECT memory_cues, memory_gaps FROM metadata")
    cue_counts = {}
    gap_counts = {}
    
    for row in metadata_cues:
        cues = parse_list(row['memory_cues'])
        gaps = parse_list(row['memory_gaps'])
        for c in cues: cue_counts[c] = cue_counts.get(c, 0) + 1
        for g in gaps: gap_counts[g] = gap_counts.get(g, 0) + 1

    all_keys = set(cue_counts.keys()).union(set(gap_counts.keys()))
    data_cg = []
    for k in all_keys:
        data_cg.append({"Type": k, "Count": cue_counts.get(k, 0), "Status": "Remembered"})
        data_cg.append({"Type": k, "Count": gap_counts.get(k, 0), "Status": "Forgotten"})

    df_cg = pd.DataFrame(data_cg)
    if not df_cg.empty:
        fig7 = px.bar(df_cg, x="Type", y="Count", color="Status", title="Memory Cues Remembered vs. Forgotten")
        fig7.write_html("reports/charts/cues_vs_gaps.html")
        fig7.write_json("reports/charts/cues_vs_gaps.json")
        
    # 8. Impact vs. Frequency Quadrant Map
    arch_path = "reports/archetype_report.json"
    if os.path.exists(arch_path):
        with open(arch_path, "r") as f:
            arch_data = json.load(f)

        quad_data = []
        for arch, info in arch_data.items():
            if "frequency" in info:
                freq = info["frequency"]["percentage"]
                sev = info["severity"]["avg_score"]
                quad_data.append({"Archetype": arch, "Frequency": freq, "Severity": sev})

        df_quad = pd.DataFrame(quad_data)
        if not df_quad.empty:
            fig8 = px.scatter(df_quad, x="Frequency", y="Severity", text="Archetype", title="Impact vs. Frequency Quadrant Map")
            fig8.add_hline(y=df_quad['Severity'].median(), line_dash="dash", line_color="red")
            fig8.add_vline(x=df_quad['Frequency'].median(), line_dash="dash", line_color="red")
            fig8.update_traces(textposition='top center')
            fig8.write_html("reports/charts/impact_frequency_quadrant.html")
            fig8.write_json("reports/charts/impact_frequency_quadrant.json")

    # Generate Markdown Report
    md_content = """# Memory Cue Analysis Dashboard

This report provides interactive visualizations based on our emergent theme analysis and archetype data.

## Interactive Charts
| # | Chart | Description |
|---|---|---|
| 1 | [Memory Cue Frequency Heatmap](charts/memory_cue_heatmap.html) | Shows which memory cues correspond with which photo categories. |
| 2 | [Archetype Distribution Pie Chart](charts/archetype_distribution.html) | Overall frequency of user archetypes across the corpus. |
| 3 | [Frustration Level by Source](charts/frustration_by_source.html) | Compares user frustration levels across different feedback sources. |
| 4 | [Search Strategy → Outcome Sankey](charts/search_strategy_sankey.html) | Maps search strategies to their ultimate outcome (found vs not found). |
| 5 | [Theme Cluster UMAP Scatter Plot](charts/theme_clusters_umap.html) | High-dimensional embedding reduction to visually represent topic clusters. |
| 6 | [Data Coverage by Source Treemap](charts/source_coverage.html) | Shows the distribution of data sources in the final dataset. |
| 7 | [Memory Cues vs Gaps](charts/cues_vs_gaps.html) | Stacked bar chart showing what users remember vs what they forget. |
| 8 | [Impact vs Frequency Quadrant Map](charts/impact_frequency_quadrant.html) | Quadrant map comparing severity to frequency for each archetype. |

*(Note: Click on the links above to open the interactive Plotly HTML files in your browser).*
"""
    with open("reports/memory_cue_analysis.md", "w") as f:
        f.write(md_content)
        
    print("Done! Reports and charts generated successfully.")

if __name__ == "__main__":
    main()
