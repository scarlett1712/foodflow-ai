"""
backend/app/services/recommendation_service.py
Dịch vụ Quy Đổi Công Thức & Gợi Ý Mua Hàng (Recipe Conversion & Purchase Orders):
- Quy đổi Nhu cầu món (Dự báo + Đơn đặt trước) sang Nguyên liệu cần theo Bảng Recipe
- Đối chiếu Tồn kho thực tế
- Tính toán Lượng thiếu hụt & Đề xuất số lượng cần mua
- Phân loại trạng thái: Thiếu khẩn cấp, Cần mua, Đủ, Dư thừa
- Ước tính chi phí nhập hàng (Estimated Cost)
"""

import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

from ..forecasting.predictor import get_forecast_for_next_days

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "foodflow.db")

def get_purchase_recommendations(target_date=None, branch_id="BRANCH_01", db_path=DB_PATH):
    """
    Tính toán gợi ý mua hàng cho 1 ngày cụ thể (mặc định ngày mai) tại 1 chi nhánh.
    """
    conn = sqlite3.connect(db_path)

    # 1. Lấy danh sách nguyên liệu
    df_ingredients = pd.read_sql_query("""
        SELECT id, name, unit, cost_per_unit, shelf_life_days, min_stock
        FROM ingredients
    """, conn)

    # 2. Lấy công thức món
    df_recipes = pd.read_sql_query("""
        SELECT dish_id, ingredient_id, quantity
        FROM recipes
    """, conn)

    # 3. Lấy tồn kho hiện tại của chi nhánh
    df_inventory = pd.read_sql_query("""
        SELECT ingredient_id, quantity as current_stock
        FROM inventory
        WHERE branch_id = ?
    """, conn, params=(branch_id,))

    # 4. Lấy thông tin chi nhánh
    branch_info = pd.read_sql_query("SELECT id, name, address, type FROM branches WHERE id = ?", conn, params=(branch_id,)).to_dict(orient="records")
    branch_meta = branch_info[0] if branch_info else {"id": branch_id, "name": branch_id}

    conn.close()

    # 5. Lấy dự báo nhu cầu từ Predictor
    forecast_data = get_forecast_for_next_days(n_days=7, branch_id=branch_id, db_path=db_path)
    
    # Tìm branch forecast
    b_forecast = None
    for b in forecast_data.get("branches", []):
        if b["branch_id"] == branch_id:
            b_forecast = b
            break
    
    if not b_forecast:
        b_forecast = {"branch_id": branch_id, "dishes": []}

    # Xác định ngày mục tiêu (mặc định ngày đầu tiên trong dự báo hoặc ngày mai)
    if not target_date:
        if b_forecast.get("dishes") and len(b_forecast["dishes"]) > 0 and b_forecast["dishes"][0].get("daily_forecasts"):
            target_date = b_forecast["dishes"][0]["daily_forecasts"][0]["date"]
        else:
            target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    # Tổng hợp nhu cầu món ăn cho ngày target_date
    dish_demands = {}
    dish_breakdown = []
    total_estimated_revenue = 0

    for dish in b_forecast.get("dishes", []):
        d_id = dish["dish_id"]
        d_name = dish["dish_name"]
        d_price = dish["price"]
        
        # Tìm ngày target
        target_day_data = None
        for day in dish["daily_forecasts"]:
            if day["date"] == target_date:
                target_day_data = day
                break
        
        if target_day_data:
            expected_qty = target_day_data["expected_demand"]
            dish_demands[d_id] = expected_qty
            total_estimated_revenue += target_day_data["estimated_revenue"]

            dish_breakdown.append({
                "dish_id": d_id,
                "dish_name": d_name,
                "category": dish["category"],
                "price": d_price,
                "xgb_forecast": target_day_data["xgb_forecast"],
                "confirmed_preorders": target_day_data["confirmed_preorders"],
                "expected_demand": expected_qty,
                "estimated_revenue": target_day_data["estimated_revenue"]
            })

    # 6. Quy đổi sang nguyên liệu cần thiết (Recipe Conversion)
    ingredient_requirements = {}
    for _, recipe in df_recipes.iterrows():
        d_id = recipe["dish_id"]
        ing_id = recipe["ingredient_id"]
        qty_per_portion = recipe["quantity"]

        dish_demand = dish_demands.get(d_id, 0)
        needed = dish_demand * qty_per_portion

        ingredient_requirements[ing_id] = ingredient_requirements.get(ing_id, 0.0) + needed

    # 7. Đối chiếu tồn kho & Sinh gợi ý mua hàng
    recommendations = []
    total_purchase_cost = 0
    total_shortage_items = 0
    total_critical_items = 0

    for _, ing in df_ingredients.iterrows():
        ing_id = ing["id"]
        ing_name = ing["name"]
        unit = ing["unit"]
        cost = ing["cost_per_unit"]
        min_stk = ing["min_stock"] or 0.0
        shelf_life = ing["shelf_life_days"]

        # Lượng cần
        required_qty = round(ingredient_requirements.get(ing_id, 0.0), 2)

        # Tồn kho hiện tại
        stock_match = df_inventory[df_inventory["ingredient_id"] == ing_id]
        current_stock = float(stock_match["current_stock"].iloc[0]) if len(stock_match) > 0 else 0.0
        current_stock = round(current_stock, 2)

        # Thiếu hụt & Gợi ý mua
        shortage = max(round(required_qty - current_stock, 2), 0.0)
        
        # Nếu thiếu hoặc sau khi dùng xong tồn kho tụt dưới min_stock -> Đề xuất mua đủ dùng + đệm min_stock
        if required_qty > current_stock:
            recommended_purchase = round(required_qty - current_stock + (min_stk * 0.2), 1)
        elif (current_stock - required_qty) < min_stk:
            recommended_purchase = round(min_stk - (current_stock - required_qty), 1)
        else:
            recommended_purchase = 0.0

        # Phân loại trạng thái
        if required_qty > 0 and current_stock < (required_qty * 0.35):
            status = "CRITICAL"
            status_text = "Thiếu khẩn cấp"
            status_color = "red"
            total_critical_items += 1
            total_shortage_items += 1
        elif shortage > 0 or recommended_purchase > 0:
            status = "WARNING"
            status_text = "Cần mua bổ sung"
            status_color = "amber"
            total_shortage_items += 1
        elif current_stock > (required_qty * 3.5) and required_qty > 0:
            status = "EXCESS"
            status_text = "Tồn dư nhiều"
            status_color = "blue"
        else:
            status = "SUFFICIENT"
            status_text = "Đủ nguyên liệu"
            status_color = "green"

        item_cost = int(round(recommended_purchase * cost))
        total_purchase_cost += item_cost

        # Tỷ lệ đáp ứng kho hiện tại
        stock_coverage_pct = round((current_stock / required_qty * 100), 1) if required_qty > 0 else 100.0

        recommendations.append({
            "ingredient_id": ing_id,
            "ingredient_name": ing_name,
            "unit": unit,
            "cost_per_unit": cost,
            "shelf_life_days": shelf_life,
            "min_stock": min_stk,
            "current_stock": current_stock,
            "required_quantity": required_qty,
            "shortage": shortage,
            "recommended_purchase": recommended_purchase,
            "estimated_cost": item_cost,
            "status": status,
            "status_text": status_text,
            "status_color": status_color,
            "stock_coverage_pct": stock_coverage_pct
        })

    # Sắp xếp danh sách gợi ý: CRITICAL lên đầu, sau đó WARNING, SUFFICIENT, EXCESS
    status_order = {"CRITICAL": 0, "WARNING": 1, "SUFFICIENT": 2, "EXCESS": 3}
    recommendations.sort(key=lambda x: (status_order[x["status"]], -x["recommended_purchase"]))

    return {
        "target_date": target_date,
        "branch": branch_meta,
        "summary": {
            "total_items_to_buy": total_shortage_items,
            "critical_shortage_items": total_critical_items,
            "total_estimated_purchase_cost": total_purchase_cost,
            "total_estimated_sales_revenue": total_estimated_revenue,
            "profit_margin_estimated": round(((total_estimated_revenue - total_purchase_cost) / total_estimated_revenue * 100), 1) if total_estimated_revenue > 0 else 0
        },
        "recommendations": recommendations,
        "dish_demands": dish_breakdown
    }

if __name__ == "__main__":
    res = get_purchase_recommendations(branch_id="BRANCH_01")
    print(f"GỢI Ý MUA HÀNG CHO NGÀY: {res['target_date']} - {res['branch']['name']}")
    print(f"-> Tổng số nguyên liệu cần mua: {res['summary']['total_items_to_buy']}")
    print(f"-> Số nguyên liệu thiếu khẩn cấp: {res['summary']['critical_shortage_items']}")
    print(f"-> Ngân sách đi chợ dự kiến: {res['summary']['total_estimated_purchase_cost']:,} VNĐ")
    print(f"-> Doanh thu dự kiến: {res['summary']['total_estimated_sales_revenue']:,} VNĐ")
    print("-" * 80)
    print(f"{'MÃ NL':<7} | {'TÊN NGUYÊN LIỆU':<25} | {'CẦN DÙNG':<10} | {'TỒN KHO':<10} | {'CẦN MUA':<10} | {'TRẠNG THÁI'}")
    print("-" * 80)
    for r in res["recommendations"][:12]:
        print(f"{r['ingredient_id']:<7} | {r['ingredient_name']:<25} | {r['required_quantity']} {r['unit']:<4} | {r['current_stock']} {r['unit']:<4} | {r['recommended_purchase']} {r['unit']:<4} | {r['status_text']}")
