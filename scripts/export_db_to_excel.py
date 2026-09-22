"""
scripts/export_db_to_excel.py
Chuyển đổi toàn bộ Database FoodFlow AI thành tập Dataset Excel (.xlsx) chuyên nghiệp.
Mỗi bảng trong SQLite sẽ được xuất thành một Sheet riêng biệt với định dạng đẹp mắt,
kèm theo Sheet 'Overview' tổng hợp mô tả dữ liệu và thống kê.
"""

import os
import sys
import sqlite3
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Đường dẫn DB và Output
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "backend", "foodflow.db")
OUTPUT_PATHS = [
    os.path.join(BASE_DIR, "data", "foodflow_dataset.xlsx"),
    os.path.join(BASE_DIR, "foodflow_dataset.xlsx")
]

TABLE_METADATA = {
    "branches": {
        "title": "Chi Nhánh (Branches)",
        "desc": "Danh mục các chi nhánh nhà hàng/quán thuộc chuỗi FoodFlow."
    },
    "dishes": {
        "title": "Món Ăn & Đồ Uống (Dishes)",
        "desc": "Danh mục 22 món ăn, thức uống, phân loại và đơn giá niêm yết."
    },
    "ingredients": {
        "title": "Nguyên Liệu (Ingredients)",
        "desc": "Danh mục 35 nguyên vật liệu, đơn vị tính, giá vốn, hạn sử dụng và mức tồn kho tối thiểu."
    },
    "recipes": {
        "title": "Định Lượng Món (Recipes)",
        "desc": "Công thức định lượng chi tiết (BOM - Bill of Materials) giữa từng món ăn và nguyên liệu."
    },
    "sales": {
        "title": "Lịch Sử Bán Hàng (Sales)",
        "desc": "Dataset lịch sử giao dịch bán hàng theo ngày, chi nhánh, món ăn, số lượng và doanh thu (2 năm)."
    },
    "inventory": {
        "title": "Tồn Kho Hiện Tại (Inventory)",
        "desc": "Số lượng tồn kho thực tế của từng nguyên liệu tại từng chi nhánh."
    },
    "inventory_batches": {
        "title": "Lô Hàng & Blockchain (Inventory Batches)",
        "desc": "Theo dõi lô nhập hàng, hạn sử dụng, băm mật mã và chữ ký chứng thực Solana On-chain."
    },
    "preorders": {
        "title": "Đơn Đặt Trước (Preorders)",
        "desc": "Danh sách các đơn đặt bàn / đặt món trước của khách hàng theo chi nhánh và ngày."
    },
    "purchase_history": {
        "title": "Lịch Sử Mua Hàng (Purchase History)",
        "desc": "Lịch sử đặt hàng thu mua bổ sung nguyên vật liệu từ nhà cung cấp."
    },
    "calendar": {
        "title": "Lịch & Ngày Lễ (Calendar)",
        "desc": "Dữ liệu lịch 730 ngày kèm cờ ngày cuối tuần, ngày lễ tết phục vụ dự báo nhu cầu."
    }
}

# Thứ tự sắp xếp các Sheet trong Excel
SHEET_ORDER = [
    "branches",
    "dishes",
    "ingredients",
    "recipes",
    "inventory",
    "inventory_batches",
    "preorders",
    "purchase_history",
    "calendar",
    "sales"
]

def export_db_to_excel():
    print(f"Đang kết nối tới Database: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Không tìm thấy file CSDL tại {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Lấy danh sách tất cả các bảng
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    all_tables = [r[0] for r in cur.fetchall()]

    # Sắp xếp các bảng theo thứ tự logic
    ordered_tables = [t for t in SHEET_ORDER if t in all_tables]
    for t in all_tables:
        if t not in ordered_tables:
            ordered_tables.append(t)

    table_data = {}
    summary_rows = []

    print("Đang đọc dữ liệu từ database...")
    for t in ordered_tables:
        df = pd.read_sql_query(f"SELECT * FROM {t}", conn)
        table_data[t] = df
        meta = TABLE_METADATA.get(t, {"title": t, "desc": "Bảng dữ liệu CSDL"})
        summary_rows.append({
            "Mã Bảng (Sheet)": t,
            "Tên Bảng": meta["title"],
            "Số Bản Ghi (Rows)": len(df),
            "Số Cột (Columns)": len(df.columns),
            "Danh Sách Cột": ", ".join(df.columns),
            "Mô Tả": meta["desc"]
        })
        print(f"  + Bảng '{t}': {len(df):,} dòng, {len(df.columns)} cột")

    conn.close()

    overview_df = pd.DataFrame(summary_rows)

    # Xuất ra file Excel
    primary_output = OUTPUT_PATHS[0]
    print(f"\nĐang ghi file Excel: {primary_output} ...")
    
    with pd.ExcelWriter(primary_output, engine="openpyxl") as writer:
        # 1. Sheet Overview
        overview_df.to_excel(writer, sheet_name="Overview", index=False)
        
        # 2. Các sheet dữ liệu
        for t in ordered_tables:
            table_data[t].to_excel(writer, sheet_name=t, index=False)

        # Định dạng giao diện các sheets qua openpyxl
        wb = writer.book
        
        # Style tokens
        header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid") # Navy Blue
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        regular_font = Font(name="Calibri", size=10)
        bold_font = Font(name="Calibri", size=10, bold=True)
        thin_border = Border(
            left=Side(style='thin', color='D9D9D9'),
            right=Side(style='thin', color='D9D9D9'),
            top=Side(style='thin', color='D9D9D9'),
            bottom=Side(style='thin', color='D9D9D9')
        )
        accent_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")

        # Format Sheet Overview
        ws_over = wb["Overview"]
        ws_over.views.sheetView[0].showGridLines = True
        
        for col_idx in range(1, len(overview_df.columns) + 1):
            cell = ws_over.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        for row_idx in range(2, len(overview_df) + 2):
            for col_idx in range(1, len(overview_df.columns) + 1):
                cell = ws_over.cell(row=row_idx, column=col_idx)
                cell.font = regular_font
                cell.border = thin_border
                if col_idx in [1, 3, 4]:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    if col_idx == 1:
                        cell.font = bold_font
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center")

        ws_over.row_dimensions[1].height = 28
        for row in range(2, len(overview_df) + 2):
            ws_over.row_dimensions[row].height = 24

        ws_over.column_dimensions['A'].width = 20
        ws_over.column_dimensions['B'].width = 30
        ws_over.column_dimensions['C'].width = 20
        ws_over.column_dimensions['D'].width = 18
        ws_over.column_dimensions['E'].width = 45
        ws_over.column_dimensions['F'].width = 55

        # Format Data Sheets
        for t in ordered_tables:
            ws = wb[t]
            ws.views.sheetView[0].showGridLines = True
            ws.freeze_panes = "A2"  # Cố định header
            df = table_data[t]
            
            ws.row_dimensions[1].height = 26

            for col_idx in range(1, len(df.columns) + 1):
                cell = ws.cell(row=1, column=col_idx)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")

            # Định dạng độ rộng cột vừa vặn nội dung (tối đa 40 ký tự)
            for col_idx, col_name in enumerate(df.columns, 1):
                max_len = len(str(col_name))
                # Lấy mẫu tối đa 100 dòng đầu để tính width tối ưu hiệu năng
                sample_vals = df[col_name].dropna().head(100).astype(str)
                if len(sample_vals) > 0:
                    val_max = sample_vals.map(len).max()
                    max_len = max(max_len, val_max)
                col_letter = get_column_letter(col_idx)
                ws.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 40)

            # Căn lề dữ liệu cơ bản
            # Đối với bảng sales lớn (48k dòng), chỉ format viền / font nhanh tránh quá tải
            if len(df) <= 5000:
                for row_idx in range(2, len(df) + 2):
                    for col_idx in range(1, len(df.columns) + 1):
                        cell = ws.cell(row=row_idx, column=col_idx)
                        cell.font = regular_font
                        cell.border = thin_border

    print(f"Xuat thanh cong: {primary_output}")

    # Copy / Save file sang thu muc goc project neu khac nhau
    import shutil
    shutil.copy2(primary_output, OUTPUT_PATHS[1])
    print(f"Da dong bo ban copy den: {OUTPUT_PATHS[1]}")

    file_size_mb = os.path.getsize(primary_output) / (1024 * 1024)
    print(f"Kich thuoc file Excel: {file_size_mb:.2f} MB")
    print("HOÀN TẤT CHUYỂN ĐỔI DATABASE THÀNH DATASET EXCEL!")

if __name__ == "__main__":
    export_db_to_excel()
