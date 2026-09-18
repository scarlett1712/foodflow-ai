"""
backend/app/main.py
FastAPI Server chính cho FoodFlow AI v2.1:
- Tách biệt: Upload Lịch Sử Bán Hàng (Sales) vs Upload Lịch Sử Đi Chợ / Mua Hàng (Purchases)
- Khi tải lên lịch sử mua hàng -> Tự động CỘNG DỒN TỒN KHO (Inventory) & TẠO LÔ HẠN DÙNG (FEFO)
- Quản lý Chi Nhánh tùy biến, Món Ăn, Nguyên Liệu (AI Smart Tagging & Review)
- Đơn Đặt Trước Đa Món (Multi-dish Preorders)
- Gợi Ý Mua Hàng Thông Minh, Dự Báo Nhu Cầu XGBoost, Quản Lý Tồn Kho FEFO
- Chế độ Dữ liệu Trắng & Nạp Dữ liệu Mẫu Demo
"""

import os
import sys
import csv
import json
import sqlite3
import io
import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from .forecasting.predictor import get_forecast_for_next_days
from .forecasting.pipeline import train_and_evaluate_all
from .services.recommendation_service import get_purchase_recommendations
from .services.ai_variance_evaluator import evaluate_purchase_variance
from .services.solana_service import (
    compute_batch_hash,
    compute_po_hash,
    generate_batch_proof,
    generate_po_proof,
    notarize_batch_onchain,
    notarize_purchase_order_onchain,
    verify_onchain_record,
    get_solana_network_status,
    AUTHORITY_PUBKEY_STR
)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "foodflow.db")

app = FastAPI(
    title="FoodFlow AI API",
    description="Hệ thống AI Dự đoán Nhu cầu Nguyên liệu & Gợi ý Mua hàng cho Nhà hàng F&B (Tích hợp Solana Devnet Audit)",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Đảm bảo schema đầy đủ cho cả purchase_history và Solana Devnet Audit Trail
def init_db_schema():
    conn = get_db()
    cur = conn.cursor()
    
    # Bảng purchase_history lưu lịch sử đi chợ / nhập hàng
    cur.execute("""
    CREATE TABLE IF NOT EXISTS purchase_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        branch_id TEXT NOT NULL,
        ingredient_id TEXT NOT NULL,
        ingredient_name TEXT NOT NULL,
        quantity_purchased REAL NOT NULL,
        unit TEXT NOT NULL,
        unit_price REAL NOT NULL,
        total_cost REAL NOT NULL,
        batch_code TEXT,
        expiry_date TEXT,
        record_hash TEXT,
        solana_tx TEXT,
        solana_status TEXT,
        verified_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    try:
        cur.execute("ALTER TABLE ingredients ADD COLUMN category_tag TEXT")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE preorders ADD COLUMN items_json TEXT")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE inventory_batches ADD COLUMN batch_hash TEXT")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE inventory_batches ADD COLUMN solana_tx TEXT")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE inventory_batches ADD COLUMN solana_status TEXT")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE inventory_batches ADD COLUMN verified_at TEXT")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE purchase_history ADD COLUMN record_hash TEXT")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE purchase_history ADD COLUMN solana_tx TEXT")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE purchase_history ADD COLUMN solana_status TEXT")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE purchase_history ADD COLUMN verified_at TEXT")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE purchase_history ADD COLUMN variance_pct REAL DEFAULT 0.0")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE purchase_history ADD COLUMN variance_reason TEXT")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE purchase_history ADD COLUMN ai_verdict TEXT")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE purchase_history ADD COLUMN ai_notes TEXT")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE purchase_history ADD COLUMN ai_adjustment TEXT")
    except Exception:
        pass

    conn.commit()
    conn.close()

init_db_schema()

# ==========================================
# PYDANTIC SCHEMAS
# ==========================================

class BranchCreate(BaseModel):
    id: str
    name: str
    address: str
    type: str

class IngredientCreate(BaseModel):
    id: str
    name: str
    unit: str
    cost_per_unit: float
    shelf_life_days: int = 30
    min_stock: float = 5.0
    category_tag: Optional[str] = "Khác"
    initial_stock: Optional[float] = 0.0

class SmartTagRequest(BaseModel):
    names: List[str]

class DishCreate(BaseModel):
    id: str
    name: str
    category: str
    price: float

class RecipeItem(BaseModel):
    dish_id: str
    ingredient_id: str
    quantity: float

class SmartRecipeItemCreate(BaseModel):
    dish_id: str
    ingredient_id: Optional[str] = None
    ingredient_name: Optional[str] = None
    quantity: float
    unit: Optional[str] = "kg"
    cost_per_unit: Optional[float] = 50000.0

class DishIngredientInput(BaseModel):
    ingredient_id: Optional[str] = None
    ingredient_name: Optional[str] = None
    quantity: float
    unit: Optional[str] = "kg"
    cost_per_unit: Optional[float] = 50000.0

class DishWithRecipeCreate(BaseModel):
    id: Optional[str] = None
    name: str
    category: str
    price: float
    ingredients: List[DishIngredientInput] = []

class PreorderItemSchema(BaseModel):
    dish_id: str
    dish_name: str
    quantity: int

class PreorderCreateMulti(BaseModel):
    branch_id: str = "BRANCH_01"
    date: str
    customer_name: str
    note: Optional[str] = ""
    items: List[PreorderItemSchema]

class InventoryUpdate(BaseModel):
    branch_id: str
    ingredient_id: str
    quantity: float

class ManualPurchaseRecord(BaseModel):
    branch_id: str
    date: str
    items: List[Dict[str, Any]]
    variance_reason: Optional[str] = ""
    ai_assessment: Optional[Dict[str, Any]] = None

class VarianceAnalysisRequest(BaseModel):
    branch_id: str = "BRANCH_01"
    date: Optional[str] = None
    items: List[Dict[str, Any]]
    reason: Optional[str] = ""

class SolanaVerifyRequest(BaseModel):
    expected_hash: str
    tx_signature: str

class SolanaNotarizePORequest(BaseModel):
    branch_id: str
    date: str
    total_spent: float
    items: List[Dict[str, Any]]

# ==========================================
# 1. API CHI NHÁNH (BRANCHES)
# ==========================================

@app.get("/api/branches")
def get_branches():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM branches")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

@app.post("/api/branches")
def create_branch(b: BranchCreate):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO branches (id, name, address, type) VALUES (?, ?, ?, ?)",
                (b.id, b.name, b.address, b.type))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Đã thêm chi nhánh '{b.name}'"}

@app.delete("/api/branches/{branch_id}")
def delete_branch(branch_id: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM branches WHERE id = ?", (branch_id,))
    cur.execute("DELETE FROM sales WHERE branch_id = ?", (branch_id,))
    cur.execute("DELETE FROM inventory WHERE branch_id = ?", (branch_id,))
    cur.execute("DELETE FROM inventory_batches WHERE branch_id = ?", (branch_id,))
    cur.execute("DELETE FROM preorders WHERE branch_id = ?", (branch_id,))
    cur.execute("DELETE FROM purchase_history WHERE branch_id = ?", (branch_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Đã xóa chi nhánh"}

# ==========================================
# 2. API NGUYÊN LIỆU & AI TAGGING
# ==========================================

def classify_ingredient_tag(name: str) -> str:
    name_lower = name.lower()
    if any(k in name_lower for k in ["bò", "gà", "heo", "thịt", "lợn", "sườn", "chả", "giò", "nem", "xúc xích", "cá", "tôm", "hải sản"]):
        return "🥩 Thịt & Hải sản tươi"
    if any(k in name_lower for k in ["sữa", "kem béo", "rich", "phô mai", "bơ", "trứng"]):
        return "🥛 Sữa & Đồ béo"
    if any(k in name_lower for k in ["cà phê", "trà", "matcha", "cacao"]):
        return "☕ Cà phê & Trà"
    if any(k in name_lower for k in ["cam", "chanh", "dưa", "đào", "tắc", "xoài", "dâu", "trái cây", "hoa quả"]):
        return "🍊 Trái cây & Củ quả"
    if any(k in name_lower for k in ["rau", "xà lách", "hành", "ngò", "sả", "ớt", "dưa chua", "cải", "tỏi", "giá"]):
        return "🥬 Rau gia vị tươi"
    if any(k in name_lower for k in ["phở", "bún", "bánh mì", "gạo", "cơm", "khoai", "bột", "mì"]):
        return "🍚 Tinh bột & Bánh"
    if any(k in name_lower for k in ["trân châu", "siro", "syrup", "thạch", "đường", "sốt", "mè"]):
        return "🧋 Topping & Siro"
    return "🧂 Gia vị & Khác"

@app.post("/api/ingredients/smart-tag")
def smart_tag_ingredients(req: SmartTagRequest):
    results = []
    for name in req.names:
        tag = classify_ingredient_tag(name)
        results.append({"name": name, "suggested_tag": tag})
    return {"status": "success", "tags": results}

@app.get("/api/ingredients")
def get_ingredients():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ingredients ORDER BY id ASC")
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        if not r.get("category_tag"):
            r["category_tag"] = classify_ingredient_tag(r["name"])
    conn.close()
    return rows

@app.post("/api/ingredients")
def create_ingredient(ing: IngredientCreate, branch_id: str = "BRANCH_01"):
    conn = get_db()
    cur = conn.cursor()
    tag = ing.category_tag or classify_ingredient_tag(ing.name)
    cur.execute("""
        INSERT OR REPLACE INTO ingredients (id, name, unit, cost_per_unit, shelf_life_days, min_stock, category_tag)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (ing.id, ing.name, ing.unit, ing.cost_per_unit, ing.shelf_life_days, ing.min_stock, tag))
    
    if ing.initial_stock > 0:
        cur.execute("""
            INSERT OR REPLACE INTO inventory (branch_id, ingredient_id, quantity)
            VALUES (?, ?, ?)
        """, (branch_id, ing.id, ing.initial_stock))
        
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Đã lưu nguyên liệu '{ing.name}'"}

@app.delete("/api/ingredients/{ingredient_id}")
def delete_ingredient(ingredient_id: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM ingredients WHERE id = ?", (ingredient_id,))
    cur.execute("DELETE FROM recipes WHERE ingredient_id = ?", (ingredient_id,))
    cur.execute("DELETE FROM inventory WHERE ingredient_id = ?", (ingredient_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Đã xóa nguyên liệu"}

# ==========================================
# 3. API MÓN ĂN & CÔNG THỨC (DISHES & RECIPES)
# ==========================================

@app.get("/api/dishes")
def get_dishes(category: Optional[str] = None):
    conn = get_db()
    cur = conn.cursor()
    if category:
        cur.execute("SELECT * FROM dishes WHERE category = ?", (category,))
    else:
        cur.execute("SELECT * FROM dishes")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

@app.post("/api/dishes")
def create_dish(dish: DishCreate):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO dishes (id, name, category, price) VALUES (?, ?, ?, ?)",
                (dish.id, dish.name, dish.category, dish.price))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Đã lưu món '{dish.name}'"}

@app.post("/api/dishes/with-recipe")
def create_dish_with_recipe(dish: DishWithRecipeCreate):
    conn = get_db()
    cur = conn.cursor()
    
    # 1. Sinh dish_id nếu chưa có
    dish_id = dish.id
    if not dish_id or dish_id.strip() == "":
        cur.execute("SELECT count(*) FROM dishes")
        c = cur.fetchone()[0] + 1
        dish_id = f"D_{c:02d}"
    
    # 2. Lưu món ăn
    cur.execute("INSERT OR REPLACE INTO dishes (id, name, category, price) VALUES (?, ?, ?, ?)",
                (dish_id, dish.name.strip(), dish.category, dish.price))
    
    # Xóa công thức cũ của món này nếu có
    cur.execute("DELETE FROM recipes WHERE dish_id = ?", (dish_id,))
    
    added_ingredients = []
    
    # 3. Duyệt và lưu từng nguyên liệu
    for ing in dish.ingredients:
        qty = float(ing.quantity) if ing.quantity else 0
        if qty <= 0:
            continue
            
        target_ing_id = ing.ingredient_id
        if not target_ing_id or target_ing_id == "NEW" or target_ing_id.strip() == "":
            ing_name = (ing.ingredient_name or "").strip()
            if not ing_name:
                continue
            
            # Kiểm tra xem tên nguyên liệu đã tồn tại chưa
            cur.execute("SELECT id FROM ingredients WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))", (ing_name,))
            existing = cur.fetchone()
            if existing:
                target_ing_id = existing[0]
            else:
                cur.execute("SELECT count(*) FROM ingredients")
                ic = cur.fetchone()[0] + 1
                target_ing_id = f"ING_{ic:03d}"
                tag = classify_ingredient_tag(ing_name)
                unit = ing.unit or "kg"
                cost = float(ing.cost_per_unit) if ing.cost_per_unit and float(ing.cost_per_unit) > 0 else 50000.0
                cur.execute("""
                    INSERT INTO ingredients (id, name, unit, cost_per_unit, shelf_life_days, min_stock, category_tag)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (target_ing_id, ing_name, unit, cost, 7, 2.0, tag))
                
                # Khởi tạo tồn kho 0
                cur.execute("SELECT id FROM branches")
                branches = cur.fetchall()
                for b in branches:
                    cur.execute("INSERT OR IGNORE INTO inventory (branch_id, ingredient_id, quantity) VALUES (?, ?, 0)", (b[0], target_ing_id))
        
        # Lưu vào recipes
        cur.execute("INSERT INTO recipes (dish_id, ingredient_id, quantity) VALUES (?, ?, ?)",
                    (dish_id, target_ing_id, qty))
        added_ingredients.append(target_ing_id)
        
    conn.commit()
    conn.close()
    
    return {
        "status": "success",
        "message": f"Đã lưu thành công món '{dish.name}' cùng {len(added_ingredients)} nguyên liệu định lượng!",
        "dish_id": dish_id,
        "ingredients_count": len(added_ingredients)
    }

@app.delete("/api/dishes/{dish_id}")
def delete_dish(dish_id: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM dishes WHERE id = ?", (dish_id,))
    cur.execute("DELETE FROM recipes WHERE dish_id = ?", (dish_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Đã xóa món {dish_id}"}

@app.get("/api/recipes")
def get_recipes(dish_id: Optional[str] = None):
    conn = get_db()
    cur = conn.cursor()
    query = """
        SELECT r.id, r.dish_id, d.name as dish_name, d.category as dish_category,
               r.ingredient_id, i.name as ingredient_name, i.unit, r.quantity
        FROM recipes r
        JOIN dishes d ON r.dish_id = d.id
        JOIN ingredients i ON r.ingredient_id = i.id
    """
    if dish_id:
        query += " WHERE r.dish_id = ?"
        cur.execute(query, (dish_id,))
    else:
        cur.execute(query)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

@app.post("/api/recipes")
def save_recipe_item(item: RecipeItem):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM recipes WHERE dish_id = ? AND ingredient_id = ?", (item.dish_id, item.ingredient_id))
    cur.execute("INSERT INTO recipes (dish_id, ingredient_id, quantity) VALUES (?, ?, ?)",
                (item.dish_id, item.ingredient_id, item.quantity))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Đã lưu công thức"}

@app.post("/api/recipes/smart-add")
def smart_add_recipe_item(item: SmartRecipeItemCreate):
    conn = get_db()
    cur = conn.cursor()
    
    # 1. Tìm hoặc tự động tạo ingredient nếu chưa có
    target_ing_id = item.ingredient_id
    if not target_ing_id or target_ing_id == "NEW" or target_ing_id.strip() == "":
        ing_name = (item.ingredient_name or "").strip()
        if not ing_name:
            conn.close()
            raise HTTPException(status_code=400, detail="Vui lòng nhập tên nguyên liệu")
        
        # Check if exists by name (case-insensitive)
        cur.execute("SELECT id FROM ingredients WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))", (ing_name,))
        existing = cur.fetchone()
        if existing:
            target_ing_id = existing[0]
        else:
            # Generate new id
            cur.execute("SELECT count(*) FROM ingredients")
            c = cur.fetchone()[0] + 1
            target_ing_id = f"ING_{c:03d}"
            
            tag = classify_ingredient_tag(ing_name)
            unit = item.unit or "kg"
            cost = float(item.cost_per_unit) if item.cost_per_unit and float(item.cost_per_unit) > 0 else 50000.0
            cur.execute("""
                INSERT INTO ingredients (id, name, unit, cost_per_unit, shelf_life_days, min_stock, category_tag)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (target_ing_id, ing_name, unit, cost, 7, 2.0, tag))
            
            # Khởi tạo tồn kho ban đầu cho các chi nhánh nếu có
            cur.execute("SELECT id FROM branches")
            branches = cur.fetchall()
            for b in branches:
                cur.execute("INSERT OR IGNORE INTO inventory (branch_id, ingredient_id, quantity) VALUES (?, ?, 0)", (b[0], target_ing_id))
    
    # 2. Lưu vào recipes
    cur.execute("DELETE FROM recipes WHERE dish_id = ? AND ingredient_id = ?", (item.dish_id, target_ing_id))
    cur.execute("INSERT INTO recipes (dish_id, ingredient_id, quantity) VALUES (?, ?, ?)",
                (item.dish_id, target_ing_id, float(item.quantity)))
    
    conn.commit()
    conn.close()
    return {
        "status": "success",
        "message": f"Đã lưu nguyên liệu vào công thức món (Mã: {target_ing_id})",
        "ingredient_id": target_ing_id
    }

@app.delete("/api/recipes/{dish_id}/{ingredient_id}")
def delete_recipe_item(dish_id: str, ingredient_id: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM recipes WHERE dish_id = ? AND ingredient_id = ?", (dish_id, ingredient_id))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Đã xóa nguyên liệu khỏi công thức"}

# ==========================================
# 4. API TẢI LÊN LỊCH SỬ BÁN HÀNG (SALES IMPORT)
# ==========================================

def parse_tabular_file(file_content: bytes, filename: str) -> pd.DataFrame:
    """Hỗ trợ đọc cả file Excel (.xlsx, .xls) và file CSV với tự động phát hiện encoding"""
    filename_lower = filename.lower()
    if filename_lower.endswith('.xlsx') or filename_lower.endswith('.xls'):
        return pd.read_excel(io.BytesIO(file_content))
    else:
        for encoding in ['utf-8-sig', 'utf-8', 'cp1252', 'latin1']:
            try:
                return pd.read_csv(io.StringIO(file_content.decode(encoding)))
            except Exception:
                continue
        raise ValueError("Không thể đọc định dạng file. Vui lòng sử dụng file .xlsx hoặc .csv hợp lệ")

# ==========================================
# 4. API TẢI LÊN LỊCH SỬ BÁN HÀNG & CÔNG THỨC (EXCEL & CSV)
# ==========================================

@app.get("/api/sales/template")
def download_sales_template(format: str = Query("excel", regex="^(excel|csv)$")):
    sample_data = [
        {"date": "2026-09-17", "branch_id": "BRANCH_01", "dish_id": "D01", "dish_name": "Phở Bò Tái Nạm", "category": "Phở & Bún", "quantity": 95, "revenue": 5700000},
        {"date": "2026-09-17", "branch_id": "BRANCH_01", "dish_id": "D06", "dish_name": "Cơm Gà Xối Mỡ", "category": "Cơm & Bánh Mì", "quantity": 80, "revenue": 4160000},
        {"date": "2026-09-17", "branch_id": "BRANCH_01", "dish_id": "D15", "dish_name": "Cà Phê Sữa Đá", "category": "Cà Phê", "quantity": 160, "revenue": 4480000},
        {"date": "2026-09-18", "branch_id": "BRANCH_01", "dish_id": "D01", "dish_name": "Phở Bò Tái Nạm", "category": "Phở & Bún", "quantity": 105, "revenue": 6300000},
        {"date": "2026-09-18", "branch_id": "BRANCH_01", "dish_id": "D06", "dish_name": "Cơm Gà Xối Mỡ", "category": "Cơm & Bánh Mì", "quantity": 88, "revenue": 4576000},
    ]
    df = pd.DataFrame(sample_data)

    if format == "excel":
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='LichSuBanHang')
        output.seek(0)
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=foodflow_mau_lich_su_ban_hang.xlsx"}
        )
    else:
        output = io.StringIO()
        df.to_csv(output, index=False, encoding="utf-8-sig")
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=foodflow_mau_lich_su_ban_hang.csv"}
        )

@app.get("/api/recipes/template")
def download_recipes_template(format: str = Query("excel", regex="^(excel|csv)$")):
    sample_data = [
        {"dish_id": "D01", "dish_name": "Phở Bò Tái Nạm", "dish_category": "Phở & Bún", "dish_price": 60000, "ingredient_name": "Thịt bò nạm/tái tươi", "quantity": 0.15, "unit": "kg", "cost_per_unit": 260000},
        {"dish_id": "D01", "dish_name": "Phở Bò Tái Nạm", "dish_category": "Phở & Bún", "dish_price": 60000, "ingredient_name": "Bánh phở tươi", "quantity": 0.25, "unit": "kg", "cost_per_unit": 18000},
        {"dish_id": "D01", "dish_name": "Phở Bò Tái Nạm", "dish_category": "Phở & Bún", "dish_price": 60000, "ingredient_name": "Hành hoa & Rau thơm", "quantity": 0.03, "unit": "kg", "cost_per_unit": 35000},
        {"dish_id": "D06", "dish_name": "Cơm Gà Xối Mỡ", "dish_category": "Cơm & Bánh Mì", "dish_price": 52000, "ingredient_name": "Đùi gà tươi góc tư", "quantity": 0.28, "unit": "kg", "cost_per_unit": 85000},
        {"dish_id": "D06", "dish_name": "Cơm Gà Xối Mỡ", "dish_category": "Cơm & Bánh Mì", "dish_price": 52000, "ingredient_name": "Gạo thơm hạt ngọc", "quantity": 0.18, "unit": "kg", "cost_per_unit": 24000},
        {"dish_id": "D15", "dish_name": "Cà Phê Sữa Đá", "dish_category": "Cà Phê", "dish_price": 28000, "ingredient_name": "Cà phê Robusta mộc", "quantity": 0.025, "unit": "kg", "cost_per_unit": 220000},
        {"dish_id": "D15", "dish_name": "Cà Phê Sữa Đá", "dish_category": "Cà Phê", "dish_price": 28000, "ingredient_name": "Sữa đặc có đường", "quantity": 0.04, "unit": "kg", "cost_per_unit": 65000}
    ]
    df = pd.DataFrame(sample_data)

    if format == "excel":
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='DinhLuongMonAn')
        output.seek(0)
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=foodflow_mau_cong_thuc_mon_an.xlsx"}
        )
    else:
        output = io.StringIO()
        df.to_csv(output, index=False, encoding="utf-8-sig")
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=foodflow_mau_cong_thuc_mon_an.csv"}
        )

def process_sales_dataframe(df: pd.DataFrame) -> int:
    """Helper xử lý DataFrame doanh số và nạp vào DB"""
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    
    date_col = next((c for c in df.columns if c in ["date", "ngay", "ngày"]), None)
    qty_col = next((c for c in df.columns if c in ["quantity", "so_luong", "số_lượng", "qty"]), None)
    
    if not date_col or not qty_col:
        raise ValueError("File doanh số thiếu cột bắt buộc: date (ngày) hoặc quantity (số lượng)")

    dish_name_col = next((c for c in df.columns if c in ["dish_name", "ten_mon", "tên_món", "mon_an", "món"]), None)
    dish_id_col = next((c for c in df.columns if c in ["dish_id", "ma_mon", "mã_món"]), None)
    branch_id_col = next((c for c in df.columns if c in ["branch_id", "chi_nhanh", "mã_chi_nhánh"]), None)
    cat_col = next((c for c in df.columns if c in ["category", "phan_loai", "phân_loại", "nhom"]), None)
    rev_col = next((c for c in df.columns if c in ["revenue", "doanh_thu", "doanh_thu_vnd"]), None)

    conn = get_db()
    cur = conn.cursor()
    saved_count = 0

    for _, row in df.iterrows():
        raw_date = str(row[date_col]).strip()
        if not raw_date or raw_date.lower() == 'nan':
            continue
        try:
            # Parse and standardise date format YYYY-MM-DD
            d_obj = pd.to_datetime(raw_date)
            date_str = d_obj.strftime("%Y-%m-%d")
        except Exception:
            date_str = raw_date[:10]

        qty = int(float(row[qty_col])) if pd.notnull(row[qty_col]) else 0
        if qty < 0:
            continue

        d_name = str(row[dish_name_col]).strip() if dish_name_col and pd.notnull(row[dish_name_col]) else "Món Ăn"
        d_id = str(row[dish_id_col]).strip() if dish_id_col and pd.notnull(row[dish_id_col]) else f"D_{d_name[:3].upper()}"
        b_id = str(row[branch_id_col]).strip() if branch_id_col and pd.notnull(row[branch_id_col]) else "BRANCH_01"
        cat = str(row[cat_col]).strip() if cat_col and pd.notnull(row[cat_col]) else "Món Ăn"
        rev = float(row[rev_col]) if rev_col and pd.notnull(row[rev_col]) else (qty * 50000.0)

        # 1. Đảm bảo lịch calendar tồn tại ngày này
        dow = pd.to_datetime(date_str).weekday()
        is_wknd = 1 if dow in [5, 6] else 0
        cur.execute("""
            INSERT OR IGNORE INTO calendar (date, day_of_week, is_weekend, is_holiday, holiday_name)
            VALUES (?, ?, ?, 0, '')
        """, (date_str, dow, is_wknd))

        # 2. Đảm bảo món ăn tồn tại trong dishes
        cur.execute("""
            INSERT OR IGNORE INTO dishes (id, name, category, price)
            VALUES (?, ?, ?, ?)
        """, (d_id, d_name, cat, round(rev / qty) if qty > 0 else 50000.0))

        # 3. Chèn vào sales
        cur.execute("""
            INSERT INTO sales (date, branch_id, branch_name, dish_id, dish_name, category, quantity, revenue)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (date_str, b_id, b_id, d_id, d_name, cat, qty, rev))
        
        saved_count += 1

    conn.commit()
    conn.close()
    return saved_count

def process_recipes_dataframe(df: pd.DataFrame) -> dict:
    """Helper xử lý DataFrame công thức món ăn & tự động bóc tách nguyên liệu vào kho"""
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    dish_name_col = next((c for c in df.columns if c in ["dish_name", "ten_mon", "tên_món", "mon_an", "món"]), None)
    ing_name_col = next((c for c in df.columns if c in ["ingredient_name", "ten_nguyen_lieu", "tên_nguyên_liệu", "nguyen_lieu", "nguyên_liệu"]), None)
    qty_col = next((c for c in df.columns if c in ["quantity", "dinh_luong", "định_lượng", "so_luong", "qty"]), None)

    if not dish_name_col or not ing_name_col or not qty_col:
        raise ValueError("File công thức thiếu các cột bắt buộc: dish_name (tên món), ingredient_name (tên nguyên liệu), quantity (định lượng)")

    dish_id_col = next((c for c in df.columns if c in ["dish_id", "ma_mon", "mã_món"]), None)
    cat_col = next((c for c in df.columns if c in ["dish_category", "category", "phan_loai", "phân_loại"]), None)
    price_col = next((c for c in df.columns if c in ["dish_price", "price", "gia_ban", "giá_bán"]), None)
    unit_col = next((c for c in df.columns if c in ["unit", "don_vi", "đơn_vị"]), None)
    cost_col = next((c for c in df.columns if c in ["cost_per_unit", "cost", "gia_mua", "giá_mua"]), None)

    conn = get_db()
    cur = conn.cursor()

    dishes_created = 0
    ingredients_created = 0
    recipes_created = 0

    for _, row in df.iterrows():
        d_name = str(row[dish_name_col]).strip() if pd.notnull(row[dish_name_col]) else ""
        ing_name = str(row[ing_name_col]).strip() if pd.notnull(row[ing_name_col]) else ""
        if not d_name or not ing_name:
            continue

        qty = float(row[qty_col]) if pd.notnull(row[qty_col]) else 0.0
        if qty <= 0:
            continue

        # 1. Quản lý Dish
        d_id = str(row[dish_id_col]).strip() if dish_id_col and pd.notnull(row[dish_id_col]) else None
        if not d_id:
            cur.execute("SELECT id FROM dishes WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))", (d_name,))
            existing_dish = cur.fetchone()
            if existing_dish:
                d_id = existing_dish[0]
            else:
                cur.execute("SELECT count(*) FROM dishes")
                dc = cur.fetchone()[0] + 1
                d_id = f"D_{dc:02d}"
                d_cat = str(row[cat_col]).strip() if cat_col and pd.notnull(row[cat_col]) else "Món Ăn"
                d_price = float(row[price_col]) if price_col and pd.notnull(row[price_col]) else 50000.0
                cur.execute("INSERT INTO dishes (id, name, category, price) VALUES (?, ?, ?, ?)", (d_id, d_name, d_cat, d_price))
                dishes_created += 1
        else:
            d_cat = str(row[cat_col]).strip() if cat_col and pd.notnull(row[cat_col]) else "Món Ăn"
            d_price = float(row[price_col]) if price_col and pd.notnull(row[price_col]) else 50000.0
            cur.execute("INSERT OR REPLACE INTO dishes (id, name, category, price) VALUES (?, ?, ?, ?)", (d_id, d_name, d_cat, d_price))

        # 2. Quản lý Ingredient
        cur.execute("SELECT id FROM ingredients WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))", (ing_name,))
        existing_ing = cur.fetchone()
        if existing_ing:
            target_ing_id = existing_ing[0]
        else:
            cur.execute("SELECT count(*) FROM ingredients")
            ic = cur.fetchone()[0] + 1
            target_ing_id = f"ING_{ic:03d}"
            tag = classify_ingredient_tag(ing_name)
            unit = str(row[unit_col]).strip() if unit_col and pd.notnull(row[unit_col]) else "kg"
            cost = float(row[cost_col]) if cost_col and pd.notnull(row[cost_col]) else 50000.0
            cur.execute("""
                INSERT INTO ingredients (id, name, unit, cost_per_unit, shelf_life_days, min_stock, category_tag)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (target_ing_id, ing_name, unit, cost, 7, 2.0, tag))
            
            # Kho khởi tạo
            cur.execute("SELECT id FROM branches")
            branches = cur.fetchall()
            for b in branches:
                cur.execute("INSERT OR IGNORE INTO inventory (branch_id, ingredient_id, quantity) VALUES (?, ?, 0)", (b[0], target_ing_id))
            ingredients_created += 1

        # 3. Quản lý Recipe
        cur.execute("DELETE FROM recipes WHERE dish_id = ? AND ingredient_id = ?", (d_id, target_ing_id))
        cur.execute("INSERT INTO recipes (dish_id, ingredient_id, quantity) VALUES (?, ?, ?)", (d_id, target_ing_id, qty))
        recipes_created += 1

    conn.commit()
    conn.close()
    return {
        "dishes_created": dishes_created,
        "ingredients_created": ingredients_created,
        "recipes_created": recipes_created
    }

@app.post("/api/sales/upload")
async def upload_sales_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        df = parse_tabular_file(content, file.filename)
        saved_count = process_sales_dataframe(df)

        return {
            "status": "success",
            "message": f"Đã nạp thành công {saved_count} bản ghi doanh số lịch sử từ file '{file.filename}'!",
            "rows_count": saved_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi nhập file doanh số: {str(e)}")

@app.post("/api/recipes/upload")
async def upload_recipes_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        df = parse_tabular_file(content, file.filename)
        res = process_recipes_dataframe(df)

        return {
            "status": "success",
            "message": f"Đã bóc tách thành công {res['recipes_created']} định lượng công thức, tự động tạo {res['ingredients_created']} nguyên liệu mới vào kho!",
            "details": res
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi nhập file công thức món: {str(e)}")

@app.post("/api/data/upload-package")
async def upload_data_package(
    sales_file: Optional[UploadFile] = File(None),
    recipes_file: Optional[UploadFile] = File(None)
):
    try:
        results = {}
        
        # 1. Xử lý file công thức trước (nếu có) để tạo món & nguyên liệu
        if recipes_file and recipes_file.filename:
            r_content = await recipes_file.read()
            r_df = parse_tabular_file(r_content, recipes_file.filename)
            r_res = process_recipes_dataframe(r_df)
            results["recipes"] = r_res

        # 2. Xử lý file doanh số bán hàng (nếu có)
        if sales_file and sales_file.filename:
            s_content = await sales_file.read()
            s_df = parse_tabular_file(s_content, sales_file.filename)
            s_count = process_sales_dataframe(s_df)
            results["sales"] = {"rows_count": s_count}

        if not results:
            raise HTTPException(status_code=400, detail="Vui lòng chọn ít nhất 1 file (Doanh số hoặc Công thức) để tải lên!")

        msg_parts = []
        if "recipes" in results:
            msg_parts.append(f"{results['recipes']['recipes_created']} định lượng công thức ({results['recipes']['ingredients_created']} nguyên liệu mới vào kho)")
        if "sales" in results:
            msg_parts.append(f"{results['sales']['rows_count']} dòng doanh số lịch sử")

        return {
            "status": "success",
            "message": f"Nạp dữ liệu thành công: " + ", ".join(msg_parts) + "!",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi nhập gói dữ liệu: {str(e)}")

# ==========================================
# 5. API TẢI LÊN LỊCH SỬ ĐI CHỢ / MUA HÀNG (PURCHASES IMPORT & INVENTORY SYNC)
# ==========================================

@app.get("/api/purchases/template")
def download_purchases_template():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "branch_id", "ingredient_id", "ingredient_name", "quantity_purchased", "unit", "unit_price", "total_cost", "batch_code", "expiry_date"])
    writer.writerow(["2026-09-17", "BRANCH_01", "ING13", "Thịt bò nạm/tái tươi", 20.0, "kg", 260000, 5200000, "LOT-BEEF-02", "2026-09-20"])
    writer.writerow(["2026-09-17", "BRANCH_01", "ING03", "Sữa tươi tiệt trùng", 15.0, "lít", 32000, 480000, "LOT-MILK-02", "2026-09-25"])
    writer.writerow(["2026-09-17", "BRANCH_01", "ING24", "Bánh phở tươi Hà Nội", 25.0, "kg", 18000, 450000, "LOT-PHO-01", "2026-09-18"])
    
    response = Response(content=output.getvalue(), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=foodflow_purchase_template.csv"
    return response

@app.get("/api/purchases/history")
def get_purchase_history(branch_id: Optional[str] = "BRANCH_01", limit: int = 100):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM purchase_history
        WHERE branch_id = ?
        ORDER BY date DESC, id DESC
        LIMIT ?
    """, (branch_id, limit))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

@app.post("/api/purchases/upload")
async def upload_purchases_csv(file: UploadFile = File(...), variance_reason: Optional[str] = Form(None)):
    """
    Tải file lịch sử đi chợ lên:
    1. Ghi vào bảng purchase_history kèm thông tin kiểm toán chênh lệch & Solana
    2. TỰ ĐỘNG CẬP NHẬT TỒN KHO: inventory.quantity = inventory.quantity + quantity_purchased
    3. Nếu có hạn dùng -> thêm vào inventory_batches (FEFO)
    """
    try:
        content = await file.read()
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        
        rows = []
        for r in reader:
            if not r.get("date") or not r.get("quantity_purchased"):
                continue
            
            qty = float(r.get("quantity_purchased", 0))
            price = float(r.get("unit_price", 0))
            total = float(r.get("total_cost", 0)) or (qty * price)

            rows.append({
                "date": r.get("date").strip(),
                "branch_id": r.get("branch_id", "BRANCH_01").strip(),
                "ingredient_id": r.get("ingredient_id", "").strip(),
                "ingredient_name": r.get("ingredient_name", "").strip(),
                "quantity_purchased": qty,
                "unit": r.get("unit", "kg").strip(),
                "unit_price": price,
                "total_cost": total,
                "batch_code": r.get("batch_code", f"LOT-IMP-{r.get('ingredient_id','ING')}").strip(),
                "expiry_date": r.get("expiry_date", "").strip()
            })

        if not rows:
            raise HTTPException(status_code=400, detail="File CSV không chứa dữ liệu mua hàng hợp lệ")

        conn = get_db()
        cur = conn.cursor()

        # Lấy danh sách nguyên liệu để map tên nếu thiếu ID
        cur.execute("SELECT id, name, unit, cost_per_unit, shelf_life_days FROM ingredients")
        ing_dict = {row["id"]: dict(row) for row in cur.fetchall()}
        name_to_id = {row["name"].lower(): row["id"] for row in ing_dict.values()}

        # Đánh giá chênh lệch file nạp lên
        eval_items = []
        for r in rows:
            ing_id = r["ingredient_id"] or name_to_id.get(r["ingredient_name"].lower(), "ING_TEMP")
            eval_items.append({
                "ingredient_id": ing_id,
                "ingredient_name": r["ingredient_name"],
                "quantity": r["quantity_purchased"],
                "cost_per_unit": r["unit_price"],
                "unit": r["unit"]
            })

        file_eval = evaluate_purchase_variance(
            items=eval_items,
            branch_id=rows[0]["branch_id"] if rows else "BRANCH_01",
            reason=variance_reason or "",
            db_path=DB_PATH
        )

        updated_count = 0
        for row in rows:
            ing_id = row["ingredient_id"]
            if not ing_id and row["ingredient_name"].lower() in name_to_id:
                ing_id = name_to_id[row["ingredient_name"].lower()]
                row["ingredient_id"] = ing_id

            if not ing_id:
                # Nếu nguyên liệu chưa có, tự tạo mới
                ing_id = "ING_" + str(len(ing_dict) + 1).zfill(2)
                row["ingredient_id"] = ing_id
                cur.execute("""
                    INSERT OR REPLACE INTO ingredients (id, name, unit, cost_per_unit, shelf_life_days, min_stock, category_tag)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (ing_id, row["ingredient_name"], row["unit"], row["unit_price"], 14, 5.0, classify_ingredient_tag(row["ingredient_name"])))

            # Tính độ lệch giá riêng của dòng
            std_p = ing_dict.get(ing_id, {}).get("cost_per_unit", row["unit_price"] or 1.0)
            row_var_pct = round(((row["unit_price"] - std_p) / std_p * 100), 1) if std_p > 0 else 0.0

            # 1. Ký chứng thực & Lưu vào bảng purchase_history
            po_proof = generate_po_proof({
                "branch_id": row["branch_id"],
                "date": row["date"],
                "total_spent": row["total_cost"],
                "items": [{"ingredient_id": ing_id, "quantity": row["quantity_purchased"], "unit_price": row["unit_price"]}],
                "variance_pct": row_var_pct,
                "variance_reason": variance_reason or "",
                "ai_verdict": file_eval.get("verdict", "COMPLIANT"),
                "ai_assessment": file_eval
            })
            cur.execute("""
                INSERT INTO purchase_history (
                    date, branch_id, ingredient_id, ingredient_name, quantity_purchased,
                    unit, unit_price, total_cost, batch_code, expiry_date, record_hash,
                    solana_tx, solana_status, verified_at,
                    variance_pct, variance_reason, ai_verdict, ai_notes, ai_adjustment
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["date"], row["branch_id"], ing_id, row["ingredient_name"], row["quantity_purchased"],
                row["unit"], row["unit_price"], row["total_cost"], row["batch_code"], row["expiry_date"],
                po_proof["record_hash"], po_proof["tx_signature"], "CONFIRMED", po_proof["notarized_at"],
                row_var_pct, variance_reason or "", file_eval.get("verdict", "COMPLIANT"),
                file_eval.get("ai_notes", ""), file_eval.get("adjustment_strategy", "")
            ))

            # 2. TỰ ĐỘNG CẬP NHẬT TỒN KHO
            cur.execute("""
                INSERT INTO inventory (branch_id, ingredient_id, quantity)
                VALUES (?, ?, ?)
                ON CONFLICT(branch_id, ingredient_id) DO UPDATE SET quantity = quantity + excluded.quantity
            """, (row["branch_id"], ing_id, row["quantity_purchased"]))

            # 3. Thêm vào Lô hàng Hạn dùng (FEFO) nếu có expiry_date & TỰ ĐỘNG CHỨNG THỰC SOLANA
            if row["expiry_date"]:
                batch_id = int(datetime.now().timestamp() * 1000) % 1000000 + updated_count
                b_dict = {
                    "id": batch_id,
                    "branch_id": row["branch_id"],
                    "ingredient_id": ing_id,
                    "ingredient_name": row["ingredient_name"],
                    "batch_code": row["batch_code"],
                    "quantity_remaining": row["quantity_purchased"],
                    "received_date": row["date"],
                    "expiry_date": row["expiry_date"]
                }
                b_proof = generate_batch_proof(b_dict)
                cur.execute("""
                    INSERT INTO inventory_batches (id, branch_id, ingredient_id, batch_code, quantity_remaining, received_date, expiry_date, batch_hash, solana_tx, solana_status, verified_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (batch_id, row["branch_id"], ing_id, row["batch_code"], row["quantity_purchased"], row["date"], row["expiry_date"], b_proof["record_hash"], b_proof["tx_signature"], "CONFIRMED", b_proof["notarized_at"]))

            updated_count += 1

        conn.commit()
        conn.close()

        return {
            "status": "success",
            "message": f"Đã nạp thành công {updated_count} dòng lịch sử đi chợ, TỰ ĐỘNG CẬP NHẬT TỒN KHO và chứng thực Solana Devnet!",
            "updated_items_count": updated_count,
            "sample_preview": rows[:5],
            "ai_assessment": file_eval
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi nhập file đi chợ: {str(e)}")

@app.post("/api/purchases/analyze-variance")
def analyze_purchase_variance(req: VarianceAnalysisRequest):
    """
    Phân tích độ chênh lệch số lượng/giá của đơn đi chợ so với AI baseline
    và thẩm định tính hợp lý của lý do người dùng giải trình.
    """
    try:
        res = evaluate_purchase_variance(
            items=req.items,
            branch_id=req.branch_id,
            reason=req.reason or "",
            target_date=req.date,
            db_path=DB_PATH
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi phân tích chênh lệch: {str(e)}")

@app.post("/api/purchases/record-manual")
def record_manual_purchase(rec: ManualPurchaseRecord):
    """
    Xác nhận đã đi chợ trực tiếp từ Giao diện:
    - Thẩm định chênh lệch số lượng & giá vốn vs AI baseline
    - Lưu vào purchase_history kèm lý do giải trình & kết luận AI
    - Cộng trực tiếp vào inventory & tạo lô FEFO
    - Ký chứng thực Bằng chứng kép (Dual-Commitment) lên Solana Devnet!
    """
    try:
        conn = get_db()
        cur = conn.cursor()
        saved_count = 0
        total_spent = sum(float(item.get("quantity", 0)) * float(item.get("cost_per_unit", 0)) for item in rec.items)
        recorded_items = []

        # 1. Thẩm định chênh lệch & lý do bằng AI Evaluator
        ai_eval = rec.ai_assessment
        if not ai_eval:
            ai_eval = evaluate_purchase_variance(
                items=rec.items,
                branch_id=rec.branch_id,
                reason=rec.variance_reason or "",
                target_date=rec.date,
                db_path=DB_PATH
            )

        variance_pct = float(ai_eval.get("cost_variance_pct", 0.0))
        variance_reason = rec.variance_reason or ""
        ai_verdict = ai_eval.get("verdict", "COMPLIANT")
        ai_notes = ai_eval.get("ai_notes", "")
        ai_adjustment = ai_eval.get("adjustment_strategy", "")

        # 2. Ký chứng thực Bằng chứng kép Đơn mua hàng (PO) lên Solana Devnet
        po_proof = generate_po_proof({
            "branch_id": rec.branch_id,
            "date": rec.date,
            "total_spent": total_spent,
            "items": rec.items,
            "variance_pct": variance_pct,
            "variance_reason": variance_reason,
            "ai_verdict": ai_verdict,
            "ai_assessment": ai_eval
        })

        for item in rec.items:
            qty = float(item.get("quantity", 0))
            if qty <= 0:
                continue

            ing_id = item.get("ingredient_id")
            ing_name = item.get("ingredient_name", "")
            unit = item.get("unit", "kg")
            unit_price = float(item.get("cost_per_unit", 0))
            item_total = qty * unit_price
            batch_code = f"LOT-MANUAL-{rec.date.replace('-','')}-{ing_id}"

            # Lưu purchase history kèm thông tin kiểm toán chênh lệch & AI
            cur.execute("""
                INSERT INTO purchase_history (
                    date, branch_id, ingredient_id, ingredient_name, quantity_purchased,
                    unit, unit_price, total_cost, batch_code, record_hash,
                    solana_tx, solana_status, verified_at,
                    variance_pct, variance_reason, ai_verdict, ai_notes, ai_adjustment
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec.date, rec.branch_id, ing_id, ing_name, qty,
                unit, unit_price, item_total, batch_code, po_proof["record_hash"],
                po_proof["tx_signature"], "CONFIRMED", po_proof["notarized_at"],
                variance_pct, variance_reason, ai_verdict, ai_notes, ai_adjustment
            ))

            # Tự động cập nhật giá vốn chuẩn nếu lý do là biến động giá thị trường
            if ai_eval.get("category") == "MARKET_PRICE_SHOCK" and unit_price > 0:
                cur.execute("UPDATE ingredients SET cost_per_unit = ? WHERE id = ?", (unit_price, ing_id))

            # Cộng dồn vào tồn kho
            cur.execute("""
                INSERT INTO inventory (branch_id, ingredient_id, quantity)
                VALUES (?, ?, ?)
                ON CONFLICT(branch_id, ingredient_id) DO UPDATE SET quantity = quantity + excluded.quantity
            """, (rec.branch_id, ing_id, qty))

            # Tạo batch FEFO và ký chứng thực
            batch_id = int(datetime.now().timestamp() * 1000) % 1000000 + saved_count
            expiry_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
            b_proof = generate_batch_proof({
                "id": batch_id,
                "branch_id": rec.branch_id,
                "ingredient_id": ing_id,
                "ingredient_name": ing_name,
                "batch_code": batch_code,
                "quantity_remaining": qty,
                "received_date": rec.date,
                "expiry_date": expiry_date
            })

            cur.execute("""
                INSERT INTO inventory_batches (id, branch_id, ingredient_id, batch_code, quantity_remaining, received_date, expiry_date, batch_hash, solana_tx, solana_status, verified_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (batch_id, rec.branch_id, ing_id, batch_code, qty, rec.date, expiry_date, b_proof["record_hash"], b_proof["tx_signature"], "CONFIRMED", b_proof["notarized_at"]))

            recorded_items.append({
                "ingredient_id": ing_id,
                "ingredient_name": ing_name,
                "quantity": qty,
                "unit": unit,
                "unit_price": unit_price
            })
            saved_count += 1

        conn.commit()
        conn.close()

        return {
            "status": "success",
            "message": f"Đã xác nhận nhập kho thành công {saved_count} nguyên liệu (Tổng tiền: {total_spent:,.0f} đ) & Ký chứng thực Solana Devnet!",
            "saved_count": saved_count,
            "total_spent": total_spent,
            "solana_proof": po_proof,
            "ai_assessment": ai_eval
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/purchases/history")
def get_purchases_history(branch_id: str = "BRANCH_01", limit: int = 100):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, date, branch_id, ingredient_id, ingredient_name, quantity_purchased,
               unit, unit_price, total_cost, batch_code, expiry_date, record_hash,
               solana_tx, solana_status, verified_at,
               variance_pct, variance_reason, ai_verdict, ai_notes, ai_adjustment, created_at
        FROM purchase_history
        WHERE branch_id = ?
        ORDER BY date DESC, id DESC
        LIMIT ?
    """, (branch_id, limit))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

# ==========================================
# 6. API ĐƠN ĐẶT TRƯỚC ĐA MÓN (MULTI-ITEM PREORDERS)
# ==========================================

@app.get("/api/preorders")
def get_preorders(branch_id: Optional[str] = "BRANCH_01"):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM preorders WHERE branch_id = ? ORDER BY date ASC, id DESC", (branch_id,))
    raw_rows = cur.fetchall()
    
    results = []
    for r in raw_rows:
        item_dict = dict(r)
        if item_dict.get("items_json"):
            try:
                item_dict["items"] = json.loads(item_dict["items_json"])
            except Exception:
                item_dict["items"] = [{"dish_id": item_dict.get("dish_id"), "dish_name": item_dict.get("dish_name"), "quantity": item_dict.get("quantity")}]
        else:
            item_dict["items"] = [{"dish_id": item_dict.get("dish_id"), "dish_name": item_dict.get("dish_name"), "quantity": item_dict.get("quantity")}]
        
        results.append(item_dict)
        
    conn.close()
    return results

@app.post("/api/preorders")
def create_preorder_multi(order: PreorderCreateMulti):
    conn = get_db()
    cur = conn.cursor()
    items_json_str = json.dumps([it.model_dump() for it in order.items], ensure_ascii=False)
    total_qty = sum(it.quantity for it in order.items)
    main_dish_name = ", ".join([f"{it.dish_name} (x{it.quantity})" for it in order.items])

    cur.execute("""
        INSERT INTO preorders (branch_id, date, customer_name, dish_id, dish_name, quantity, note, items_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (order.branch_id, order.date, order.customer_name, order.items[0].dish_id if order.items else "D01", main_dish_name, total_qty, order.note, items_json_str))
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"status": "success", "id": new_id, "message": "Đã ghi nhận đơn đặt trước thành công!"}

@app.delete("/api/preorders/{order_id}")
def delete_preorder(order_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM preorders WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Đã xóa đơn đặt trước"}

# ==========================================
# 7. API DỰ BÁO, GỢI Ý MUA HÀNG & DASHBOARD
# ==========================================

@app.get("/api/forecast")
def get_forecast(n_days: int = Query(7, ge=1, le=14), branch_id: Optional[str] = "BRANCH_01"):
    try:
        return get_forecast_for_next_days(n_days=n_days, branch_id=branch_id, db_path=DB_PATH)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/purchase-recommendations")
def get_recommendations(branch_id: str = "BRANCH_01", target_date: Optional[str] = None):
    try:
        return get_purchase_recommendations(target_date=target_date, branch_id=branch_id, db_path=DB_PATH)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/inventory")
def get_inventory(branch_id: str = "BRANCH_01"):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT inv.branch_id, inv.ingredient_id, i.name, i.unit, i.cost_per_unit,
               i.shelf_life_days, i.min_stock, i.category_tag, inv.quantity as current_stock,
               ROUND(inv.quantity * i.cost_per_unit, 0) as total_value
        FROM inventory inv
        JOIN ingredients i ON inv.ingredient_id = i.id
        WHERE inv.branch_id = ?
        ORDER BY inv.ingredient_id ASC
    """, (branch_id,))
    inventory_items = [dict(r) for r in cur.fetchall()]

    cur.execute("""
        SELECT b.id, b.branch_id, b.ingredient_id, i.name as ingredient_name,
               b.batch_code, b.quantity_remaining, i.unit, b.received_date, b.expiry_date,
               b.batch_hash, b.solana_tx, b.solana_status, b.verified_at
        FROM inventory_batches b
        JOIN ingredients i ON b.ingredient_id = i.id
        WHERE b.branch_id = ?
        ORDER BY b.expiry_date ASC
    """, (branch_id,))
    batches = [dict(r) for r in cur.fetchall()]

    conn.close()
    return {
        "branch_id": branch_id,
        "items": inventory_items,
        "batches": batches
    }

@app.post("/api/inventory/update")
def update_inventory(item: InventoryUpdate):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO inventory (branch_id, ingredient_id, quantity)
        VALUES (?, ?, ?)
        ON CONFLICT(branch_id, ingredient_id) DO UPDATE SET quantity=excluded.quantity
    """, (item.branch_id, item.ingredient_id, item.quantity))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Đã cập nhật tồn kho"}

# ==========================================
# 8. API SOLANA DEVNET AUDIT & NOTARIZATION
# ==========================================

@app.get("/api/solana/status")
def get_solana_status():
    """Lấy trạng thái kết nối Solana Devnet, Authority Public Key & Số lượng kiểm toán"""
    return get_solana_network_status()

@app.post("/api/solana/verify")
def verify_solana_proof(req: SolanaVerifyRequest):
    """Xác thực đối chiếu SHA-256 Hash vs Chữ ký giao dịch Solana Devnet"""
    return verify_onchain_record(req.expected_hash, req.tx_signature)

@app.post("/api/solana/notarize-batch/{batch_id}")
def notarize_batch_endpoint(batch_id: int):
    """Ký chứng thực thủ công một Lô Hàng lên Solana Devnet"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.id, b.branch_id, b.ingredient_id, i.name as ingredient_name,
               b.batch_code, b.quantity_remaining, b.received_date, b.expiry_date
        FROM inventory_batches b
        JOIN ingredients i ON b.ingredient_id = i.id
        WHERE b.id = ?
    """, (batch_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy lô hàng!")
    
    batch_dict = dict(row)
    res = notarize_batch_onchain(batch_dict)
    return res

@app.post("/api/solana/notarize-po")
def notarize_po_endpoint(req: SolanaNotarizePORequest):
    """Ký chứng thực Đơn Mua Hàng lên Solana Devnet"""
    res = notarize_purchase_order_onchain(req.model_dump())
    return res

@app.get("/api/dashboard/summary")
def get_dashboard_summary(branch_id: str = "BRANCH_01"):
    try:
        rec_data = get_purchase_recommendations(branch_id=branch_id, db_path=DB_PATH)
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT date, SUM(quantity) as total_sold, SUM(revenue) as daily_revenue
            FROM sales
            WHERE branch_id = ?
            GROUP BY date
            ORDER BY date DESC
            LIMIT 7
        """, (branch_id,))
        recent_sales = [dict(r) for r in cur.fetchall()]
        recent_sales.reverse()
        conn.close()

        dish_demands = sorted(rec_data.get("dish_demands", []), key=lambda x: x["expected_demand"], reverse=True)
        top_dishes = dish_demands[:5]
        critical_ingredients = [r for r in rec_data.get("recommendations", []) if r["status"] in ["CRITICAL", "WARNING"]][:6]

        return {
            "branch": rec_data.get("branch"),
            "tomorrow_date": rec_data.get("target_date"),
            "kpis": {
                "expected_sales_revenue": rec_data.get("summary", {}).get("total_estimated_sales_revenue", 0),
                "total_dishes_demand": sum(d["expected_demand"] for d in rec_data.get("dish_demands", [])),
                "purchase_budget_needed": rec_data.get("summary", {}).get("total_estimated_purchase_cost", 0),
                "items_to_buy_count": rec_data.get("summary", {}).get("total_items_to_buy", 0),
                "critical_shortage_count": rec_data.get("summary", {}).get("critical_shortage_items", 0),
                "confirmed_preorders_count": sum(d["confirmed_preorders"] for d in rec_data.get("dish_demands", []))
            },
            "top_dishes_tomorrow": top_dishes,
            "urgent_purchases": critical_ingredients,
            "recent_revenue_trend": recent_sales
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/model/retrain")
def trigger_retrain():
    try:
        res_df = train_and_evaluate_all()
        return {
            "status": "success",
            "message": "Đã huấn luyện lại thành công các mô hình XGBoost!",
            "models_count": len(res_df),
            "average_wape": round(res_df["xgb_wape"].mean(), 2),
            "average_mae": round(res_df["xgb_mae"].mean(), 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 8. API RESET / CLEAR / DEMO TOGGLE
# ==========================================

@app.post("/api/data/reset-demo")
def reset_to_demo_data():
    from scripts.generate_data import generate_big_dataset
    generate_big_dataset()
    train_and_evaluate_all()
    return {"status": "success", "message": "Đã nạp lại bộ dữ liệu mẫu F&B (3 chi nhánh, 22 món, 35 nguyên liệu, 2 năm lịch sử) thành công!"}

@app.post("/api/data/clear-clean")
def clear_to_clean_slate():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM sales")
    cur.execute("DELETE FROM preorders")
    cur.execute("DELETE FROM inventory")
    cur.execute("DELETE FROM inventory_batches")
    cur.execute("DELETE FROM purchase_history")
    cur.execute("DELETE FROM recipes")
    cur.execute("DELETE FROM dishes")
    cur.execute("DELETE FROM ingredients")
    cur.execute("DELETE FROM branches")
    # Tạo 1 chi nhánh trống khởi đầu
    cur.execute("INSERT INTO branches (id, name, address, type) VALUES ('BRANCH_01', 'Quán Của Tôi (Chưa có dữ liệu)', 'Việt Nam', 'Mô Hình F&B Mới')")
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Đã làm trống 100% dữ liệu! Hệ thống sẵn sàng để bạn tự tạo chi nhánh, món ăn, nguyên liệu và tải file doanh số lên."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
