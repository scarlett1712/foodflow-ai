"""
scripts/generate_hadong_buffet_data.py
Sinh bộ dữ liệu mẫu F&B mô hình Buffet Lẩu Nướng cho chi nhánh mới: FoodFlow Hà Đông.
Thời gian: Từ 01/06/2026 đến 27/09/2026 (119 ngày, kết thúc vào hôm qua).
Khi tải lên hệ thống, AI sẽ tự động dự báo bắt đầu từ 28/09/2026 (Ngày mai thực tế).
"""

import os
import sys
import csv
import random
from datetime import datetime, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

random.seed(42)

DISHES = [
    {"id": "BUFFET_01", "name": "Set Buffet Nướng Lẩu Classic", "category": "Set Buffet", "price": 229000, "base": 60, "wknd_mult": 1.7},
    {"id": "BUFFET_02", "name": "Set Buffet Nướng Lẩu Premium", "category": "Set Buffet", "price": 299000, "base": 85, "wknd_mult": 1.8},
    {"id": "BUFFET_03", "name": "Set Buffet Hải Sản Thượng Hạng", "category": "Set Buffet", "price": 389000, "base": 40, "wknd_mult": 1.9},
    {"id": "DISH_01", "name": "Ba Chỉ Bò Mỹ Nướng Bulgogi", "category": "Thịt Nướng & Lẩu", "price": 89000, "base": 45, "wknd_mult": 1.6},
    {"id": "DISH_02", "name": "Dẻ Sườn Bò Ướp Sốt Chum", "category": "Thịt Nướng & Lẩu", "price": 119000, "base": 35, "wknd_mult": 1.7},
    {"id": "DISH_03", "name": "Nầm Heo Nướng Sốt Chao", "category": "Thịt Nướng & Lẩu", "price": 79000, "base": 30, "wknd_mult": 1.6},
    {"id": "DISH_04", "name": "Bạch Tuộc Nướng Sa Tế", "category": "Hải Sản", "price": 89000, "base": 30, "wknd_mult": 1.8},
    {"id": "DISH_05", "name": "Tôm Càng Xanh Nướng Muối Ớt", "category": "Hải Sản", "price": 115000, "base": 25, "wknd_mult": 1.8},
    {"id": "DISH_06", "name": "Nước Lẩu Thái Tomyum Chua Cay", "category": "Món Nước", "price": 59000, "base": 45, "wknd_mult": 1.7},
    {"id": "DISH_07", "name": "Nấm Kim Châm & Rau Lẩu Tổng Hợp", "category": "Đồ Ăn Nhẹ", "price": 35000, "base": 50, "wknd_mult": 1.6},
    {"id": "DRINK_01", "name": "Bia Tươi Tiger Bạc", "category": "Đồ Uống", "price": 35000, "base": 120, "wknd_mult": 2.0},
    {"id": "DRINK_02", "name": "Trà Hoa Cúc Mật Ong", "category": "Đồ Uống", "price": 28000, "base": 60, "wknd_mult": 1.7},
]

# Công thức định lượng (Recipes / BOM) cho từng món/set buffet
RECIPES = [
    # Set Buffet Classic
    {"dish_name": "Set Buffet Nướng Lẩu Classic", "dish_price": 229000, "ingredient_name": "Ba chỉ bò Mỹ đông lạnh", "quantity": 0.25, "unit": "kg", "cost_per_unit": 185000},
    {"dish_name": "Set Buffet Nướng Lẩu Classic", "dish_price": 229000, "ingredient_name": "Thịt ba chỉ heo tươi", "quantity": 0.20, "unit": "kg", "cost_per_unit": 130000},
    {"dish_name": "Set Buffet Nướng Lẩu Classic", "dish_price": 229000, "ingredient_name": "Nấm kim châm tươi", "quantity": 0.15, "unit": "kg", "cost_per_unit": 35000},
    {"dish_name": "Set Buffet Nướng Lẩu Classic", "dish_price": 229000, "ingredient_name": "Rau lẩu thập cẩm", "quantity": 0.20, "unit": "kg", "cost_per_unit": 20000},
    {"dish_name": "Set Buffet Nướng Lẩu Classic", "dish_price": 229000, "ingredient_name": "Cốt lẩu Tomyum Thái", "quantity": 0.08, "unit": "lít", "cost_per_unit": 65000},

    # Set Buffet Premium
    {"dish_name": "Set Buffet Nướng Lẩu Premium", "dish_price": 299000, "ingredient_name": "Ba chỉ bò Mỹ đông lạnh", "quantity": 0.25, "unit": "kg", "cost_per_unit": 185000},
    {"dish_name": "Set Buffet Nướng Lẩu Premium", "dish_price": 299000, "ingredient_name": "Dẻ sườn bò rút xương", "quantity": 0.18, "unit": "kg", "cost_per_unit": 280000},
    {"dish_name": "Set Buffet Nướng Lẩu Premium", "dish_price": 299000, "ingredient_name": "Bạch tuộc tươi sống", "quantity": 0.15, "unit": "kg", "cost_per_unit": 160000},
    {"dish_name": "Set Buffet Nướng Lẩu Premium", "dish_price": 299000, "ingredient_name": "Nấm kim châm tươi", "quantity": 0.15, "unit": "kg", "cost_per_unit": 35000},
    {"dish_name": "Set Buffet Nướng Lẩu Premium", "dish_price": 299000, "ingredient_name": "Sốt ướp Bulgogi Hàn Quốc", "quantity": 0.05, "unit": "lít", "cost_per_unit": 70000},

    # Set Buffet Hải Sản
    {"dish_name": "Set Buffet Hải Sản Thượng Hạng", "dish_price": 389000, "ingredient_name": "Tôm càng xanh tươi", "quantity": 0.25, "unit": "kg", "cost_per_unit": 240000},
    {"dish_name": "Set Buffet Hải Sản Thượng Hạng", "dish_price": 389000, "ingredient_name": "Bạch tuộc tươi sống", "quantity": 0.20, "unit": "kg", "cost_per_unit": 160000},
    {"dish_name": "Set Buffet Hải Sản Thượng Hạng", "dish_price": 389000, "ingredient_name": "Dẻ sườn bò rút xương", "quantity": 0.15, "unit": "kg", "cost_per_unit": 280000},
    {"dish_name": "Set Buffet Hải Sản Thượng Hạng", "dish_price": 389000, "ingredient_name": "Muối ớt xanh Nha Trang", "quantity": 0.04, "unit": "lít", "cost_per_unit": 50000},

    # Món nướng lẻ
    {"dish_name": "Ba Chỉ Bò Mỹ Nướng Bulgogi", "dish_price": 89000, "ingredient_name": "Ba chỉ bò Mỹ đông lạnh", "quantity": 0.20, "unit": "kg", "cost_per_unit": 185000},
    {"dish_name": "Ba Chỉ Bò Mỹ Nướng Bulgogi", "dish_price": 89000, "ingredient_name": "Sốt ướp Bulgogi Hàn Quốc", "quantity": 0.04, "unit": "lít", "cost_per_unit": 70000},

    {"dish_name": "Dẻ Sườn Bò Ướp Sốt Chum", "dish_price": 119000, "ingredient_name": "Dẻ sườn bò rút xương", "quantity": 0.20, "unit": "kg", "cost_per_unit": 280000},
    {"dish_name": "Dẻ Sườn Bò Ướp Sốt Chum", "dish_price": 119000, "ingredient_name": "Sốt ướp Bulgogi Hàn Quốc", "quantity": 0.04, "unit": "lít", "cost_per_unit": 70000},

    {"dish_name": "Nầm Heo Nướng Sốt Chao", "dish_price": 79000, "ingredient_name": "Nầm heo tươi", "quantity": 0.20, "unit": "kg", "cost_per_unit": 140000},
    {"dish_name": "Nầm Heo Nướng Sốt Chao", "dish_price": 79000, "ingredient_name": "Chao môn đỏ pha sốt", "quantity": 0.03, "unit": "hũ", "cost_per_unit": 25000},

    {"dish_name": "Bạch Tuộc Nướng Sa Tế", "dish_price": 89000, "ingredient_name": "Bạch tuộc tươi sống", "quantity": 0.22, "unit": "kg", "cost_per_unit": 160000},
    {"dish_name": "Bạch Tuộc Nướng Sa Tế", "dish_price": 89000, "ingredient_name": "Sa tế tôm cay đặc biệt", "quantity": 0.03, "unit": "lít", "cost_per_unit": 60000},

    {"dish_name": "Tôm Càng Xanh Nướng Muối Ớt", "dish_price": 115000, "ingredient_name": "Tôm càng xanh tươi", "quantity": 0.25, "unit": "kg", "cost_per_unit": 240000},
    {"dish_name": "Tôm Càng Xanh Nướng Muối Ớt", "dish_price": 115000, "ingredient_name": "Muối ớt xanh Nha Trang", "quantity": 0.03, "unit": "lít", "cost_per_unit": 50000},

    {"dish_name": "Nước Lẩu Thái Tomyum Chua Cay", "dish_price": 59000, "ingredient_name": "Cốt lẩu Tomyum Thái", "quantity": 0.15, "unit": "lít", "cost_per_unit": 65000},
    {"dish_name": "Nước Lẩu Thái Tomyum Chua Cay", "dish_price": 59000, "ingredient_name": "Sả chanh ớt tươi", "quantity": 0.05, "unit": "kg", "cost_per_unit": 25000},

    {"dish_name": "Nấm Kim Châm & Rau Lẩu Tổng Hợp", "dish_price": 35000, "ingredient_name": "Nấm kim châm tươi", "quantity": 0.15, "unit": "kg", "cost_per_unit": 35000},
    {"dish_name": "Nấm Kim Châm & Rau Lẩu Tổng Hợp", "dish_price": 35000, "ingredient_name": "Rau lẩu thập cẩm", "quantity": 0.25, "unit": "kg", "cost_per_unit": 20000},

    {"dish_name": "Bia Tươi Tiger Bạc", "dish_price": 35000, "ingredient_name": "Bia lon Tiger Crystal", "quantity": 1.0, "unit": "lon", "cost_per_unit": 18500},
    {"dish_name": "Trà Hoa Cúc Mật Ong", "dish_price": 28000, "ingredient_name": "Trà túi lọc hoa cúc", "quantity": 1.0, "unit": "gói", "cost_per_unit": 4000},
    {"dish_name": "Trà Hoa Cúc Mật Ong", "dish_price": 28000, "ingredient_name": "Mật ong rừng nguyên chất", "quantity": 0.02, "unit": "lít", "cost_per_unit": 180000},
]

def generate_datasets():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(data_dir, exist_ok=True)

    sales_csv = os.path.join(data_dir, "foodflow_hadong_buffet_sales.csv")
    recipes_csv = os.path.join(data_dir, "foodflow_hadong_buffet_recipes.csv")

    end_date = datetime(2026, 9, 27)
    start_date = datetime(2026, 6, 1) # 119 ngày
    total_days = (end_date - start_date).days + 1

    sales_rows = []
    for day_idx in range(total_days):
        cur_date = start_date + timedelta(days=day_idx)
        date_str = cur_date.strftime("%Y-%m-%d")
        dow = cur_date.weekday()
        is_weekend = dow in [4, 5, 6] # Thứ 6, Thứ 7, Chủ Nhật

        # Tăng trưởng tự nhiên của quán mới mở (+25% sau 4 tháng)
        growth_trend = 0.85 + 0.25 * (day_idx / total_days)

        for d in DISHES:
            wknd_factor = d["wknd_mult"] if is_weekend else 1.0
            noise = random.gauss(1.0, 0.08)
            qty = int(round(d["base"] * wknd_factor * growth_trend * noise))
            qty = max(qty, 5)
            rev = qty * d["price"]

            sales_rows.append({
                "date": date_str,
                "branch_id": "FoodFlow Hà Đông",
                "dish_id": d["id"],
                "dish_name": d["name"],
                "category": d["category"],
                "quantity": qty,
                "revenue": rev
            })

    # 1. Ghi file Sales CSV
    with open(sales_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "branch_id", "dish_id", "dish_name", "category", "quantity", "revenue"])
        writer.writeheader()
        writer.writerows(sales_rows)

    # 2. Ghi file Recipes CSV
    with open(recipes_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["dish_name", "dish_price", "ingredient_name", "quantity", "unit", "cost_per_unit"])
        writer.writeheader()
        writer.writerows(RECIPES)

    print("=" * 70)
    print("ĐÃ SINH THÀNH CÔNG BỘ DỮ LIỆU MẪU BUFFET CHO CHI NHÁNH HÀ ĐÔNG:")
    print(f"1. File Doanh số bán hàng: {sales_csv}")
    print(f"   -> {len(sales_rows)} dòng (từ {start_date.strftime('%Y-%m-%d')} đến {end_date.strftime('%Y-%m-%d')}, 12 món)")
    print(f"2. File Công thức định lượng: {recipes_csv}")
    print(f"   -> {len(RECIPES)} công thức định lượng (BOM)")
    print("=" * 70)

if __name__ == "__main__":
    generate_datasets()
