"""
backend/app/forecasting/predictor.py
Dịch vụ dự báo nhu cầu tương lai (Forecast Service) — Global Model v2:
- Dự báo 1 đến 7 ngày tiếp theo cho từng món ăn tại từng chi nhánh (hoặc tổng hợp)
- So sánh kết quả giữa Baseline và XGBoost Global Model
- Tích hợp đơn đặt trước đa món (Multi-item Pre-orders)
- Tết Nguyên Đán features
"""

import os
import sys
import sqlite3
import json
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from .features import build_features_for_dish, prepare_categorical_dtypes, FEATURE_COLUMNS
from .vn_calendar import VIETNAM_HOLIDAYS, get_tet_date, TET_FEATURE_NAMES

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "foodflow.db")
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_models", "global_model.joblib")
MAPPING_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_models", "category_mapping.joblib")

def get_forecast_for_next_days(n_days=7, branch_id=None, db_path=DB_PATH, model_path=MODEL_PATH):
    """
    Sinh dự báo cho n_days ngày tiếp theo.
    Signature + format output giữ nguyên 100% so với bản cũ.
    """
    conn = sqlite3.connect(db_path)
    
    # Query branches
    if branch_id and branch_id != "ALL":
        df_branches = pd.read_sql_query("SELECT id, name, address, type FROM branches WHERE id = ?", conn, params=(branch_id,))
    else:
        df_branches = pd.read_sql_query("SELECT id, name, address, type FROM branches", conn)

    # Query sales (thêm event_flag)
    df_sales = pd.read_sql_query("""
        SELECT s.date, s.branch_id, s.branch_name, s.dish_id, s.dish_name, s.category, s.quantity, s.revenue,
               s.event_flag,
               c.is_weekend, c.is_holiday, c.day_of_week
        FROM sales s
        JOIN calendar c ON s.date = c.date
        ORDER BY s.date ASC, s.branch_id ASC, s.dish_id ASC
    """, conn)

    # Query dishes
    df_dishes = pd.read_sql_query("SELECT id, name, category, price FROM dishes", conn)
    
    # Query preorders (Hỗ trợ cả multi-item JSON và legacy single-item)
    cur = conn.cursor()
    cur.execute("SELECT branch_id, date, dish_id, quantity, items_json FROM preorders")
    preorders_rows = cur.fetchall()
    conn.close()

    # Pre-aggregate preorders by (branch_id, date, dish_id)
    preorders_dict = {}
    for b_id, p_date, d_id, qty, items_json in preorders_rows:
        if items_json:
            try:
                items_list = json.loads(items_json)
                for it in items_list:
                    key = (b_id, p_date, it.get("dish_id"))
                    preorders_dict[key] = preorders_dict.get(key, 0) + int(it.get("quantity", 0))
            except Exception:
                pass
        elif d_id:
            key = (b_id, p_date, d_id)
            preorders_dict[key] = preorders_dict.get(key, 0) + int(qty or 0)

    # Load Global Model + Category Mapping
    model = None
    category_mapping = None
    if os.path.exists(model_path):
        try:
            model = joblib.load(model_path)
        except Exception:
            pass
    
    mapping_path = model_path.replace("global_model.joblib", "category_mapping.joblib")
    if os.path.exists(mapping_path):
        try:
            category_mapping = joblib.load(mapping_path)
        except Exception:
            pass

    last_date_str = df_sales["date"].max() if len(df_sales) > 0 else datetime.now().strftime("%Y-%m-%d")
    try:
        last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
    except Exception:
        last_date = datetime.now()

    branch_results = []

    for _, b_row in df_branches.iterrows():
        b_id = b_row["id"]
        b_name = b_row["name"]

        dish_forecasts = []

        for _, dish in df_dishes.iterrows():
            d_id = dish["id"]
            d_name = dish["name"]
            d_cat = dish["category"]
            d_price = dish["price"]

            df_dish = df_sales[(df_sales["branch_id"] == b_id) & (df_sales["dish_id"] == d_id)].copy()
            sim_df = df_dish.copy()

            daily_list = []
            for step in range(1, n_days + 1):
                target_date = last_date + timedelta(days=step)
                target_date_str = target_date.strftime("%Y-%m-%d")
                month_day = target_date.strftime("%m-%d")
                dow = target_date.weekday()
                is_wknd = 1 if dow in [5, 6] else 0
                is_hol = 1 if month_day in VIETNAM_HOLIDAYS else 0
                hol_name = VIETNAM_HOLIDAYS.get(month_day, "")

                if len(sim_df) >= 7:
                    # Features — lag/rolling
                    lag_1 = sim_df["quantity"].iloc[-1]
                    lag_7 = sim_df["quantity"].iloc[-7] if len(sim_df) >= 7 else lag_1
                    lag_14 = sim_df["quantity"].iloc[-14] if len(sim_df) >= 14 else lag_7
                    lag_28 = sim_df["quantity"].iloc[-28] if len(sim_df) >= 28 else lag_14

                    rolling_7 = sim_df["quantity"].tail(7).mean()
                    rolling_14 = sim_df["quantity"].tail(14).mean()
                    rolling_28 = sim_df["quantity"].tail(28).mean()
                    rolling_std_7 = sim_df["quantity"].tail(7).std() or 0.0

                    # Tết features
                    tet_features = _compute_tet_features_for_date(target_date)

                    feat_dict = {
                        "branch_id": b_id,
                        "dish_id": d_id,
                        "day_of_week": dow,
                        "day_of_month": target_date.day,
                        "month": target_date.month,
                        "is_weekend": is_wknd,
                        "is_holiday": is_hol,
                        "lag_1": lag_1,
                        "lag_7": lag_7,
                        "lag_14": lag_14,
                        "lag_28": lag_28,
                        "rolling_mean_7": rolling_7,
                        "rolling_mean_14": rolling_14,
                        "rolling_mean_28": rolling_28,
                        "rolling_std_7": rolling_std_7,
                        "event_flag": "none",  # Tương lai: không biết trước event
                    }
                    feat_dict.update(tet_features)

                    feat_vec = pd.DataFrame([feat_dict])[FEATURE_COLUMNS]

                    # Áp dụng categorical dtypes khớp với lúc train
                    if category_mapping:
                        feat_vec["branch_id"] = pd.Categorical(feat_vec["branch_id"], categories=category_mapping["branch_id"])
                        feat_vec["dish_id"] = pd.Categorical(feat_vec["dish_id"], categories=category_mapping["dish_id"])
                        feat_vec["event_flag"] = pd.Categorical(feat_vec["event_flag"], categories=category_mapping["event_flag"])

                    # Baseline prediction
                    same_dow = sim_df[pd.to_datetime(sim_df["date"]).dt.dayofweek == dow]["quantity"].tail(4)
                    base_val = int(round(same_dow.mean() if len(same_dow) > 0 else rolling_7))

                    # XGBoost Global Model prediction
                    if model is not None:
                        pred_val = model.predict(feat_vec)[0]
                        xgb_val = int(round(max(pred_val, 0)))
                    else:
                        xgb_val = base_val
                else:
                    # Fallback when insufficient data
                    base_val = 30
                    xgb_val = 30

                # Preorders
                pre_qty = preorders_dict.get((b_id, target_date_str, d_id), 0)
                expected_demand = xgb_val + pre_qty

                daily_list.append({
                    "date": target_date_str,
                    "day_name": ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"][dow],
                    "is_weekend": bool(is_wknd),
                    "is_holiday": bool(is_hol),
                    "holiday_name": hol_name,
                    "baseline_forecast": base_val,
                    "xgb_forecast": xgb_val,
                    "confirmed_preorders": pre_qty,
                    "expected_demand": expected_demand,
                    "estimated_revenue": expected_demand * d_price
                })

                if len(sim_df) > 0:
                    sim_row = pd.DataFrame([{
                        "date": target_date_str,
                        "branch_id": b_id,
                        "branch_name": b_name,
                        "dish_id": d_id,
                        "dish_name": d_name,
                        "category": d_cat,
                        "quantity": xgb_val,
                        "revenue": xgb_val * d_price,
                        "event_flag": None,
                        "is_weekend": is_wknd,
                        "is_holiday": is_hol,
                        "day_of_week": dow
                    }])
                    sim_df = pd.concat([sim_df, sim_row], ignore_index=True)

            dish_forecasts.append({
                "dish_id": d_id,
                "dish_name": d_name,
                "category": d_cat,
                "price": d_price,
                "daily_forecasts": daily_list
            })

        branch_results.append({
            "branch_id": b_id,
            "branch_name": b_name,
            "branch_type": b_row.get("type", ""),
            "dishes": dish_forecasts
        })

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "forecast_horizon_days": n_days,
        "branches": branch_results
    }


def _compute_tet_features_for_date(target_date):
    """Tính 6 cột Tết features cho 1 ngày cụ thể (dùng khi predict tương lai)."""
    if isinstance(target_date, datetime):
        target_ts = pd.Timestamp(target_date)
    else:
        target_ts = pd.Timestamp(target_date)

    year = target_ts.year
    best_delta = 999
    for y in [year - 1, year, year + 1]:
        try:
            tet = get_tet_date(y)
            d = (target_ts - tet).days
            if abs(d) < abs(best_delta):
                best_delta = d
        except (ValueError, KeyError):
            continue

    return {
        "days_to_tet": best_delta,
        "days_to_tet_abs": abs(best_delta),
        "is_pre_tet": 1 if -30 <= best_delta <= -1 else 0,
        "is_tat_nien_period": 1 if -21 <= best_delta <= -1 else 0,
        "is_tet": 1 if 0 <= best_delta <= 2 else 0,
        "is_post_tet": 1 if 3 <= best_delta <= 7 else 0,
    }
