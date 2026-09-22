"""
scripts/generate_data.py
Sinh dữ liệu quy mô lớn cho FoodFlow AI (3 Chi Nhánh, 22 Món Ăn/Đồ Uống, 35 Nguyên Liệu, 2 Năm Lịch Sử ~48,000+ dòng):
- Chi nhánh 1: FoodFlow Quận 1 (Bistro & Cơm Trưa Văn Phòng)
- Chi nhánh 2: FoodFlow Cầu Giấy (Trà Sữa & Ăn Vặt Giới Trẻ)
- Chi nhánh 3: FoodFlow Tây Hồ (Ẩm Thực Truyền Thống Gia Đình)

v2 — Cải thiện độ phức tạp dữ liệu:
- Nhiễu Gauss tăng từ 5% → 12%
- Event spikes (4 loại sự kiện bất thường) + cột event_flag
- Tương tác phi tuyến branch_type × weekend × weather
- Tết Nguyên Đán 2025/2026 (hệ số tất niên + mở cửa xuyên Tết)
"""

import os
import sys
import csv
import json
import math
import random
import sqlite3
from datetime import datetime, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

random.seed(42)

# Import vn_calendar từ backend (dùng chung VIETNAM_HOLIDAYS, Tết multiplier)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.app.forecasting.vn_calendar import (
    VIETNAM_HOLIDAYS,
    get_tet_date,
    get_tet_synthetic_multiplier,
)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "foodflow.db")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# 1. Danh sách Chi Nhánh (Branches)
BRANCHES = [
    {"id": "BRANCH_01", "name": "FoodFlow Quận 1", "address": "120 Lê Lợi, Bến Thành, Quận 1, TP.HCM", "type": "Bistro & Cơm Văn Phòng"},
    {"id": "BRANCH_02", "name": "FoodFlow Cầu Giấy", "address": "88 Cầu Giấy, Quan Hoa, Cầu Giấy, Hà Nội", "type": "Trà Sữa & Ăn Vặt Sinh Viên"},
    {"id": "BRANCH_03", "name": "FoodFlow Tây Hồ", "address": "45 Xuân Diệu, Quảng An, Tây Hồ, Hà Nội", "type": "Ẩm Thực Truyền Thống & Gia Đình"},
]

# Mapping branch_id → branch_type cho tương tác phi tuyến
BRANCH_TYPE_MAP = {
    "BRANCH_01": "bistro",
    "BRANCH_02": "tra_sua",
    "BRANCH_03": "am_thuc_truyen_thong",
}

# 2. Danh mục 22 Món Ăn & Đồ Uống (Dishes)
DISHES = [
    # Phở & Bún
    {"id": "D01", "name": "Phở Bò Tái Nạm", "category": "Phở & Bún", "price": 60000, "base_sales": 80, "weekend_mult": 1.45, "weekday_mult": 0.9, "branch_weights": {"BRANCH_01": 1.1, "BRANCH_02": 0.6, "BRANCH_03": 1.4}},
    {"id": "D02", "name": "Phở Gà Ta Lá Chanh", "category": "Phở & Bún", "price": 55000, "base_sales": 65, "weekend_mult": 1.35, "weekday_mult": 0.95, "branch_weights": {"BRANCH_01": 1.0, "BRANCH_02": 0.5, "BRANCH_03": 1.3}},
    {"id": "D03", "name": "Bún Chả Hà Nội", "category": "Phở & Bún", "price": 55000, "base_sales": 70, "weekend_mult": 1.3, "weekday_mult": 1.1, "branch_weights": {"BRANCH_01": 1.2, "BRANCH_02": 0.7, "BRANCH_03": 1.3}},
    {"id": "D04", "name": "Bún Bò Huế Cốt Đậm", "category": "Phở & Bún", "price": 65000, "base_sales": 60, "weekend_mult": 1.4, "weekday_mult": 0.9, "branch_weights": {"BRANCH_01": 1.1, "BRANCH_02": 0.6, "BRANCH_03": 1.3}},
    {"id": "D05", "name": "Bún Thịt Nướng Chả Giò", "category": "Phở & Bún", "price": 50000, "base_sales": 55, "weekend_mult": 1.2, "weekday_mult": 1.05, "branch_weights": {"BRANCH_01": 1.2, "BRANCH_02": 0.8, "BRANCH_03": 1.0}},
    
    # Cơm & Bánh Mì
    {"id": "D06", "name": "Cơm Gà Xối Mỡ Giòn Da", "category": "Cơm & Bánh Mì", "price": 52000, "base_sales": 85, "weekend_mult": 0.9, "weekday_mult": 1.25, "branch_weights": {"BRANCH_01": 1.4, "BRANCH_02": 1.1, "BRANCH_03": 0.7}},
    {"id": "D07", "name": "Cơm Rang Dưa Bò Hà Nội", "category": "Cơm & Bánh Mì", "price": 55000, "base_sales": 65, "weekend_mult": 0.95, "weekday_mult": 1.2, "branch_weights": {"BRANCH_01": 1.3, "BRANCH_02": 0.9, "BRANCH_03": 0.8}},
    {"id": "D08", "name": "Cơm Tấm Sườn Bì Chả", "category": "Cơm & Bánh Mì", "price": 55000, "base_sales": 75, "weekend_mult": 1.05, "weekday_mult": 1.2, "branch_weights": {"BRANCH_01": 1.5, "BRANCH_02": 0.8, "BRANCH_03": 0.8}},
    {"id": "D09", "name": "Bánh Mì Thịt Nướng Giòn", "category": "Cơm & Bánh Mì", "price": 35000, "base_sales": 70, "weekend_mult": 0.85, "weekday_mult": 1.25, "branch_weights": {"BRANCH_01": 1.4, "BRANCH_02": 1.3, "BRANCH_03": 0.6}},
    {"id": "D10", "name": "Bánh Mì Chảo Thập Cẩm", "category": "Cơm & Bánh Mì", "price": 48000, "base_sales": 45, "weekend_mult": 1.4, "weekday_mult": 0.9, "branch_weights": {"BRANCH_01": 1.1, "BRANCH_02": 1.2, "BRANCH_03": 0.8}},

    # Ăn Vặt & Khai Vị
    {"id": "D11", "name": "Khoai Tây Chiên Bơ Tỏi", "category": "Ăn Vặt", "price": 32000, "base_sales": 50, "weekend_mult": 1.6, "weekday_mult": 0.8, "branch_weights": {"BRANCH_01": 0.8, "BRANCH_02": 1.8, "BRANCH_03": 0.7}},
    {"id": "D12", "name": "Nem Rán Hà Nội (3 Cuốn)", "category": "Ăn Vặt", "price": 35000, "base_sales": 40, "weekend_mult": 1.3, "weekday_mult": 0.95, "branch_weights": {"BRANCH_01": 0.9, "BRANCH_02": 0.9, "BRANCH_03": 1.4}},
    {"id": "D13", "name": "Gà Popcorn Giòn Cay", "category": "Ăn Vặt", "price": 38000, "base_sales": 55, "weekend_mult": 1.5, "weekday_mult": 0.85, "branch_weights": {"BRANCH_01": 0.7, "BRANCH_02": 1.9, "BRANCH_03": 0.6}},
    {"id": "D14", "name": "Salad Ức Gà Sốt Mè Rang", "category": "Ăn Vặt", "price": 45000, "base_sales": 35, "weekend_mult": 0.9, "weekday_mult": 1.2, "branch_weights": {"BRANCH_01": 1.6, "BRANCH_02": 0.8, "BRANCH_03": 0.9}},

    # Cà Phê
    {"id": "D15", "name": "Cà Phê Sữa Đá Sài Gòn", "category": "Cà Phê", "price": 28000, "base_sales": 130, "weekend_mult": 1.1, "weekday_mult": 1.35, "branch_weights": {"BRANCH_01": 1.6, "BRANCH_02": 1.0, "BRANCH_03": 1.0}},
    {"id": "D16", "name": "Bạc Xỉu Đá Ngọt Ngào", "category": "Cà Phê", "price": 32000, "base_sales": 80, "weekend_mult": 1.2, "weekday_mult": 1.1, "branch_weights": {"BRANCH_01": 1.3, "BRANCH_02": 1.4, "BRANCH_03": 0.8}},
    {"id": "D17", "name": "Cà Phê Muối Xứ Huế", "category": "Cà Phê", "price": 35000, "base_sales": 70, "weekend_mult": 1.35, "weekday_mult": 1.1, "branch_weights": {"BRANCH_01": 1.2, "BRANCH_02": 1.5, "BRANCH_03": 0.9}},
    {"id": "D18", "name": "Americano Đá Tươi Mát", "category": "Cà Phê", "price": 30000, "base_sales": 50, "weekend_mult": 0.9, "weekday_mult": 1.3, "branch_weights": {"BRANCH_01": 1.7, "BRANCH_02": 0.7, "BRANCH_03": 0.9}},

    # Trà & Đồ Uống Trái Cây
    {"id": "D19", "name": "Trà Đào Cam Sả Tươi", "category": "Trà & Trái Cây", "price": 42000, "base_sales": 75, "weekend_mult": 1.5, "weekday_mult": 0.9, "branch_weights": {"BRANCH_01": 1.0, "BRANCH_02": 1.6, "BRANCH_03": 0.8}},
    {"id": "D20", "name": "Trà Sữa Trân Châu Ô Long", "category": "Trà & Trái Cây", "price": 45000, "base_sales": 95, "weekend_mult": 1.6, "weekday_mult": 0.85, "branch_weights": {"BRANCH_01": 0.8, "BRANCH_02": 1.9, "BRANCH_03": 0.6}},
    {"id": "D21", "name": "Matcha Latte Sữa Tươi", "category": "Trà & Trái Cây", "price": 48000, "base_sales": 50, "weekend_mult": 1.4, "weekday_mult": 0.95, "branch_weights": {"BRANCH_01": 1.2, "BRANCH_02": 1.5, "BRANCH_03": 0.7}},
    {"id": "D22", "name": "Nước Ép Dưa Hấu Tươi", "category": "Trà & Trái Cây", "price": 38000, "base_sales": 45, "weekend_mult": 1.3, "weekday_mult": 0.95, "branch_weights": {"BRANCH_01": 1.1, "BRANCH_02": 0.9, "BRANCH_03": 1.2}},
]

# 3. Danh mục 35 Nguyên Liệu (Ingredients)
INGREDIENTS = [
    # Cà phê & Pha chế
    {"id": "ING01", "name": "Cà phê hạt Arabica-Robusta", "unit": "kg", "cost_per_unit": 220000, "shelf_life_days": 180, "min_stock": 8.0},
    {"id": "ING02", "name": "Sữa đặc Ông Thọ / Ngôi Sao", "unit": "lon", "cost_per_unit": 18000, "shelf_life_days": 365, "min_stock": 25.0},
    {"id": "ING03", "name": "Sữa tươi tiệt trùng", "unit": "lít", "cost_per_unit": 32000, "shelf_life_days": 60, "min_stock": 20.0},
    {"id": "ING04", "name": "Kem béo thực vật Rich's", "unit": "hộp (454ml)", "cost_per_unit": 28000, "shelf_life_days": 90, "min_stock": 10.0},
    {"id": "ING05", "name": "Trà Ô Long Bảo Lộc", "unit": "kg", "cost_per_unit": 250000, "shelf_life_days": 365, "min_stock": 4.0},
    {"id": "ING06", "name": "Bột Matcha Uji", "unit": "kg", "cost_per_unit": 450000, "shelf_life_days": 180, "min_stock": 2.0},
    {"id": "ING07", "name": "Trân châu đen Đài Loan", "unit": "kg", "cost_per_unit": 45000, "shelf_life_days": 180, "min_stock": 8.0},
    {"id": "ING08", "name": "Đào ngâm đóng hộp", "unit": "hộp", "cost_per_unit": 35000, "shelf_life_days": 730, "min_stock": 12.0},
    {"id": "ING09", "name": "Cam vàng nhập khẩu", "unit": "kg", "cost_per_unit": 42000, "shelf_life_days": 14, "min_stock": 10.0},
    {"id": "ING10", "name": "Cây sả tươi", "unit": "kg", "cost_per_unit": 20000, "shelf_life_days": 10, "min_stock": 4.0},
    {"id": "ING11", "name": "Dưa hấu tươi", "unit": "kg", "cost_per_unit": 15000, "shelf_life_days": 7, "min_stock": 15.0},
    {"id": "ING12", "name": "Đường nước Syrup", "unit": "lít", "cost_per_unit": 25000, "shelf_life_days": 180, "min_stock": 15.0},

    # Thịt & Hải sản / Đạm
    {"id": "ING13", "name": "Thịt bò nạm/tái tươi", "unit": "kg", "cost_per_unit": 260000, "shelf_life_days": 3, "min_stock": 15.0},
    {"id": "ING14", "name": "Thịt bắp bò hoa", "unit": "kg", "cost_per_unit": 280000, "shelf_life_days": 3, "min_stock": 10.0},
    {"id": "ING15", "name": "Thịt gà ta thả vườn", "unit": "kg", "cost_per_unit": 95000, "shelf_life_days": 3, "min_stock": 12.0},
    {"id": "ING16", "name": "Ức gà phi lê", "unit": "kg", "cost_per_unit": 75000, "shelf_life_days": 5, "min_stock": 10.0},
    {"id": "ING17", "name": "Thịt ba chỉ heo tươi", "unit": "kg", "cost_per_unit": 130000, "shelf_life_days": 3, "min_stock": 12.0},
    {"id": "ING18", "name": "Sườn cốt lết heo", "unit": "kg", "cost_per_unit": 140000, "shelf_life_days": 3, "min_stock": 12.0},
    {"id": "ING19", "name": "Chả lụa / Chả bì", "unit": "kg", "cost_per_unit": 110000, "shelf_life_days": 7, "min_stock": 6.0},
    {"id": "ING20", "name": "Giò heo bún bò", "unit": "kg", "cost_per_unit": 100000, "shelf_life_days": 3, "min_stock": 8.0},
    {"id": "ING21", "name": "Nem chua / Chả giò sống", "unit": "kg", "cost_per_unit": 120000, "shelf_life_days": 7, "min_stock": 6.0},
    {"id": "ING22", "name": "Trứng gà tươi", "unit": "quả", "cost_per_unit": 3200, "shelf_life_days": 30, "min_stock": 60.0},
    {"id": "ING23", "name": "Xúc xích tiệt trùng/hun khói", "unit": "kg", "cost_per_unit": 110000, "shelf_life_days": 60, "min_stock": 6.0},

    # Tinh bột & Bánh
    {"id": "ING24", "name": "Bánh phở tươi Hà Nội", "unit": "kg", "cost_per_unit": 18000, "shelf_life_days": 1, "min_stock": 18.0},
    {"id": "ING25", "name": "Bún tươi sợi nhỏ", "unit": "kg", "cost_per_unit": 16000, "shelf_life_days": 1, "min_stock": 15.0},
    {"id": "ING26", "name": "Bún bò sợi to", "unit": "kg", "cost_per_unit": 17000, "shelf_life_days": 1, "min_stock": 12.0},
    {"id": "ING27", "name": "Ổ Bánh mì giòn", "unit": "ổ", "cost_per_unit": 4000, "shelf_life_days": 1, "min_stock": 40.0},
    {"id": "ING28", "name": "Gạo thơm Jasmine", "unit": "kg", "cost_per_unit": 22000, "shelf_life_days": 180, "min_stock": 30.0},
    {"id": "ING29", "name": "Gạo tấm Sài Gòn", "unit": "kg", "cost_per_unit": 24000, "shelf_life_days": 180, "min_stock": 25.0},
    {"id": "ING30", "name": "Khoai tây cắt sợi đông lạnh", "unit": "kg", "cost_per_unit": 55000, "shelf_life_days": 180, "min_stock": 10.0},

    # Rau củ quả & Gia vị đặc thù
    {"id": "ING31", "name": "Rau sống & Xà lách", "unit": "kg", "cost_per_unit": 25000, "shelf_life_days": 3, "min_stock": 12.0},
    {"id": "ING32", "name": "Dưa cải chua muối", "unit": "kg", "cost_per_unit": 20000, "shelf_life_days": 14, "min_stock": 8.0},
    {"id": "ING33", "name": "Hành lá & Ngò rí", "unit": "kg", "cost_per_unit": 30000, "shelf_life_days": 4, "min_stock": 5.0},
    {"id": "ING34", "name": "Chanh tươi & Ớt xiêm", "unit": "kg", "cost_per_unit": 35000, "shelf_life_days": 10, "min_stock": 5.0},
    {"id": "ING35", "name": "Sốt mè rang Kewpie", "unit": "chai (1L)", "cost_per_unit": 135000, "shelf_life_days": 180, "min_stock": 3.0},
]

# 4. Định Lượng Công Thức (Recipes)
RECIPES = [
    # D01: Phở Bò Tái Nạm
    {"dish_id": "D01", "ingredient_id": "ING13", "quantity": 0.12},
    {"dish_id": "D01", "ingredient_id": "ING24", "quantity": 0.16},
    {"dish_id": "D01", "ingredient_id": "ING33", "quantity": 0.02},
    {"dish_id": "D01", "ingredient_id": "ING12", "quantity": 0.01},

    # D02: Phở Gà Ta Lá Chanh
    {"dish_id": "D02", "ingredient_id": "ING15", "quantity": 0.15},
    {"dish_id": "D02", "ingredient_id": "ING24", "quantity": 0.16},
    {"dish_id": "D02", "ingredient_id": "ING33", "quantity": 0.02},

    # D03: Bún Chả Hà Nội
    {"dish_id": "D03", "ingredient_id": "ING17", "quantity": 0.16},
    {"dish_id": "D03", "ingredient_id": "ING25", "quantity": 0.18},
    {"dish_id": "D03", "ingredient_id": "ING31", "quantity": 0.08},
    {"dish_id": "D03", "ingredient_id": "ING12", "quantity": 0.02},

    # D04: Bún Bò Huế
    {"dish_id": "D04", "ingredient_id": "ING14", "quantity": 0.10},
    {"dish_id": "D04", "ingredient_id": "ING20", "quantity": 0.12},
    {"dish_id": "D04", "ingredient_id": "ING26", "quantity": 0.18},
    {"dish_id": "D04", "ingredient_id": "ING10", "quantity": 0.03},

    # D05: Bún Thịt Nướng Chả Giò
    {"dish_id": "D05", "ingredient_id": "ING17", "quantity": 0.10},
    {"dish_id": "D05", "ingredient_id": "ING21", "quantity": 0.08},
    {"dish_id": "D05", "ingredient_id": "ING25", "quantity": 0.18},
    {"dish_id": "D05", "ingredient_id": "ING31", "quantity": 0.08},

    # D06: Cơm Gà Xối Mỡ Giòn Da
    {"dish_id": "D06", "ingredient_id": "ING15", "quantity": 0.22},
    {"dish_id": "D06", "ingredient_id": "ING28", "quantity": 0.14},

    # D07: Cơm Rang Dưa Bò
    {"dish_id": "D07", "ingredient_id": "ING13", "quantity": 0.10},
    {"dish_id": "D07", "ingredient_id": "ING32", "quantity": 0.08},
    {"dish_id": "D07", "ingredient_id": "ING28", "quantity": 0.14},
    {"dish_id": "D07", "ingredient_id": "ING22", "quantity": 1.0},

    # D08: Cơm Tấm Sườn Bì Chả
    {"dish_id": "D08", "ingredient_id": "ING18", "quantity": 0.18},
    {"dish_id": "D08", "ingredient_id": "ING19", "quantity": 0.05},
    {"dish_id": "D08", "ingredient_id": "ING29", "quantity": 0.15},

    # D09: Bánh Mì Thịt Nướng Giòn
    {"dish_id": "D09", "ingredient_id": "ING27", "quantity": 1.0},
    {"dish_id": "D09", "ingredient_id": "ING17", "quantity": 0.08},
    {"dish_id": "D09", "ingredient_id": "ING31", "quantity": 0.03},

    # D10: Bánh Mì Chảo Thập Cẩm
    {"dish_id": "D10", "ingredient_id": "ING27", "quantity": 1.0},
    {"dish_id": "D10", "ingredient_id": "ING22", "quantity": 1.0},
    {"dish_id": "D10", "ingredient_id": "ING23", "quantity": 0.06},
    {"dish_id": "D10", "ingredient_id": "ING19", "quantity": 0.04},

    # D11: Khoai Tây Chiên Bơ Tỏi
    {"dish_id": "D11", "ingredient_id": "ING30", "quantity": 0.18},

    # D12: Nem Rán Hà Nội
    {"dish_id": "D12", "ingredient_id": "ING21", "quantity": 0.15},
    {"dish_id": "D12", "ingredient_id": "ING31", "quantity": 0.05},

    # D13: Gà Popcorn
    {"dish_id": "D13", "ingredient_id": "ING16", "quantity": 0.18},

    # D14: Salad Ức Gà Sốt Mè Rang
    {"dish_id": "D14", "ingredient_id": "ING16", "quantity": 0.14},
    {"dish_id": "D14", "ingredient_id": "ING31", "quantity": 0.12},
    {"dish_id": "D14", "ingredient_id": "ING35", "quantity": 0.03},

    # D15: Cà Phê Sữa Đá Sài Gòn
    {"dish_id": "D15", "ingredient_id": "ING01", "quantity": 0.025},
    {"dish_id": "D15", "ingredient_id": "ING02", "quantity": 0.08},
    {"dish_id": "D15", "ingredient_id": "ING12", "quantity": 0.01},

    # D16: Bạc Xỉu Đá
    {"dish_id": "D16", "ingredient_id": "ING01", "quantity": 0.015},
    {"dish_id": "D16", "ingredient_id": "ING02", "quantity": 0.12},
    {"dish_id": "D16", "ingredient_id": "ING03", "quantity": 0.06},

    # D17: Cà Phê Muối Xứ Huế
    {"dish_id": "D17", "ingredient_id": "ING01", "quantity": 0.022},
    {"dish_id": "D17", "ingredient_id": "ING02", "quantity": 0.06},
    {"dish_id": "D17", "ingredient_id": "ING04", "quantity": 0.08},

    # D18: Americano Đá
    {"dish_id": "D18", "ingredient_id": "ING01", "quantity": 0.025},

    # D19: Trà Đào Cam Sả Tươi
    {"dish_id": "D19", "ingredient_id": "ING05", "quantity": 0.012},
    {"dish_id": "D19", "ingredient_id": "ING08", "quantity": 0.20},
    {"dish_id": "D19", "ingredient_id": "ING09", "quantity": 0.08},
    {"dish_id": "D19", "ingredient_id": "ING10", "quantity": 0.03},
    {"dish_id": "D19", "ingredient_id": "ING12", "quantity": 0.03},

    # D20: Trà Sữa Trân Châu Ô Long
    {"dish_id": "D20", "ingredient_id": "ING05", "quantity": 0.015},
    {"dish_id": "D20", "ingredient_id": "ING03", "quantity": 0.08},
    {"dish_id": "D20", "ingredient_id": "ING02", "quantity": 0.06},
    {"dish_id": "D20", "ingredient_id": "ING07", "quantity": 0.05},
    {"dish_id": "D20", "ingredient_id": "ING12", "quantity": 0.02},

    # D21: Matcha Latte Sữa Tươi
    {"dish_id": "D21", "ingredient_id": "ING06", "quantity": 0.012},
    {"dish_id": "D21", "ingredient_id": "ING03", "quantity": 0.12},
    {"dish_id": "D21", "ingredient_id": "ING12", "quantity": 0.02},

    # D22: Nước Ép Dưa Hấu Tươi
    {"dish_id": "D22", "ingredient_id": "ING11", "quantity": 0.45},
    {"dish_id": "D22", "ingredient_id": "ING12", "quantity": 0.02},
]

# ============================================================
# 5. Event Spikes — sự kiện bất thường (MỚI v2)
# ============================================================
EVENT_TYPES = [
    {"name": "don_tiec_dot_xuat", "prob": 0.02, "mult_range": (1.6, 2.3)},    # đơn đặt tiệc đột xuất
    {"name": "su_kien_dia_phuong", "prob": 0.015, "mult_range": (1.4, 1.9)},  # sự kiện gần chi nhánh
    {"name": "thoi_tiet_cuc_doan", "prob": 0.02, "mult_range": (0.4, 0.65)},  # mưa bão lớn, giảm mạnh
    {"name": "su_co_von_hanh", "prob": 0.01, "mult_range": (0.3, 0.5)},       # sự cố vận hành
]

def get_event_multiplier():
    """Trả về (multiplier, event_name hoặc None) cho 1 ngày."""
    for event in EVENT_TYPES:
        if random.random() < event["prob"]:
            return random.uniform(*event["mult_range"]), event["name"]
    return 1.0, None


def generate_big_dataset():
    print("=" * 70)
    print("BẮT ĐẦU SINH DỮ LIỆU ĐA DẠNG v2 (3 CHI NHÁNH, 22 MÓN, 730 NGÀY)")
    print("Cải tiến: +event spikes, +tương tác phi tuyến, +Tết Nguyên Đán, nhiễu 12%")
    print("=" * 70)

    # 730 ngày (2 năm lịch sử kết thúc hôm qua 2026-09-17)
    end_date = datetime(2026, 9, 17)
    start_date = end_date - timedelta(days=729)
    total_days = 730

    # Pre-compute Tết dates cho các năm trong range
    tet_dates_in_range = {}
    for year in range(start_date.year, end_date.year + 1):
        try:
            tet_dates_in_range[year] = get_tet_date(year)
        except (ValueError, KeyError):
            pass
    print(f"-> Tết dates: {tet_dates_in_range}")

    calendar_rows = []
    sales_rows = []

    current_date = start_date
    day_idx = 0

    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        month_day = current_date.strftime("%m-%d")
        dow = current_date.weekday()
        is_wknd = 1 if dow in [5, 6] else 0
        is_hol = 1 if month_day in VIETNAM_HOLIDAYS else 0
        hol_name = VIETNAM_HOLIDAYS.get(month_day, "")

        calendar_rows.append({
            "date": date_str,
            "day_of_week": dow,
            "day_name": ["T2", "T3", "T4", "T5", "T6", "T7", "CN"][dow],
            "is_weekend": is_wknd,
            "is_holiday": is_hol,
            "holiday_name": hol_name
        })

        # Tăng trưởng theo thời gian (+20% qua 2 năm)
        trend = 1.0 + (day_idx / total_days) * 0.20
        month = current_date.month

        # Tết multiplier cho ngày này (tìm Tết gần nhất)
        tet_mult = 1.0
        for year, tet_date in tet_dates_in_range.items():
            m = get_tet_synthetic_multiplier(current_date, tet_date)
            if m != 1.0:
                tet_mult = m
                break

        # Sinh sales cho 3 chi nhánh x 22 món
        for branch in BRANCHES:
            b_id = branch["id"]
            branch_type = BRANCH_TYPE_MAP[b_id]

            # Event spike — RIÊNG theo từng chi nhánh (mỗi chi nhánh có event độc lập)
            event_mult, event_name = get_event_multiplier()

            for dish in DISHES:
                base = dish["base_sales"]
                b_weight = dish["branch_weights"].get(b_id, 1.0)
                
                day_mult = dish["weekend_mult"] if is_wknd else dish["weekday_mult"]
                hol_mult = 1.45 if is_hol else 1.0

                # Mùa hè (tháng 5-8): đồ uống tăng +20%
                weather_mult = 1.0
                if month in [5, 6, 7, 8] and dish["category"] in ["Trà & Trái Cây", "Cà Phê"]:
                    weather_mult = 1.20

                # Tương tác phi tuyến: branch_type × weekend × weather (MỚI v2)
                interaction_mult = 1.0
                if is_wknd and weather_mult > 1.0:
                    # Cuối tuần + mùa hè nóng → đồ uống tăng THÊM tùy loại quán
                    if branch_type == "tra_sua":
                        interaction_mult = 1.15   # trà sữa sinh viên: cuối tuần nóng → tăng mạnh
                    elif branch_type == "bistro":
                        interaction_mult = 1.05   # bistro: tăng nhẹ
                elif is_wknd and month in [11, 12, 1, 2]:
                    # Cuối tuần + mùa đông → ảnh hưởng khác nhau theo loại quán
                    if branch_type == "tra_sua":
                        interaction_mult = 0.85   # trà sữa: cuối tuần lạnh → giảm (sinh viên ngại ra ngoài)
                    elif branch_type == "am_thuc_truyen_thong":
                        interaction_mult = 1.10   # ẩm thực truyền thống: cuối tuần lạnh → gia đình tụ tập → tăng

                # Nhiễu Gauss 12% (tăng từ 5% cũ)
                noise = random.gauss(1.0, 0.12)

                qty = int(round(base * b_weight * day_mult * hol_mult * trend * weather_mult * event_mult * interaction_mult * tet_mult * noise))
                qty = max(qty, 4)

                sales_rows.append({
                    "date": date_str,
                    "branch_id": b_id,
                    "branch_name": branch["name"],
                    "dish_id": dish["id"],
                    "dish_name": dish["name"],
                    "category": dish["category"],
                    "quantity": qty,
                    "revenue": qty * dish["price"],
                    "event_flag": event_name   # MỚI: None nếu không có event
                })

        current_date += timedelta(days=1)
        day_idx += 1

    print(f"-> Đã sinh {len(sales_rows)} bản ghi doanh số ({total_days} ngày x 3 chi nhánh x 22 món).")

    # Đếm event flags
    event_counts = {}
    for row in sales_rows:
        ef = row.get("event_flag")
        if ef:
            event_counts[ef] = event_counts.get(ef, 0) + 1
    print(f"-> Event flags: {event_counts}")

    # Sinh Tồn Kho (Inventory) theo từng chi nhánh
    inventory_rows = []
    for branch in BRANCHES:
        b_id = branch["id"]
        for ing in INGREDIENTS:
            min_stk = ing["min_stock"]
            if ing["id"] in ["ING13", "ING14", "ING15", "ING17", "ING18", "ING24", "ING25", "ING27", "ING03", "ING09", "ING11"]:
                qty = round(min_stk * random.uniform(0.3, 0.7), 1)
            else:
                qty = round(min_stk * random.uniform(1.2, 2.5), 1)

            inventory_rows.append({
                "branch_id": b_id,
                "ingredient_id": ing["id"],
                "quantity": qty
            })

    # Sinh Pre-orders cho ngày mai (2026-09-18)
    tomorrow_str = (end_date + timedelta(days=1)).strftime("%Y-%m-%d")
    preorders = [
        {"id": 1, "branch_id": "BRANCH_01", "date": tomorrow_str, "customer_name": "Công ty TechCorp (Họp sáng)", "dish_id": "D15", "dish_name": "Cà Phê Sữa Đá Sài Gòn", "quantity": 25, "note": "Giao lúc 8h30"},
        {"id": 2, "branch_id": "BRANCH_01", "date": tomorrow_str, "customer_name": "Văn phòng Luật Mekong (Cơm trưa)", "dish_id": "D06", "dish_name": "Cơm Gà Xối Mỡ Giòn Da", "quantity": 18, "note": "Giao lúc 11h45"},
        {"id": 3, "branch_id": "BRANCH_01", "date": tomorrow_str, "customer_name": "Anh Minh (Đặt ăn trưa)", "dish_id": "D01", "dish_name": "Phở Bò Tái Nạm", "quantity": 12, "note": "Giao 12h00"},
        {"id": 4, "branch_id": "BRANCH_02", "date": tomorrow_str, "customer_name": "CLB Tiếng Anh ĐH Quốc Gia (Offline)", "dish_id": "D20", "dish_name": "Trà Sữa Trân Châu Ô Long", "quantity": 30, "note": "Lấy lúc 14h30"},
        {"id": 5, "branch_id": "BRANCH_02", "date": tomorrow_str, "customer_name": "Nhóm sinh viên Bách Khoa", "dish_id": "D13", "dish_name": "Gà Popcorn Giòn Cay", "quantity": 15, "note": "Ăn tại quán 16h00"},
        {"id": 6, "branch_id": "BRANCH_02", "date": tomorrow_str, "customer_name": "Chị Phương (Sinh nhật)", "dish_id": "D19", "dish_name": "Trà Đào Cam Sả Tươi", "quantity": 16, "note": "Giao 15h00"},
        {"id": 7, "branch_id": "BRANCH_03", "date": tomorrow_str, "customer_name": "Gia đình Bác Hùng (Tiệc mừng)", "dish_id": "D01", "dish_name": "Phở Bò Tái Nạm", "quantity": 20, "note": "Ăn tại quán 18h30"},
        {"id": 8, "branch_id": "BRANCH_03", "date": tomorrow_str, "customer_name": "Bàn tiệc cô Mai", "dish_id": "D04", "dish_name": "Bún Bò Huế Cốt Đậm", "quantity": 14, "note": "Ăn tại quán 19h00"},
    ]

    # Sinh Lô Hàng Tồn Kho (Inventory Batches - FEFO)
    batches = [
        {"id": 1, "branch_id": "BRANCH_01", "ingredient_id": "ING03", "batch_code": "LOT-MILK-01", "quantity_remaining": 6.0, "received_date": "2026-09-12", "expiry_date": "2026-09-22"},
        {"id": 2, "branch_id": "BRANCH_01", "ingredient_id": "ING13", "batch_code": "LOT-BEEF-01", "quantity_remaining": 5.5, "received_date": "2026-09-16", "expiry_date": "2026-09-19"},
        {"id": 3, "branch_id": "BRANCH_02", "ingredient_id": "ING09", "batch_code": "LOT-ORANGE-01", "quantity_remaining": 4.0, "received_date": "2026-09-14", "expiry_date": "2026-09-21"},
        {"id": 4, "branch_id": "BRANCH_02", "ingredient_id": "ING11", "batch_code": "LOT-MELON-01", "quantity_remaining": 8.0, "received_date": "2026-09-15", "expiry_date": "2026-09-19"},
        {"id": 5, "branch_id": "BRANCH_03", "ingredient_id": "ING14", "batch_code": "LOT-SHANK-01", "quantity_remaining": 4.0, "received_date": "2026-09-16", "expiry_date": "2026-09-19"},
        {"id": 6, "branch_id": "BRANCH_03", "ingredient_id": "ING15", "batch_code": "LOT-CHICK-01", "quantity_remaining": 6.0, "received_date": "2026-09-16", "expiry_date": "2026-09-19"},
        {"id": 7, "branch_id": "BRANCH_01", "ingredient_id": "ING01", "batch_code": "LOT-COFFEE-01", "quantity_remaining": 12.0, "received_date": "2026-08-01", "expiry_date": "2027-02-01"},
        {"id": 8, "branch_id": "BRANCH_02", "ingredient_id": "ING08", "batch_code": "LOT-PEACH-01", "quantity_remaining": 20.0, "received_date": "2026-07-01", "expiry_date": "2027-07-01"},
    ]

    # Lưu CSV
    def save_csv(filename, fieldnames, rows):
        path = os.path.join(DATA_DIR, filename)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)
        print(f"-> Đã lưu CSV: {filename} ({len(rows)} dòng)")

    save_csv("branches.csv", ["id", "name", "address", "type"], BRANCHES)
    save_csv("dishes.csv", ["id", "name", "category", "price", "base_sales", "weekend_mult", "weekday_mult"], DISHES)
    save_csv("ingredients.csv", ["id", "name", "unit", "cost_per_unit", "shelf_life_days", "min_stock"], INGREDIENTS)
    save_csv("recipes.csv", ["dish_id", "ingredient_id", "quantity"], RECIPES)
    save_csv("calendar.csv", ["date", "day_of_week", "day_name", "is_weekend", "is_holiday", "holiday_name"], calendar_rows)
    save_csv("sales.csv", ["date", "branch_id", "branch_name", "dish_id", "dish_name", "category", "quantity", "revenue", "event_flag"], sales_rows)
    save_csv("inventory.csv", ["branch_id", "ingredient_id", "quantity"], inventory_rows)
    save_csv("inventory_batches.csv", ["id", "branch_id", "ingredient_id", "batch_code", "quantity_remaining", "received_date", "expiry_date"], batches)
    save_csv("preorders.csv", ["id", "branch_id", "date", "customer_name", "dish_id", "dish_name", "quantity", "note"], preorders)

    # Nạp SQLite DB
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Tạo bảng
    cur.execute("DROP TABLE IF EXISTS branches")
    cur.execute("DROP TABLE IF EXISTS dishes")
    cur.execute("DROP TABLE IF EXISTS ingredients")
    cur.execute("DROP TABLE IF EXISTS recipes")
    cur.execute("DROP TABLE IF EXISTS calendar")
    cur.execute("DROP TABLE IF EXISTS sales")
    cur.execute("DROP TABLE IF EXISTS inventory")
    cur.execute("DROP TABLE IF EXISTS inventory_batches")
    cur.execute("DROP TABLE IF EXISTS preorders")

    cur.execute("""
    CREATE TABLE branches (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        address TEXT NOT NULL,
        type TEXT NOT NULL
    )""")

    cur.execute("""
    CREATE TABLE dishes (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL
    )""")

    cur.execute("""
    CREATE TABLE ingredients (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        unit TEXT NOT NULL,
        cost_per_unit REAL NOT NULL,
        shelf_life_days INTEGER,
        min_stock REAL
    )""")

    cur.execute("""
    CREATE TABLE recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dish_id TEXT NOT NULL,
        ingredient_id TEXT NOT NULL,
        quantity REAL NOT NULL
    )""")

    cur.execute("""
    CREATE TABLE calendar (
        date TEXT PRIMARY KEY,
        day_of_week INTEGER,
        day_name TEXT,
        is_weekend INTEGER,
        is_holiday INTEGER,
        holiday_name TEXT
    )""")

    cur.execute("""
    CREATE TABLE sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        branch_id TEXT NOT NULL,
        branch_name TEXT NOT NULL,
        dish_id TEXT NOT NULL,
        dish_name TEXT NOT NULL,
        category TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        revenue REAL NOT NULL,
        event_flag TEXT
    )""")

    cur.execute("""
    CREATE TABLE inventory (
        branch_id TEXT NOT NULL,
        ingredient_id TEXT NOT NULL,
        quantity REAL NOT NULL,
        PRIMARY KEY (branch_id, ingredient_id)
    )""")

    cur.execute("""
    CREATE TABLE inventory_batches (
        id INTEGER PRIMARY KEY,
        branch_id TEXT NOT NULL,
        ingredient_id TEXT NOT NULL,
        batch_code TEXT NOT NULL,
        quantity_remaining REAL NOT NULL,
        received_date TEXT,
        expiry_date TEXT,
        batch_hash TEXT,
        solana_tx TEXT,
        solana_status TEXT,
        verified_at TEXT
    )""")

    cur.execute("""
    CREATE TABLE preorders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        branch_id TEXT NOT NULL,
        date TEXT NOT NULL,
        customer_name TEXT,
        dish_id TEXT NOT NULL,
        dish_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        note TEXT
    )""")

    # Chèn dữ liệu
    cur.executemany("INSERT INTO branches (id, name, address, type) VALUES (?, ?, ?, ?)",
                    [(b["id"], b["name"], b["address"], b["type"]) for b in BRANCHES])

    cur.executemany("INSERT INTO dishes (id, name, category, price) VALUES (?, ?, ?, ?)",
                    [(d["id"], d["name"], d["category"], d["price"]) for d in DISHES])

    cur.executemany("INSERT INTO ingredients (id, name, unit, cost_per_unit, shelf_life_days, min_stock) VALUES (?, ?, ?, ?, ?, ?)",
                    [(i["id"], i["name"], i["unit"], i["cost_per_unit"], i["shelf_life_days"], i["min_stock"]) for i in INGREDIENTS])

    cur.executemany("INSERT INTO recipes (dish_id, ingredient_id, quantity) VALUES (?, ?, ?)",
                    [(r["dish_id"], r["ingredient_id"], r["quantity"]) for r in RECIPES])

    cur.executemany("INSERT INTO calendar (date, day_of_week, day_name, is_weekend, is_holiday, holiday_name) VALUES (?, ?, ?, ?, ?, ?)",
                    [(c["date"], c["day_of_week"], c["day_name"], c["is_weekend"], c["is_holiday"], c["holiday_name"]) for c in calendar_rows])

    cur.executemany("INSERT INTO sales (date, branch_id, branch_name, dish_id, dish_name, category, quantity, revenue, event_flag) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [(s["date"], s["branch_id"], s["branch_name"], s["dish_id"], s["dish_name"], s["category"], s["quantity"], s["revenue"], s.get("event_flag")) for s in sales_rows])

    cur.executemany("INSERT INTO inventory (branch_id, ingredient_id, quantity) VALUES (?, ?, ?)",
                    [(inv["branch_id"], inv["ingredient_id"], inv["quantity"]) for inv in inventory_rows])

    # Ký chứng thực Solana Devnet cho các lô hàng mẫu
    from backend.app.services.solana_service import generate_batch_proof
    batches_with_proof = []
    for b in batches:
        proof = generate_batch_proof(b)
        batches_with_proof.append((
            b["id"], b["branch_id"], b["ingredient_id"], b["batch_code"],
            b["quantity_remaining"], b["received_date"], b["expiry_date"],
            proof["record_hash"], proof["tx_signature"], "CONFIRMED", proof["notarized_at"]
        ))

    cur.executemany("INSERT INTO inventory_batches (id, branch_id, ingredient_id, batch_code, quantity_remaining, received_date, expiry_date, batch_hash, solana_tx, solana_status, verified_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    batches_with_proof)

    cur.executemany("INSERT INTO preorders (id, branch_id, date, customer_name, dish_id, dish_name, quantity, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    [(p["id"], p["branch_id"], p["date"], p["customer_name"], p["dish_id"], p["dish_name"], p["quantity"], p["note"]) for p in preorders])

    conn.commit()
    conn.close()

    print("=" * 70)
    print(f"NẠP THÀNH CÔNG VÀO SQLITE: {DB_PATH}")
    print(f"Tổng kết: 3 Chi Nhánh | 22 Món Ăn/Uống | 35 Nguyên Liệu | {len(sales_rows)} Bản ghi Sales (730 ngày)")
    print(f"Cải tiến v2: event_flag column, Tết Nguyên Đán, nhiễu 12%, tương tác phi tuyến")
    print("=" * 70)

if __name__ == "__main__":
    generate_big_dataset()
