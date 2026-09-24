"""
scripts/generate_data.py
Sinh dữ liệu quy mô lớn cho FoodFlow AI (3 Chi Nhánh, 22 Món Ăn/Đồ Uống, 35 Nguyên Liệu, 2 Năm Lịch Sử ~48,000+ dòng):
- Chi nhánh 1: FoodFlow Quận 1 (Bistro & Cơm Trưa Văn Phòng)
- Chi nhánh 2: FoodFlow Cầu Giấy (Trà Sữa & Ăn Vặt Giới Trẻ)
- Chi nhánh 3: FoodFlow Tây Hồ (Ẩm Thực Truyền Thống Gia Đình)

v3 — Tích hợp Khí hậu & Làm mượt Dữ liệu Thời tiết (Weather Dynamics & Smooth Transition):
- Đường cong nhiệt độ điều hòa chu kỳ năm + chuỗi ngày mưa liên tục (Markov spells)
- Làm mượt tác động thời tiết (Exponential Smoothing) tránh nhảy bước đột ngột
- Cột weather_condition, temperature, precipitation_mm trong sales
- 4 loại sự kiện bất thường (Event spikes) + event_flag
- Chu kỳ Tết Nguyên Đán 2025/2026
- Nhiễu Gauss 12%
"""

import os
import sys
import csv
import json
import math
import random
import sqlite3
import shutil
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
ROOT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "foodflow.db")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# 1. Danh sách Chi Nhánh (Branches)
BRANCHES = [
    {"id": "BRANCH_01", "name": "FoodFlow Quận 1", "address": "120 Lê Lợi, Bến Thành, Quận 1, TP.HCM", "type": "Bistro & Cơm Văn Phòng"},
    {"id": "BRANCH_02", "name": "FoodFlow Cầu Giấy", "address": "88 Cầu Giấy, Quan Hoa, Cầu Giấy, Hà Nội", "type": "Trà Sữa & Ăn Vặt Sinh Viên"},
    {"id": "BRANCH_03", "name": "FoodFlow Tây Hồ", "address": "45 Xuân Diệu, Quảng An, Tây Hồ, Hà Nội", "type": "Ẩm Thực Truyền Thống & Gia Đình"},
]

BRANCH_TYPE_MAP = {
    "BRANCH_01": "bistro",
    "BRANCH_02": "tra_sua",
    "BRANCH_03": "am_thuc_truyen_thong",
}

# 2. Danh mục 22 Món Ăn & Đồ Uống (Dishes)
DISHES = [
    # Phở & Bún
    {"id": "D01", "name": "Phở Bò Tái Nạm", "category": "Món Nước", "price": 60000, "base_sales": 80, "weekend_mult": 1.45, "weekday_mult": 1.0, "branch_weights": {"BRANCH_01": 1.4, "BRANCH_02": 0.8, "BRANCH_03": 1.5}},
    {"id": "D02", "name": "Phở Gà Ta Lá Chanh", "category": "Món Nước", "price": 55000, "base_sales": 60, "weekend_mult": 1.4, "weekday_mult": 1.0, "branch_weights": {"BRANCH_01": 1.3, "BRANCH_02": 0.7, "BRANCH_03": 1.6}},
    {"id": "D03", "name": "Bún Chả Hà Nội", "category": "Món Khô", "price": 65000, "base_sales": 90, "weekend_mult": 1.35, "weekday_mult": 1.1, "branch_weights": {"BRANCH_01": 1.3, "BRANCH_02": 0.9, "BRANCH_03": 1.7}},
    {"id": "D04", "name": "Bún Bò Huế Cốt Đậm", "category": "Món Nước", "price": 65000, "base_sales": 65, "weekend_mult": 1.5, "weekday_mult": 1.0, "branch_weights": {"BRANCH_01": 1.5, "BRANCH_02": 0.8, "BRANCH_03": 1.2}},
    {"id": "D05", "name": "Bún Thịt Nướng Chả Giò", "category": "Món Khô", "price": 55000, "base_sales": 70, "weekend_mult": 1.4, "weekday_mult": 1.0, "branch_weights": {"BRANCH_01": 1.4, "BRANCH_02": 1.1, "BRANCH_03": 0.9}},

    # Cơm & Bánh Mì
    {"id": "D06", "name": "Cơm Gà Xối Mỡ Giòn Da", "category": "Món Khô", "price": 55000, "base_sales": 110, "weekend_mult": 1.25, "weekday_mult": 1.3, "branch_weights": {"BRANCH_01": 1.6, "BRANCH_02": 1.4, "BRANCH_03": 0.8}},
    {"id": "D07", "name": "Cơm Rang Dưa Bò Hà Nội", "category": "Món Khô", "price": 60000, "base_sales": 80, "weekend_mult": 1.3, "weekday_mult": 1.2, "branch_weights": {"BRANCH_01": 1.4, "BRANCH_02": 1.0, "BRANCH_03": 1.3}},
    {"id": "D08", "name": "Cơm Tấm Sườn Bì Chả", "category": "Món Khô", "price": 65000, "base_sales": 105, "weekend_mult": 1.4, "weekday_mult": 1.1, "branch_weights": {"BRANCH_01": 1.7, "BRANCH_02": 1.1, "BRANCH_03": 0.7}},
    {"id": "D09", "name": "Bánh Mì Thịt Nướng Giòn", "category": "Món Khô", "price": 35000, "base_sales": 120, "weekend_mult": 1.2, "weekday_mult": 1.4, "branch_weights": {"BRANCH_01": 1.5, "BRANCH_02": 1.6, "BRANCH_03": 0.6}},
    {"id": "D10", "name": "Bánh Mì Chảo Thập Cẩm", "category": "Món Khô", "price": 50000, "base_sales": 55, "weekend_mult": 1.6, "weekday_mult": 0.9, "branch_weights": {"BRANCH_01": 1.3, "BRANCH_02": 1.4, "BRANCH_03": 0.8}},

    # Ăn Vặt & Món Phụ
    {"id": "D11", "name": "Nem Rán Hà Nội (10 cái)", "category": "Đồ Ăn Nhẹ", "price": 60000, "base_sales": 45, "weekend_mult": 1.5, "weekday_mult": 0.9, "branch_weights": {"BRANCH_01": 1.1, "BRANCH_02": 1.2, "BRANCH_03": 1.6}},
    {"id": "D12", "name": "Gỏi Cuốn Tôm Thịt (4 cuốn)", "category": "Đồ Ăn Nhẹ", "price": 40000, "base_sales": 50, "weekend_mult": 1.35, "weekday_mult": 1.0, "branch_weights": {"BRANCH_01": 1.4, "BRANCH_02": 0.9, "BRANCH_03": 1.2}},
    {"id": "D13", "name": "Khoai Tây Chiên Lắc Phô Mai", "category": "Đồ Ăn Nhẹ", "price": 35000, "base_sales": 60, "weekend_mult": 1.7, "weekday_mult": 0.8, "branch_weights": {"BRANCH_01": 0.9, "BRANCH_02": 2.0, "BRANCH_03": 0.6}},
    {"id": "D14", "name": "Gà Rán Giòn Cay (2 miếng)", "category": "Đồ Ăn Nhẹ", "price": 50000, "base_sales": 70, "weekend_mult": 1.6, "weekday_mult": 0.9, "branch_weights": {"BRANCH_01": 1.0, "BRANCH_02": 1.9, "BRANCH_03": 0.7}},

    # Đồ Uống & Trà Sữa
    {"id": "D15", "name": "Cà Phê Sữa Đá Sài Gòn", "category": "Cà Phê", "price": 28000, "base_sales": 150, "weekend_mult": 1.1, "weekday_mult": 1.5, "branch_weights": {"BRANCH_01": 1.8, "BRANCH_02": 1.2, "BRANCH_03": 1.1}},
    {"id": "D16", "name": "Bạc Xỉu Đá", "category": "Cà Phê", "price": 30000, "base_sales": 80, "weekend_mult": 1.2, "weekday_mult": 1.3, "branch_weights": {"BRANCH_01": 1.5, "BRANCH_02": 1.4, "BRANCH_03": 0.8}},
    {"id": "D17", "name": "Cà Phê Muối Xứ Huế", "category": "Cà Phê", "price": 35000, "base_sales": 75, "weekend_mult": 1.3, "weekday_mult": 1.2, "branch_weights": {"BRANCH_01": 1.4, "BRANCH_02": 1.5, "BRANCH_03": 0.9}},
    {"id": "D18", "name": "Americano Đá", "category": "Cà Phê", "price": 30000, "base_sales": 50, "weekend_mult": 1.0, "weekday_mult": 1.4, "branch_weights": {"BRANCH_01": 1.9, "BRANCH_02": 0.8, "BRANCH_03": 0.9}},
    {"id": "D19", "name": "Trà Đào Cam Sả Tươi", "category": "Trà & Trái Cây", "price": 38000, "base_sales": 95, "weekend_mult": 1.5, "weekday_mult": 1.1, "branch_weights": {"BRANCH_01": 1.3, "BRANCH_02": 1.8, "BRANCH_03": 0.9}},
    {"id": "D20", "name": "Trà Sữa Trân Châu Ô Long", "category": "Trà & Trái Cây", "price": 42000, "base_sales": 130, "weekend_mult": 1.7, "weekday_mult": 1.0, "branch_weights": {"BRANCH_01": 1.1, "BRANCH_02": 2.2, "BRANCH_03": 0.7}},
    {"id": "D21", "name": "Matcha Latte Sữa Tươi", "category": "Trà & Trái Cây", "price": 45000, "base_sales": 60, "weekend_mult": 1.5, "weekday_mult": 1.0, "branch_weights": {"BRANCH_01": 1.2, "BRANCH_02": 1.7, "BRANCH_03": 0.7}},
    {"id": "D22", "name": "Nước Ép Dưa Hấu Tươi", "category": "Trà & Trái Cây", "price": 35000, "base_sales": 55, "weekend_mult": 1.4, "weekday_mult": 1.0, "branch_weights": {"BRANCH_01": 1.3, "BRANCH_02": 1.2, "BRANCH_03": 1.1}},
]

# 3. Danh mục 35 Nguyên Liệu (Ingredients)
INGREDIENTS = [
    {"id": "ING01", "name": "Cà phê hạt Robusta Buôn Ma Thuột", "unit": "kg", "cost_per_unit": 180000, "shelf_life_days": 180, "min_stock": 5.0},
    {"id": "ING02", "name": "Sữa đặc Ông Thọ / Ngôi Sao", "unit": "lon", "cost_per_unit": 24000, "shelf_life_days": 365, "min_stock": 20.0},
    {"id": "ING03", "name": "Sữa tươi tiệt trùng", "unit": "lít", "cost_per_unit": 32000, "shelf_life_days": 30, "min_stock": 15.0},
    {"id": "ING04", "name": "Kem béo thực vật Rich lùn", "unit": "hộp", "cost_per_unit": 36000, "shelf_life_days": 180, "min_stock": 10.0},
    {"id": "ING05", "name": "Trà đen / Trà Ô long", "unit": "kg", "cost_per_unit": 220000, "shelf_life_days": 365, "min_stock": 4.0},
    {"id": "ING06", "name": "Bột Matcha Uji Nhật Bản", "unit": "kg", "cost_per_unit": 650000, "shelf_life_days": 180, "min_stock": 1.5},
    {"id": "ING07", "name": "Trân châu đen Đài Loan", "unit": "kg", "cost_per_unit": 45000, "shelf_life_days": 180, "min_stock": 8.0},
    {"id": "ING08", "name": "Đào ngâm đóng hộp", "unit": "hộp", "cost_per_unit": 38000, "shelf_life_days": 365, "min_stock": 12.0},
    {"id": "ING09", "name": "Cam sành tươi", "unit": "kg", "cost_per_unit": 25000, "shelf_life_days": 7, "min_stock": 10.0},
    {"id": "ING10", "name": "Sả cây tươi", "unit": "kg", "cost_per_unit": 18000, "shelf_life_days": 10, "min_stock": 4.0},
    {"id": "ING11", "name": "Dưa hấu tươi", "unit": "kg", "cost_per_unit": 16000, "shelf_life_days": 7, "min_stock": 15.0},
    {"id": "ING12", "name": "Đường mía tinh luyện", "unit": "kg", "cost_per_unit": 22000, "shelf_life_days": 365, "min_stock": 15.0},
    {"id": "ING13", "name": "Thịt bò nạm/tái tươi", "unit": "kg", "cost_per_unit": 260000, "shelf_life_days": 3, "min_stock": 12.0},
    {"id": "ING14", "name": "Bắp bò / Nạm bò hầm", "unit": "kg", "cost_per_unit": 280000, "shelf_life_days": 3, "min_stock": 8.0},
    {"id": "ING15", "name": "Thịt gà ta thả vườn", "unit": "kg", "cost_per_unit": 135000, "shelf_life_days": 3, "min_stock": 10.0},
    {"id": "ING16", "name": "Gà góc tư làm sẵn", "unit": "kg", "cost_per_unit": 75000, "shelf_life_days": 3, "min_stock": 15.0},
    {"id": "ING17", "name": "Thịt ba chỉ heo tươi", "unit": "kg", "cost_per_unit": 140000, "shelf_life_days": 3, "min_stock": 12.0},
    {"id": "ING18", "name": "Sườn cốt lết heo", "unit": "kg", "cost_per_unit": 130000, "shelf_life_days": 3, "min_stock": 10.0},
    {"id": "ING19", "name": "Thịt nạc vai xay", "unit": "kg", "cost_per_unit": 115000, "shelf_life_days": 3, "min_stock": 8.0},
    {"id": "ING20", "name": "Tôm thẻ tươi bóc vỏ", "unit": "kg", "cost_per_unit": 210000, "shelf_life_days": 3, "min_stock": 6.0},
    {"id": "ING21", "name": "Chả lụa / Chả huế", "unit": "kg", "cost_per_unit": 160000, "shelf_life_days": 7, "min_stock": 5.0},
    {"id": "ING22", "name": "Trứng gà tươi", "unit": "quả", "cost_per_unit": 3200, "shelf_life_days": 21, "min_stock": 50.0},
    {"id": "ING23", "name": "Pate gan thượng hạng", "unit": "kg", "cost_per_unit": 150000, "shelf_life_days": 10, "min_stock": 4.0},
    {"id": "ING24", "name": "Bánh phở tươi Hà Nội", "unit": "kg", "cost_per_unit": 18000, "shelf_life_days": 2, "min_stock": 15.0},
    {"id": "ING25", "name": "Bún tươi sợi nhỏ", "unit": "kg", "cost_per_unit": 16000, "shelf_life_days": 2, "min_stock": 15.0},
    {"id": "ING26", "name": "Gạo thơm ST25", "unit": "kg", "cost_per_unit": 28000, "shelf_life_days": 180, "min_stock": 25.0},
    {"id": "ING27", "name": "Ổ Bánh mì giòn", "unit": "ổ", "cost_per_unit": 4000, "shelf_life_days": 1, "min_stock": 40.0},
    {"id": "ING28", "name": "Bánh tráng cuốn / Bánh đa nem", "unit": "gói", "cost_per_unit": 15000, "shelf_life_days": 180, "min_stock": 10.0},
    {"id": "ING29", "name": "Khoai tây cọng đông lạnh", "unit": "kg", "cost_per_unit": 55000, "shelf_life_days": 180, "min_stock": 10.0},
    {"id": "ING30", "name": "Bột phô mai lắc", "unit": "kg", "cost_per_unit": 140000, "shelf_life_days": 180, "min_stock": 2.0},
    {"id": "ING31", "name": "Rau sống & Thảo mộc tổng hợp", "unit": "kg", "cost_per_unit": 35000, "shelf_life_days": 3, "min_stock": 8.0},
    {"id": "ING32", "name": "Dưa cải chua muối", "unit": "kg", "cost_per_unit": 20000, "shelf_life_days": 14, "min_stock": 6.0},
    {"id": "ING33", "name": "Hành lá & Ngò rí", "unit": "kg", "cost_per_unit": 30000, "shelf_life_days": 4, "min_stock": 4.0},
    {"id": "ING34", "name": "Nước mắm cá cơm Phan Thiết", "unit": "lít", "cost_per_unit": 65000, "shelf_life_days": 365, "min_stock": 8.0},
    {"id": "ING35", "name": "Gia vị & Dầu ăn tổng hợp", "unit": "lít", "cost_per_unit": 45000, "shelf_life_days": 180, "min_stock": 10.0},
]

# 4. Định lượng Món ăn (Recipes)
RECIPES = [
    {"dish_id": "D01", "ingredient_id": "ING24", "quantity": 0.18},
    {"dish_id": "D01", "ingredient_id": "ING13", "quantity": 0.12},
    {"dish_id": "D01", "ingredient_id": "ING33", "quantity": 0.02},
    {"dish_id": "D01", "ingredient_id": "ING31", "quantity": 0.05},

    {"dish_id": "D02", "ingredient_id": "ING24", "quantity": 0.18},
    {"dish_id": "D02", "ingredient_id": "ING15", "quantity": 0.13},
    {"dish_id": "D02", "ingredient_id": "ING33", "quantity": 0.02},

    {"dish_id": "D03", "ingredient_id": "ING25", "quantity": 0.20},
    {"dish_id": "D03", "ingredient_id": "ING17", "quantity": 0.14},
    {"dish_id": "D03", "ingredient_id": "ING31", "quantity": 0.06},
    {"dish_id": "D03", "ingredient_id": "ING34", "quantity": 0.04},

    {"dish_id": "D04", "ingredient_id": "ING25", "quantity": 0.20},
    {"dish_id": "D04", "ingredient_id": "ING14", "quantity": 0.10},
    {"dish_id": "D04", "ingredient_id": "ING21", "quantity": 0.04},
    {"dish_id": "D04", "ingredient_id": "ING10", "quantity": 0.02},
    {"dish_id": "D04", "ingredient_id": "ING31", "quantity": 0.05},

    {"dish_id": "D05", "ingredient_id": "ING25", "quantity": 0.18},
    {"dish_id": "D05", "ingredient_id": "ING17", "quantity": 0.10},
    {"dish_id": "D05", "ingredient_id": "ING28", "quantity": 0.05},
    {"dish_id": "D05", "ingredient_id": "ING31", "quantity": 0.05},

    {"dish_id": "D06", "ingredient_id": "ING26", "quantity": 0.15},
    {"dish_id": "D06", "ingredient_id": "ING16", "quantity": 0.25},
    {"dish_id": "D06", "ingredient_id": "ING35", "quantity": 0.05},

    {"dish_id": "D07", "ingredient_id": "ING26", "quantity": 0.15},
    {"dish_id": "D07", "ingredient_id": "ING13", "quantity": 0.08},
    {"dish_id": "D07", "ingredient_id": "ING32", "quantity": 0.06},
    {"dish_id": "D07", "ingredient_id": "ING22", "quantity": 1.0},

    {"dish_id": "D08", "ingredient_id": "ING26", "quantity": 0.15},
    {"dish_id": "D08", "ingredient_id": "ING18", "quantity": 0.15},
    {"dish_id": "D08", "ingredient_id": "ING22", "quantity": 1.0},
    {"dish_id": "D08", "ingredient_id": "ING34", "quantity": 0.03},

    {"dish_id": "D09", "ingredient_id": "ING27", "quantity": 1.0},
    {"dish_id": "D09", "ingredient_id": "ING17", "quantity": 0.08},
    {"dish_id": "D09", "ingredient_id": "ING31", "quantity": 0.03},

    {"dish_id": "D10", "ingredient_id": "ING27", "quantity": 1.0},
    {"dish_id": "D10", "ingredient_id": "ING22", "quantity": 2.0},
    {"dish_id": "D10", "ingredient_id": "ING23", "quantity": 0.04},
    {"dish_id": "D10", "ingredient_id": "ING13", "quantity": 0.05},

    {"dish_id": "D11", "ingredient_id": "ING19", "quantity": 0.15},
    {"dish_id": "D11", "ingredient_id": "ING28", "quantity": 0.10},
    {"dish_id": "D11", "ingredient_id": "ING22", "quantity": 1.0},

    {"dish_id": "D12", "ingredient_id": "ING20", "quantity": 0.08},
    {"dish_id": "D12", "ingredient_id": "ING17", "quantity": 0.06},
    {"dish_id": "D12", "ingredient_id": "ING25", "quantity": 0.08},
    {"dish_id": "D12", "ingredient_id": "ING28", "quantity": 0.05},

    {"dish_id": "D13", "ingredient_id": "ING29", "quantity": 0.18},
    {"dish_id": "D13", "ingredient_id": "ING30", "quantity": 0.02},

    {"dish_id": "D14", "ingredient_id": "ING16", "quantity": 0.22},
    {"dish_id": "D14", "ingredient_id": "ING35", "quantity": 0.06},

    {"dish_id": "D15", "ingredient_id": "ING01", "quantity": 0.025},
    {"dish_id": "D15", "ingredient_id": "ING02", "quantity": 0.08},
    {"dish_id": "D15", "ingredient_id": "ING12", "quantity": 0.01},

    {"dish_id": "D16", "ingredient_id": "ING01", "quantity": 0.015},
    {"dish_id": "D16", "ingredient_id": "ING02", "quantity": 0.12},
    {"dish_id": "D16", "ingredient_id": "ING03", "quantity": 0.06},

    {"dish_id": "D17", "ingredient_id": "ING01", "quantity": 0.022},
    {"dish_id": "D17", "ingredient_id": "ING02", "quantity": 0.06},
    {"dish_id": "D17", "ingredient_id": "ING04", "quantity": 0.08},

    {"dish_id": "D18", "ingredient_id": "ING01", "quantity": 0.025},

    {"dish_id": "D19", "ingredient_id": "ING05", "quantity": 0.012},
    {"dish_id": "D19", "ingredient_id": "ING08", "quantity": 0.20},
    {"dish_id": "D19", "ingredient_id": "ING09", "quantity": 0.08},
    {"dish_id": "D19", "ingredient_id": "ING10", "quantity": 0.03},
    {"dish_id": "D19", "ingredient_id": "ING12", "quantity": 0.03},

    {"dish_id": "D20", "ingredient_id": "ING05", "quantity": 0.015},
    {"dish_id": "D20", "ingredient_id": "ING03", "quantity": 0.08},
    {"dish_id": "D20", "ingredient_id": "ING02", "quantity": 0.06},
    {"dish_id": "D20", "ingredient_id": "ING07", "quantity": 0.05},
    {"dish_id": "D20", "ingredient_id": "ING12", "quantity": 0.02},

    {"dish_id": "D21", "ingredient_id": "ING06", "quantity": 0.012},
    {"dish_id": "D21", "ingredient_id": "ING03", "quantity": 0.12},
    {"dish_id": "D21", "ingredient_id": "ING12", "quantity": 0.02},

    {"dish_id": "D22", "ingredient_id": "ING11", "quantity": 0.45},
    {"dish_id": "D22", "ingredient_id": "ING12", "quantity": 0.02},
]

# 5. Event Spikes — sự kiện bất thường
EVENT_TYPES = [
    {"name": "don_tiec_dot_xuat", "prob": 0.02, "mult_range": (1.6, 2.3)},
    {"name": "su_kien_dia_phuong", "prob": 0.015, "mult_range": (1.4, 1.9)},
    {"name": "thoi_tiet_cuc_doan", "prob": 0.02, "mult_range": (0.4, 0.65)},
    {"name": "su_co_von_hanh", "prob": 0.01, "mult_range": (0.3, 0.5)},
]

def get_event_multiplier():
    """Trả về (multiplier, event_name hoặc None) cho 1 ngày."""
    for event in EVENT_TYPES:
        if random.random() < event["prob"]:
            return random.uniform(*event["mult_range"]), event["name"]
    return 1.0, None


def generate_smooth_weather_series(start_date, total_days):
    """
    Sinh chuỗi thời tiết 730 ngày tại Việt Nam với đường cong mượt mà:
    - Nhiệt độ dao động theo hàm điều hòa chu kỳ năm + nhiễu mượt AR(1)
    - Mùa mưa (tháng 5-10) xuất hiện theo đợt tự nhiên
    """
    weather_series = []
    in_rain_spell = 0

    for i in range(total_days):
        cur_date = start_date + timedelta(days=i)
        day_of_year = cur_date.timetuple().tm_yday
        month = cur_date.month

        # Nhiệt độ điều hòa: đỉnh điểm tháng 4-6 ~ 35°C, thấp điểm tháng 12-1 ~ 26.5°C
        seasonal_temp = 31.5 + 4.0 * math.sin(2 * math.pi * (day_of_year - 80) / 365)
        temp_noise = random.gauss(0, 0.8)
        daily_temp = round(seasonal_temp + temp_noise, 1)

        is_rainy_season = 1 if month in [5, 6, 7, 8, 9, 10] else 0

        if in_rain_spell > 0:
            in_rain_spell -= 1
            precip = round(random.uniform(8.0, 28.0), 1)
            cond = "mua_rao" if precip < 25.0 else "mua_bao"
        else:
            rain_chance = 0.40 if is_rainy_season else 0.08
            if random.random() < rain_chance:
                in_rain_spell = random.choice([1, 2, 3])
                precip = round(random.uniform(5.0, 22.0), 1)
                cond = "mua_rao"
            else:
                precip = 0.0
                if daily_temp >= 33.5:
                    cond = "nang_nong"
                elif daily_temp < 20.0:
                    cond = "lanh_ret"
                else:
                    cond = "nang_dep"

        weather_series.append({
            "date": cur_date.strftime("%Y-%m-%d"),
            "temperature": daily_temp,
            "precipitation_mm": precip,
            "weather_condition": cond
        })

    return weather_series


def generate_big_dataset():
    print("=" * 75)
    print("BẮT ĐẦU SINH DỮ LIỆU ĐA DẠNG v3 (3 CHI NHÁNH, 22 MÓN, 730 NGÀY)")
    print("Cải tiến: +Làm mượt Thời tiết & Khí hậu, +Event spikes, +Tết VN, nhiễu 12%")
    print("=" * 75)

    end_date = datetime(2026, 9, 17)
    start_date = end_date - timedelta(days=729)
    total_days = 730

    # Sinh chuỗi thời tiết 730 ngày mượt mà
    weather_series = generate_smooth_weather_series(start_date, total_days)
    weather_map = {w["date"]: w for w in weather_series}
    print(f"-> Đã sinh chuỗi thời tiết {total_days} ngày với đường cong mượt mà.")

    # Pre-compute Tết dates
    tet_dates_in_range = {}
    for year in range(start_date.year, end_date.year + 1):
        try:
            tet_dates_in_range[year] = get_tet_date(year)
        except (ValueError, KeyError):
            pass

    calendar_rows = []
    sales_rows = []

    current_date = start_date
    day_idx = 0

    # Khởi tạo bộ nhớ làm mượt thời tiết (Exponential Smoothing) cho từng chi nhánh
    prev_weather_mult = {b["id"]: 1.0 for b in BRANCHES}

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

        trend = 1.0 + (day_idx / total_days) * 0.20
        month = current_date.month

        # Thời tiết ngày này
        w_today = weather_map[date_str]
        t_val = w_today["temperature"]
        p_val = w_today["precipitation_mm"]
        w_cond = w_today["weather_condition"]

        # Tết multiplier
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

            event_mult, event_name = get_event_multiplier()

            for dish in DISHES:
                base = dish["base_sales"]
                b_weight = dish["branch_weights"].get(b_id, 1.0)
                
                day_mult = dish["weekend_mult"] if is_wknd else dish["weekday_mult"]
                hol_mult = 1.45 if is_hol else 1.0

                # Hệ số tác động thời tiết mượt mà theo danh mục
                raw_weather_mult = 1.0
                if w_cond == "nang_nong":
                    if dish["category"] in ["Trà & Trái Cây", "Cà Phê", "Đồ Ăn Nhẹ"]:
                        raw_weather_mult = 1.25 + 0.05 * min(1.0, max(0.0, (t_val - 33.5) / 3.0))
                    elif dish["category"] in ["Món Nước"]:
                        raw_weather_mult = 0.90
                elif w_cond == "mua_rao":
                    if dish["category"] in ["Món Nước"]:
                        raw_weather_mult = 1.20
                    elif dish["category"] in ["Trà & Trái Cây"]:
                        raw_weather_mult = 0.85
                elif w_cond == "mua_bao":
                    raw_weather_mult = 0.55
                elif w_cond == "lanh_ret":
                    if dish["category"] in ["Món Nước"]:
                        raw_weather_mult = 1.28
                    elif dish["category"] in ["Trà & Trái Cây"]:
                        raw_weather_mult = 0.78

                # Làm mượt (Smooth filter: 70% hiện tại + 30% hôm trước)
                weather_mult = 0.75 * raw_weather_mult + 0.25 * prev_weather_mult[b_id]
                prev_weather_mult[b_id] = weather_mult

                # Tương tác phi tuyến: branch_type × weekend × weather
                interaction_mult = 1.0
                if is_wknd and w_cond == "nang_nong":
                    if branch_type == "tra_sua":
                        interaction_mult = 1.15
                    elif branch_type == "bistro":
                        interaction_mult = 1.05
                elif is_wknd and (month in [11, 12, 1, 2] or w_cond == "lanh_ret"):
                    if branch_type == "tra_sua":
                        interaction_mult = 0.85
                    elif branch_type == "am_thuc_truyen_thong":
                        interaction_mult = 1.10

                # Nhiễu Gauss 12%
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
                    "event_flag": event_name,
                    "weather_condition": w_cond,
                    "temperature": t_val,
                    "precipitation_mm": p_val
                })

        current_date += timedelta(days=1)
        day_idx += 1

    print(f"-> Đã sinh {len(sales_rows)} bản ghi doanh số ({total_days} ngày x 3 chi nhánh x 22 món).")

    # Sinh Tồn Kho
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

    # Sinh Pre-orders
    tomorrow_str = (end_date + timedelta(days=1)).strftime("%Y-%m-%d")
    preorders = [
        {"id": 1, "branch_id": "BRANCH_01", "date": tomorrow_str, "customer_name": "Công ty TechCorp (Họp sáng)", "dish_id": "D15", "dish_name": "Cà Phê Sữa Đá Sài Gòn", "quantity": 25, "note": "Giao lúc 8h30"},
        {"id": 2, "branch_id": "BRANCH_01", "date": tomorrow_str, "customer_name": "Ngân hàng VietFin (Tiệc trưa)", "dish_id": "D08", "dish_name": "Cơm Tấm Sườn Bì Chả", "quantity": 30, "note": "Giao lúc 11h30"},
        {"id": 3, "branch_id": "BRANCH_02", "date": tomorrow_str, "customer_name": "CLB Guitar Sinh Viên (Offline)", "dish_id": "D20", "dish_name": "Trà Sữa Trân Châu Ô Long", "quantity": 40, "note": "Nhận tại quán lúc 14h00"},
        {"id": 4, "branch_id": "BRANCH_02", "date": tomorrow_str, "customer_name": "Sinh nhật bạn Minh Anh", "dish_id": "D14", "dish_name": "Gà Rán Giòn Cay (2 miếng)", "quantity": 20, "note": "Bàn số 5 lúc 18h30"},
        {"id": 5, "branch_id": "BRANCH_03", "date": tomorrow_str, "customer_name": "Gia đình bác Hùng (Họp mặt)", "dish_id": "D01", "dish_name": "Phở Bò Tái Nạm", "quantity": 18, "note": "Bàn VIP 1 lúc 7h30 sáng"},
        {"id": 6, "branch_id": "BRANCH_03", "date": tomorrow_str, "customer_name": "Đoàn khách du lịch Đà Nẵng", "dish_id": "D03", "dish_name": "Bún Chả Hà Nội", "quantity": 35, "note": "Giao lúc 12h00"},
    ]

    # Sinh Lô Hàng FEFO
    batches = [
        {"id": 1, "branch_id": "BRANCH_01", "ingredient_id": "ING13", "batch_code": "LOT-BEEF-01", "quantity_remaining": 6.0, "received_date": "2026-09-15", "expiry_date": "2026-09-18"},
        {"id": 2, "branch_id": "BRANCH_01", "ingredient_id": "ING24", "batch_code": "LOT-PHO-01", "quantity_remaining": 10.0, "received_date": "2026-09-16", "expiry_date": "2026-09-18"},
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
        with open(path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)
        print(f"-> Đã lưu CSV: {filename} ({len(rows)} dòng)")

    save_csv("branches.csv", ["id", "name", "address", "type"], BRANCHES)
    save_csv("dishes.csv", ["id", "name", "category", "price", "base_sales", "weekend_mult", "weekday_mult"], DISHES)
    save_csv("ingredients.csv", ["id", "name", "unit", "cost_per_unit", "shelf_life_days", "min_stock"], INGREDIENTS)
    save_csv("recipes.csv", ["dish_id", "ingredient_id", "quantity"], RECIPES)
    save_csv("calendar.csv", ["date", "day_of_week", "day_name", "is_weekend", "is_holiday", "holiday_name"], calendar_rows)
    save_csv("sales.csv", ["date", "branch_id", "branch_name", "dish_id", "dish_name", "category", "quantity", "revenue", "event_flag", "weather_condition", "temperature", "precipitation_mm"], sales_rows)
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
        event_flag TEXT,
        weather_condition TEXT,
        temperature REAL,
        precipitation_mm REAL
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

    cur.executemany("INSERT INTO sales (date, branch_id, branch_name, dish_id, dish_name, category, quantity, revenue, event_flag, weather_condition, temperature, precipitation_mm) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [(s["date"], s["branch_id"], s["branch_name"], s["dish_id"], s["dish_name"], s["category"], s["quantity"], s["revenue"], s.get("event_flag"), s.get("weather_condition"), s.get("temperature"), s.get("precipitation_mm")) for s in sales_rows])

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

    # Đồng bộ sang root foodflow.db
    shutil.copy2(DB_PATH, ROOT_DB_PATH)

    print("=" * 75)
    print(f"NẠP THÀNH CÔNG VÀO SQLITE: {DB_PATH}")
    print(f"Tổng kết: 3 Chi Nhánh | 22 Món | 35 Nguyên Liệu | {len(sales_rows)} Bản ghi Sales (730 ngày)")
    print(f"Cải tiến v3: Làm mượt thời tiết (Smooth Transition), Weather Dynamics, Tết VN, Nhiễu 12%")
    print("=" * 75)

if __name__ == "__main__":
    generate_big_dataset()
