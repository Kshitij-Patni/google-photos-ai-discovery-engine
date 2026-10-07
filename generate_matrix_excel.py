import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def create_prioritization_excel():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Prioritization Matrix"
    ws.views.sheetView[0].showGridLines = True

    # Palette
    NAVY_HEADER = "1A365D"       # Deep Executive Navy
    SUBHEADER_FILL = "F0F4F8"    # Soft Gray-Blue
    ACCENT_BLUE = "2B6CB0"       # Professional Steel Blue
    CARD_BG = "F7FAFC"           # Off-white card fill
    BORDER_COLOR = "CBD5E0"      # Crisp light border
    P0_FILL = "FED7D7"           # Soft Red for P0
    P0_FONT = "9B2C2C"           # Dark Red
    P1_FILL = "FEEBC8"           # Soft Orange for P1
    P1_FONT = "9C4221"           # Dark Orange
    P2_FILL = "FEFCBF"           # Soft Yellow for P2
    P2_FONT = "975A16"           # Dark Yellow

    thin_border = Border(
        left=Side(style='thin', color=BORDER_COLOR),
        right=Side(style='thin', color=BORDER_COLOR),
        top=Side(style='thin', color=BORDER_COLOR),
        bottom=Side(style='thin', color=BORDER_COLOR)
    )
    double_bottom_border = Border(
        left=Side(style='thin', color=BORDER_COLOR),
        right=Side(style='thin', color=BORDER_COLOR),
        top=Side(style='thin', color=BORDER_COLOR),
        bottom=Side(style='double', color="1A202C")
    )

    # 1. Title Block
    ws.merge_cells("B2:J2")
    ws["B2"] = "GOOGLE PHOTOS AI DISCOVERY ENGINE — SEGMENT PRIORITIZATION MATRIX"
    ws["B2"].font = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
    ws["B2"].fill = PatternFill(start_color=NAVY_HEADER, end_color=NAVY_HEADER, fill_type="solid")
    ws["B2"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 36

    ws.merge_cells("B3:J3")
    ws["B3"] = "Quantitative Evaluation of 5,682 User Feedback Records across Play Store, App Store, Reddit, and Support Forums"
    ws["B3"].font = Font(name="Calibri", size=10, italic=True, color="4A5568")
    ws["B3"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[3].height = 20

    # 2. Executive KPI Summary Cards (Row 5 to 6)
    kpis = [
        ("B", "C", "TOTAL USER RECORDS", "5,682", "Multi-platform dataset"),
        ("D", "E", "PRIMARY TARGET SHARE", "69.8%", "The Frustrated Searcher (S1)"),
        ("F", "G", "PEAK FAILURE RATE", "81.3%", "Worst search drop-off rate"),
        ("H", "J", "STRATEGIC PRIORITY", "S1: Immediate Focus", "Highest ROI & Google One Retention")
    ]

    for start_col, end_col, label, val, sub in kpis:
        cell_range = f"{start_col}5:{end_col}5"
        ws.merge_cells(cell_range)
        ws[f"{start_col}5"] = label
        ws[f"{start_col}5"].font = Font(name="Calibri", size=8, bold=True, color="718096")
        ws[f"{start_col}5"].alignment = Alignment(horizontal="center", vertical="center")
        ws[f"{start_col}5"].fill = PatternFill(start_color=CARD_BG, end_color=CARD_BG, fill_type="solid")

        cell_range_val = f"{start_col}6:{end_col}6"
        ws.merge_cells(cell_range_val)
        ws[f"{start_col}6"] = val
        ws[f"{start_col}6"].font = Font(name="Calibri", size=14, bold=True, color=NAVY_HEADER)
        ws[f"{start_col}6"].alignment = Alignment(horizontal="center", vertical="center")
        ws[f"{start_col}6"].fill = PatternFill(start_color=CARD_BG, end_color=CARD_BG, fill_type="solid")

        # apply borders to card cells
        cols = [start_col] if start_col == end_col else [chr(c) for c in range(ord(start_col), ord(end_col)+1)]
        for c in cols:
            for r in [5, 6]:
                ws[f"{c}{r}"].border = thin_border

    ws.row_dimensions[5].height = 18
    ws.row_dimensions[6].height = 28

    # 3. Main Table Header (Row 8)
    headers = [
        ("B", "Segment ID"),
        ("C", "Target User Segment"),
        ("D", "Primary Pain Theme"),
        ("E", "Audience Share"),
        ("F", "Search Failure Rate"),
        ("G", "Severity Score"),
        ("H", "Google One Impact"),
        ("I", "Weighted Score"),
        ("J", "Strategic Priority")
    ]

    ws.row_dimensions[8].height = 26
    for col, h in headers:
        cell = ws[f"{col}8"]
        cell.value = h
        cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color=ACCENT_BLUE, end_color=ACCENT_BLUE, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    # 4. Main Data Rows (Row 9 to 12)
    # Weights for formula:
    # Audience Share (Col E): 40%
    # Search Failure Rate (Col F): 30%
    # Severity Score (Col G): 20%
    # Monetization Impact relative value: S1=1.0, S2=0.6, S3=0.4, S4=0.2 (10%)
    data = [
        ("S1", "Segment 1: The Frustrated Searcher", "Keyword Mismatch (Associative vs Literal)", 0.698, 0.813, 0.849, "Core Paid Users (High LTV)", 1.0, "🔴 P0 (Immediate Focus)", P0_FILL, P0_FONT),
        ("S2", "Segment 2: The Organized Migrator", "Album Fragmentation & Folder Loss", 0.111, 0.663, 0.650, "Moderate Churn Risk", 0.6, "🔴 P0 (Fast Follow)", P0_FILL, P0_FONT),
        ("S3", "Segment 3: The Memory Fader", "Temporal & Spatial Decay", 0.036, 0.728, 0.700, "Casual / Growing", 0.4, "🟠 P1 (Phase 2)", P1_FILL, P1_FONT),
        ("S4", "Segment 4: The Legacy Keeper", "Zero Metadata & Face Match Fails", 0.034, 0.722, 0.600, "Niche / Low", 0.2, "🟡 P2 (Backlog)", P2_FILL, P2_FONT)
    ]

    for idx, row in enumerate(data, start=9):
        ws.row_dimensions[idx].height = 24
        
        ws[f"B{idx}"] = row[0]
        ws[f"B{idx}"].alignment = Alignment(horizontal="center", vertical="center")
        ws[f"B{idx}"].font = Font(name="Calibri", bold=True, size=10)
        
        ws[f"C{idx}"] = row[1]
        ws[f"C{idx}"].alignment = Alignment(horizontal="left", vertical="center")
        ws[f"C{idx}"].font = Font(name="Calibri", size=10, bold=(idx == 9))
        
        ws[f"D{idx}"] = row[2]
        ws[f"D{idx}"].alignment = Alignment(horizontal="left", vertical="center")
        ws[f"D{idx}"].font = Font(name="Calibri", size=10)
        
        ws[f"E{idx}"] = row[3]
        ws[f"E{idx}"].number_format = "0.0%"
        ws[f"E{idx}"].alignment = Alignment(horizontal="right", vertical="center")
        ws[f"E{idx}"].font = Font(name="Calibri", size=10, bold=(idx == 9))
        
        ws[f"F{idx}"] = row[4]
        ws[f"F{idx}"].number_format = "0.0%"
        ws[f"F{idx}"].alignment = Alignment(horizontal="right", vertical="center")
        ws[f"F{idx}"].font = Font(name="Calibri", size=10, bold=(idx == 9))
        
        ws[f"G{idx}"] = row[5]
        ws[f"G{idx}"].number_format = "0.000"
        ws[f"G{idx}"].alignment = Alignment(horizontal="right", vertical="center")
        ws[f"G{idx}"].font = Font(name="Calibri", size=10, bold=(idx == 9))
        
        ws[f"H{idx}"] = row[6]
        ws[f"H{idx}"].alignment = Alignment(horizontal="center", vertical="center")
        ws[f"H{idx}"].font = Font(name="Calibri", size=10)
        
        # Weighted Score Formula: (Share*40% + Failure*30% + Severity*20% + MonetizationNorm*10%) * 100
        monetize_val = row[7]
        ws[f"I{idx}"] = f"=ROUND((E{idx}*0.40 + F{idx}*0.30 + G{idx}*0.20 + {monetize_val}*0.10)*100, 1)"
        ws[f"I{idx}"].number_format = "0.0"
        ws[f"I{idx}"].alignment = Alignment(horizontal="right", vertical="center")
        ws[f"I{idx}"].font = Font(name="Calibri", size=11, bold=True, color=NAVY_HEADER if idx > 9 else "9B2C2C")

        ws[f"J{idx}"] = row[8]
        ws[f"J{idx}"].alignment = Alignment(horizontal="center", vertical="center")
        ws[f"J{idx}"].font = Font(name="Calibri", size=10, bold=True, color=row[10])
        ws[f"J{idx}"].fill = PatternFill(start_color=row[9], end_color=row[9], fill_type="solid")

        # Borders and highlight for S1
        for col_letter in ["B", "C", "D", "E", "F", "G", "H", "I"]:
            ws[f"{col_letter}{idx}"].border = thin_border
            if idx == 9: # S1 winner highlight
                ws[f"{col_letter}{idx}"].fill = PatternFill(start_color="FFF5F5", end_color="FFF5F5", fill_type="solid")
        ws[f"J{idx}"].border = thin_border

    # 5. Methodology & Weighting Footnote Box (Rows 14 to 19)
    ws.merge_cells("B14:J14")
    ws["B14"] = "📐 SCORING MODEL & WEIGHTING METHODOLOGY"
    ws["B14"].font = Font(name="Calibri", size=10, bold=True, color=NAVY_HEADER)
    ws["B14"].fill = PatternFill(start_color=SUBHEADER_FILL, end_color=SUBHEADER_FILL, fill_type="solid")
    ws["B14"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws["B14"].border = thin_border
    ws.row_dimensions[14].height = 22

    method_notes = [
        ("Audience Share (40% Weight):", "Prioritizes total user volume affected across 5,682 sample records. S1 represents nearly 70% of the entire user base."),
        ("Search Failure Rate (30% Weight):", "Measures severity of task breakdown. S1 experiences 81.3% search failure, highest across all archetypes."),
        ("Severity Score (20% Weight):", "Reflects emotional dissatisfaction and frustration score (0.0 to 1.0) derived from NLP sentiment analysis."),
        ("Google One Impact (10% Weight):", "Business value weighting protecting high-LTV subscribers (users with 5k-20k photos paying for recurring storage tiers).")
    ]

    for idx, (title, desc) in enumerate(method_notes, start=15):
        ws.row_dimensions[idx].height = 18
        ws[f"B{idx}"] = title
        ws[f"B{idx}"].font = Font(name="Calibri", size=9, bold=True, color="2D3748")
        ws[f"B{idx}"].alignment = Alignment(horizontal="left", vertical="center")
        
        ws.merge_cells(f"C{idx}:J{idx}")
        ws[f"C{idx}"] = desc
        ws[f"C{idx}"].font = Font(name="Calibri", size=9, color="4A5568")
        ws[f"C{idx}"].alignment = Alignment(horizontal="left", vertical="center")

        for col_l in ["B", "C", "D", "E", "F", "G", "H", "I", "J"]:
            ws[f"{col_l}{idx}"].border = thin_border

    # Column Widths
    col_widths = {
        "A": 3,
        "B": 14,
        "C": 36,
        "D": 38,
        "E": 16,
        "F": 20,
        "G": 16,
        "H": 25,
        "I": 16,
        "J": 26,
        "K": 3
    }
    for col, width in col_widths.items():
        ws.column_dimensions[col].width = width

    output_path = "/Users/shree/Desktop/Next Leap Prodman/Final project - Google photos/Google Photos AI Discovery Engine/Segment_Prioritization_Matrix.xlsx"
    wb.save(output_path)
    print(f"Excel created successfully at {output_path}")

if __name__ == "__main__":
    create_prioritization_excel()
