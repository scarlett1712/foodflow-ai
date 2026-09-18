"""
backend/app/services/ai_variance_evaluator.py
Service phân tích chênh lệch đi chợ thực tế vs AI Baseline, thẩm định tính hợp lý của lý do giải trình và đề xuất chiến lược thích ứng mô hình dự báo.
"""

import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime

def evaluate_purchase_variance(
    items: List[Dict[str, Any]],
    branch_id: str = "BRANCH_01",
    reason: str = "",
    target_date: Optional[str] = None,
    db_path: str = "foodflow.db"
) -> Dict[str, Any]:
    """
    Phân tích so sánh đơn mua hàng thực tế với định mức AI & Giá vốn chuẩn:
    - Phát hiện chênh lệch số lượng (Quantity Variance) & đơn giá (Price Variance).
    - Thẩm định ngữ nghĩa của lý do giải trình (AI Plausibility Assessment).
    - Đưa ra chiến lược tự động điều chỉnh mô hình ML / Hệ thống tồn kho.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Lấy thông tin giá vốn chuẩn của từng nguyên liệu
    cur.execute("SELECT id, name, unit, cost_per_unit, min_stock, category_tag FROM ingredients")
    ing_map = {row["id"]: dict(row) for row in cur.fetchall()}

    # 2. Lấy tồn kho hiện tại
    cur.execute("SELECT ingredient_id, quantity FROM inventory WHERE branch_id = ?", (branch_id,))
    stock_map = {row["ingredient_id"]: row["quantity"] for row in cur.fetchall()}

    conn.close()

    total_actual_cost = 0.0
    total_baseline_cost = 0.0
    item_evaluations = []
    has_quantity_spike = False
    has_price_spike = False
    max_price_spike_pct = 0.0

    for item in items:
        ing_id = item.get("ingredient_id")
        actual_qty = float(item.get("quantity", 0))
        if actual_qty <= 0:
            continue

        actual_unit_price = float(item.get("cost_per_unit", 0))
        ing_info = ing_map.get(ing_id, {})
        std_price = float(ing_info.get("cost_per_unit", actual_unit_price or 1.0))
        ing_name = item.get("ingredient_name") or ing_info.get("name", ing_id)
        unit = item.get("unit") or ing_info.get("unit", "kg")

        actual_item_cost = actual_qty * actual_unit_price
        baseline_item_cost = actual_qty * std_price  # Chuẩn giá
        total_actual_cost += actual_item_cost
        total_baseline_cost += baseline_item_cost

        # Tính độ lệch đơn giá
        price_diff = actual_unit_price - std_price
        price_var_pct = round((price_diff / std_price * 100), 1) if std_price > 0 else 0.0
        if price_var_pct > max_price_spike_pct:
            max_price_spike_pct = price_var_pct

        # Cảnh báo đơn giá tăng > 10%
        is_price_flagged = price_var_pct >= 10.0
        if is_price_flagged:
            has_price_spike = True

        # Đánh giá số lượng
        min_stk = float(ing_info.get("min_stock", 5.0))
        is_qty_flagged = actual_qty > (min_stk * 2.5)  # Mua vượt 2.5 lần định mức tối thiểu
        if is_qty_flagged:
            has_quantity_spike = True

        item_evaluations.append({
            "ingredient_id": ing_id,
            "ingredient_name": ing_name,
            "unit": unit,
            "actual_quantity": actual_qty,
            "actual_unit_price": actual_unit_price,
            "standard_unit_price": std_price,
            "price_variance_pct": price_var_pct,
            "price_diff_vnd": price_diff * actual_qty,
            "is_price_flagged": is_price_flagged,
            "is_qty_flagged": is_qty_flagged,
            "actual_cost": actual_item_cost,
        })

    # Tổng chênh lệch chi phí
    cost_variance_diff = total_actual_cost - total_baseline_cost
    cost_variance_pct = round((cost_variance_diff / total_baseline_cost * 100), 1) if total_baseline_cost > 0 else 0.0

    # Phân loại và đánh giá tính hợp lý của lý do
    clean_reason = (reason or "").strip().lower()
    flagged_count = sum(1 for x in item_evaluations if x["is_price_flagged"] or x["is_qty_flagged"])
    is_variance_detected = flagged_count > 0 or cost_variance_pct >= 10.0

    # Phân tích Semantic AI cho lý do
    if not is_variance_detected:
        verdict = "COMPLIANT"
        plausibility_level = "CAO (100%)"
        plausibility_badge = "success"
        category = "ALIGNED_WITH_PLAN"
        category_text = "Hoàn Toàn Khớp Định Mức"
        ai_notes = "Chi phí và số lượng đi chợ nằm trong giới hạn tối ưu của hệ thống."
        adjustment_strategy = "Giữ nguyên trọng số mô hình dự báo XGBoost hiện tại."
        audit_status = "AI_VERIFIED_OPTIMAL"
    elif len(clean_reason) < 4:
        verdict = "ANOMALY"
        plausibility_level = "THẤP (20%)"
        plausibility_badge = "danger"
        category = "MISSING_EXPLANATION"
        category_text = "Chưa Giải Trình / Lý Do Không Rõ Ràng"
        ai_notes = f"Phát hiện {flagged_count} mặt hàng chênh lệch (+{cost_variance_pct}% ngân sách) nhưng chưa có lý do cụ thể."
        adjustment_strategy = "Gắn cờ kiểm toán On-Chain (Audit Flag). Yêu cầu quản lý chi nhánh rà soát đối chiếu hóa đơn gốc."
        audit_status = "FLAGGED_UNEXPLAINED_VARIANCE"
    else:
        # Nhận diện các pattern lý do
        has_market_kw = any(w in clean_reason for w in ["bão", "mưa", "thị trường", "tăng giá", "khan hiếm", "hàng hiếm", "xăng", "vận chuyển", "nhà cung cấp", "nông sản", "đắt", "leo thang"])
        has_event_kw = any(w in clean_reason for w in ["tiệc", "đoàn", "khách", "sự kiện", "đám cưới", "sinh nhật", "cuối tuần", "tour", "hội nghị", "đột xuất", "đặt trước", "đông"])
        has_spoilage_kw = any(w in clean_reason for w in ["hỏng", "hư", "hết hạn", "mất", "bảo quản", "ẩm", "mốc", "đổi trả", "hao hụt", "rách", "vỡ"])
        has_bulk_kw = any(w in clean_reason for w in ["giá sỉ", "chiết khấu", "gom hàng", "khuyến mãi", "combo", "rẻ hơn", "tích trữ", "mua nhiều"])

        if has_market_kw:
            verdict = "PLAUSIBLE"
            plausibility_level = "HỢP LÝ CAO (92%)"
            plausibility_badge = "success"
            category = "MARKET_PRICE_SHOCK"
            category_text = "Biến Động Giá Thị Trường / Nhà Cung Cấp"
            ai_notes = f"Lý do phù hợp với xu hướng biến động giá đơn vị thực tế (+{max_price_spike_pct}% đơn giá)."
            adjustment_strategy = "Tự động cập nhật bảng Giá Vốn Chuẩn (Standard Cost) mới và điều chỉnh hạn mức chi phí dự toán tuần tới."
            audit_status = "VERIFIED_MARKET_SHOCK"
        elif has_event_kw:
            verdict = "PLAUSIBLE"
            plausibility_level = "HỢP LÝ CAO (95%)"
            plausibility_badge = "success"
            category = "EVENT_SPIKE"
            category_text = "Phục Vụ Tiệc / Sự Kiện Lớn Đột Xuất"
            ai_notes = "Lý do phục vụ sự kiện đột xuất giải thích việc mua bổ sung khối lượng lớn."
            adjustment_strategy = "Cập nhật số dư kho FEFO thực tế và gắn nhãn Outlier Event để mô hình Machine Learning không bị sai lệch dự báo tuần kế tiếp."
            audit_status = "VERIFIED_EVENT_BUFFER"
        elif has_spoilage_kw:
            verdict = "MONITOR"
            plausibility_level = "CẦN THEO DÕI (75%)"
            plausibility_badge = "warning"
            category = "SPOILAGE_REPLACEMENT"
            category_text = "Bù Đắp Hàng Hư Hỏng / Hao Hụt Kho"
            ai_notes = "Nhập bù cho số lượng bị hỏng/hao hụt. Cần rà soát điều kiện bảo quản nhiệt độ và quy trình xuất nhập FEFO."
            adjustment_strategy = "Bù đắp lượng thiếu hụt trong kho và kích hoạt thông báo kiểm tra tỷ lệ hao hụt (Waste Ratio Tracking)."
            audit_status = "MONITOR_SPOILAGE_LOSS"
        elif has_bulk_kw:
            verdict = "PLAUSIBLE"
            plausibility_level = "HỢP LÝ (88%)"
            plausibility_badge = "success"
            category = "BULK_PURCHASE_DISCOUNT"
            category_text = "Mua Tích Trữ Nhận Chiết Khấu Sỉ"
            ai_notes = "Tận dụng chiết khấu mua sỉ số lượng lớn giúp tối ưu chi phí đơn vị dài hạn."
            adjustment_strategy = "Điều chỉnh mức Safety Stock tạm thời và ưu tiên xuất kho sớm trước khi hết hạn FEFO."
            audit_status = "VERIFIED_BULK_STOCK"
        else:
            verdict = "MONITOR"
            plausibility_level = "TRUNG BÌNH (65%)"
            plausibility_badge = "warning"
            category = "OPERATIONAL_REASON"
            category_text = "Lý Do Vận Hành Khác"
            ai_notes = f"Đã ghi nhận lý do: '{reason}'. Hệ thống sẽ theo dõi chu kỳ xuất dùng thực tế."
            adjustment_strategy = "Ghi nhận giải trình vào sổ kiểm toán Solana và theo dõi tỷ lệ tiêu thụ thực tế."
            audit_status = "VERIFIED_WITH_REASON"

    return {
        "is_variance_detected": is_variance_detected,
        "flagged_items_count": flagged_count,
        "total_actual_cost": total_actual_cost,
        "total_baseline_cost": total_baseline_cost,
        "cost_variance_pct": cost_variance_pct,
        "cost_variance_diff": cost_variance_diff,
        "max_price_spike_pct": max_price_spike_pct,
        "verdict": verdict,
        "plausibility_level": plausibility_level,
        "plausibility_badge": plausibility_badge,
        "category": category,
        "category_text": category_text,
        "ai_notes": ai_notes,
        "adjustment_strategy": adjustment_strategy,
        "audit_status": audit_status,
        "item_evaluations": item_evaluations,
        "evaluated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
