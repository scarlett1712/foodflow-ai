"""
backend/app/forecasting/predictor.py
Dịch vụ dự báo nhu cầu tương lai (Universal Weather-Aware Forecast Service):
- Dự báo n ngày tiếp theo cho bất kỳ chi nhánh / món ăn nào trong Database
- Tích hợp Dự báo Thời tiết (Open-Meteo API): Nắng nóng, Mưa rào, Mưa bão, Lạnh rét
- Tự động điều chỉnh nhu cầu theo tác động thời tiết (Đồ uống tăng khi nắng nóng, Món nước/lẩu tăng khi mưa/lạnh)
- Cung cấp hàm predict_custom_timeseries() để dự báo cho BẤT KỲ dữ liệu nào người dùng nhập (zero-shot)
- Tích hợp Đơn đặt trước đa món (Multi-item Preorders)
- Tích hợp Lịch Việt Nam & 6 đặc trưng chu kỳ Tết Nguyên Đán
"""

import os
import sys
import sqlite3
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from .features import (
    build_features_for_dish,
    prepare_categorical_dtypes,
    FEATURE_COLUMNS,
    normalize_category,
    normalize_branch_type,
    STANDARD_CATEGORIES,
    STANDARD_BRANCH_TYPES,
    STANDARD_EVENT_FLAGS,
)
from .vn_calendar import VIETNAM_HOLIDAYS, get_tet_date, TET_FEATURE_NAMES
from .weather_service import (
    get_weather_forecast,
    get_weather_multiplier,
    get_weather_description,
    classify_weather,
    STANDARD_WEATHER_CONDITIONS,
)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "foodflow.db")
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_models", "global_model.joblib")
MAPPING_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_models", "category_mapping.joblib")


def _compute_tet_features_for_date(target_date):
    """Tính 6 cột Tết features cho 1 ngày cụ thể (dùng khi predict tương lai)."""
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


def _load_universal_model(model_path=MODEL_PATH):
    """Tải model Universal XGBoost."""
    if os.path.exists(model_path):
        try:
            return joblib.load(model_path)
        except Exception:
            return None
    return None


def get_forecast_for_next_days(n_days=7, branch_id=None, db_path=DB_PATH, model_path=MODEL_PATH, city="ho_chi_minh"):
    """
    Sinh dự báo cho n_days ngày tiếp theo cho các chi nhánh trong Database.
    Hỗ trợ tích hợp Dự báo thời tiết tự động theo từng ngày.
    """
    conn = sqlite3.connect(db_path)
    
    # Query branches động
    if branch_id and branch_id != "ALL":
        df_branches = pd.read_sql_query("SELECT id, name, address, type FROM branches WHERE id = ?", conn, params=(branch_id,))
    else:
        df_branches = pd.read_sql_query("SELECT id, name, address, type FROM branches", conn)

    # Query sales động
    df_sales = pd.read_sql_query("""
        SELECT s.date, s.branch_id, s.branch_name, s.dish_id, s.dish_name, s.category, s.quantity, s.revenue,
               s.event_flag,
               c.is_weekend, c.is_holiday, c.day_of_week
        FROM sales s
        JOIN calendar c ON s.date = c.date
        ORDER BY s.date ASC, s.branch_id ASC, s.dish_id ASC
    """, conn)

    # Query dishes động
    df_dishes = pd.read_sql_query("SELECT id, name, category, price FROM dishes", conn)
    
    # Query preorders
    cur = conn.cursor()
    cur.execute("SELECT branch_id, date, dish_id, quantity, items_json FROM preorders")
    preorders_rows = cur.fetchall()
    conn.close()

    preorders_dict = {}
    for row in preorders_rows:
        b_id, p_date, d_id, qty, items_json = row
        if items_json:
            import json
            try:
                items = json.loads(items_json)
                for itm in items:
                    dish_key = (b_id, p_date, itm.get("dish_id"))
                    preorders_dict[dish_key] = preorders_dict.get(dish_key, 0) + int(itm.get("quantity", 0))
            except Exception:
                pass
        elif d_id and qty:
            key = (b_id, p_date, d_id)
            preorders_dict[key] = preorders_dict.get(key, 0) + int(qty or 0)

    # Load Universal Model
    model = _load_universal_model(model_path)

    # Lấy dự báo thời tiết N ngày tới
    weather_list = get_weather_forecast(city_key=city, days=n_days + 2)
    weather_by_date = {w["date"]: w for w in weather_list}

    # Ngày bắt đầu dự báo: neo theo ngày hiện tại thực tế (datetime.now()) để dự báo đúng ngày mai theo thời gian thực
    last_date = datetime.now()

    branch_results = []

    for _, b_row in df_branches.iterrows():
        b_id = b_row["id"]
        b_name = b_row["name"]
        b_type = normalize_branch_type(b_row.get("type", "general"))

        dish_forecasts = []

        for _, d_row in df_dishes.iterrows():
            d_id = d_row["id"]
            d_name = d_row["name"]
            d_cat = normalize_category(d_row.get("category", "Khác"))
            d_price = float(d_row.get("price", 50000.0) or 50000.0)

            # Lọc lịch sử của chi nhánh + món ăn này
            sim_df = df_sales[(df_sales["branch_id"] == b_id) & (df_sales["dish_id"] == d_id)].copy()
            sim_df = sim_df.sort_values("date").reset_index(drop=True)

            daily_list = []

            for i in range(1, n_days + 1):
                target_date = last_date + timedelta(days=i)
                date_str = target_date.strftime("%Y-%m-%d")
                month_day = target_date.strftime("%m-%d")
                dow = target_date.weekday()
                is_wknd = 1 if dow in [5, 6] else 0
                is_hol = 1 if month_day in VIETNAM_HOLIDAYS else 0
                hol_name = VIETNAM_HOLIDAYS.get(month_day, "")

                # Thời tiết ngày này
                w_info = weather_by_date.get(date_str)
                if not w_info and len(weather_list) > 0:
                    w_info = weather_list[min(i - 1, len(weather_list) - 1)]
                
                temp_val = w_info["temperature"] if w_info else 32.0
                precip_val = w_info["precipitation_mm"] if w_info else 0.0
                is_rain_val = w_info["is_rainy"] if w_info else 0
                cond_val = w_info["weather_condition"] if w_info else classify_weather(temp_val, precip_val)
                cond_desc = w_info["weather_desc"] if w_info else get_weather_description(cond_val)

                # Thống kê chuỗi thời gian
                if len(sim_df) >= 7:
                    lag_1 = float(sim_df["quantity"].iloc[-1])
                    lag_7 = float(sim_df["quantity"].iloc[-7]) if len(sim_df) >= 7 else lag_1
                    lag_14 = float(sim_df["quantity"].iloc[-14]) if len(sim_df) >= 14 else lag_7
                    lag_28 = float(sim_df["quantity"].iloc[-28]) if len(sim_df) >= 28 else lag_14

                    rolling_7 = float(sim_df["quantity"].tail(7).mean())
                    rolling_14 = float(sim_df["quantity"].tail(14).mean())
                    rolling_28 = float(sim_df["quantity"].tail(28).mean())
                    rolling_std_7 = float(sim_df["quantity"].tail(7).std() or 0.0)
                elif len(sim_df) > 0:
                    mean_val = float(sim_df["quantity"].mean())
                    lag_1 = lag_7 = lag_14 = lag_28 = mean_val
                    rolling_7 = rolling_14 = rolling_28 = mean_val
                    rolling_std_7 = 0.0
                else:
                    # Cold start: chưa có dữ liệu lịch sử
                    lag_1 = lag_7 = lag_14 = lag_28 = 20.0
                    rolling_7 = rolling_14 = rolling_28 = 20.0
                    rolling_std_7 = 0.0

                trend_momentum = (lag_1 + 1.0) / (rolling_7 + 1.0)
                growth_ratio = (rolling_7 + 1.0) / (rolling_28 + 1.0)
                volatility = rolling_std_7 / (rolling_7 + 1.0)

                # Tết features
                tet_features = _compute_tet_features_for_date(target_date)

                feat_dict = {
                    "category": d_cat,
                    "branch_type": b_type,
                    "event_flag": "none",
                    "weather_condition": cond_val,
                    "temperature": temp_val,
                    "precipitation_mm": precip_val,
                    "is_rainy": is_rain_val,
                    "price": d_price,
                    "log_price": np.log1p(d_price),
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
                    "trend_momentum_7": trend_momentum,
                    "growth_ratio_28": growth_ratio,
                    "volatility_7": volatility,
                }
                feat_dict.update(tet_features)

                feat_vec = pd.DataFrame([feat_dict])[FEATURE_COLUMNS]
                feat_vec = prepare_categorical_dtypes(feat_vec)

                # Baseline prediction
                if len(sim_df) > 0:
                    same_dow = sim_df[pd.to_datetime(sim_df["date"]).dt.dayofweek == dow]["quantity"].tail(4)
                    base_val = int(round(same_dow.mean() if len(same_dow) > 0 else rolling_7))
                else:
                    base_val = 20

                # Universal Model prediction
                if model is not None:
                    try:
                        pred_val = model.predict(feat_vec)[0]
                        xgb_val = int(round(max(pred_val, 0)))
                    except Exception:
                        xgb_val = base_val
                else:
                    xgb_val = base_val

                # Preorders
                po_qty = preorders_dict.get((b_id, date_str, d_id), 0)
                final_qty = max(xgb_val, po_qty)

                diff = xgb_val - base_val
                diff_pct = round((diff / base_val) * 100, 1) if base_val > 0 else 0.0

                w_mult, w_impact_reason = get_weather_multiplier(d_cat, cond_val, b_type)

                daily_list.append({
                    "date": date_str,
                    "day_name": ["T2", "T3", "T4", "T5", "T6", "T7", "CN"][dow],
                    "day_of_week": dow,
                    "is_weekend": bool(is_wknd),
                    "is_holiday": bool(is_hol),
                    "holiday_name": hol_name,
                    # Weather info
                    "weather_condition": cond_val,
                    "weather_desc": cond_desc,
                    "temperature": temp_val,
                    "precipitation_mm": precip_val,
                    "is_rainy": bool(is_rain_val),
                    "weather_impact_reason": w_impact_reason,
                    # Predictions & Aliases
                    "baseline_quantity": base_val,
                    "xgb_quantity": xgb_val,
                    "xgb_forecast": xgb_val,
                    "preorder_quantity": po_qty,
                    "confirmed_preorders": po_qty,
                    "final_forecast_quantity": final_qty,
                    "expected_demand": final_qty,
                    "unit_price": d_price,
                    "expected_revenue": final_qty * d_price,
                    "estimated_revenue": final_qty * d_price,
                    "difference_vs_baseline": diff,
                    "difference_percent": diff_pct,
                    "days_to_tet": tet_features["days_to_tet"],
                    "is_tet_period": bool(tet_features["is_tat_nien_period"] or tet_features["is_tet"])
                })

                # Append vào sim_df cho các ngày tiếp theo trong rolling
                sim_row = pd.DataFrame([{
                    "date": date_str,
                    "branch_id": b_id,
                    "branch_name": b_name,
                    "dish_id": d_id,
                    "dish_name": d_name,
                    "category": d_cat,
                    "quantity": xgb_val,
                    "revenue": xgb_val * d_price,
                    "event_flag": "none",
                    "weather_condition": cond_val,
                    "temperature": temp_val,
                    "precipitation_mm": precip_val,
                    "is_rainy": is_rain_val,
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
            "branch_type": b_type,
            "dishes": dish_forecasts
        })

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "city": city,
        "forecast_horizon_days": n_days,
        "branches": branch_results
    }


def predict_custom_timeseries(
    sales_history_df: pd.DataFrame,
    future_days: int = 7,
    branch_type: str = "general",
    dish_category: str = "Khác",
    price: float = 50000.0,
    preorders: dict = None,
    weather_condition: str = None,
    temperature: float = None,
    precipitation_mm: float = None,
    model_path: str = MODEL_PATH
) -> dict:
    """
    Hàm dự báo Phổ quát (Universal Zero-Shot Prediction with Weather Integration):
    Nhận vào BẤT KỲ DataFrame lịch sử bán hàng nào từ người dùng,
    kết hợp điều kiện thời tiết (nắng nóng, mưa rào, mưa bão, lạnh) để dự báo.
    """
    model = _load_universal_model(model_path)
    b_type = normalize_branch_type(branch_type)
    d_cat = normalize_category(dish_category)
    d_price = float(price if price > 0 else 50000.0)
    preorders = preorders or {}

    # Lấy dự báo thời tiết mặc định
    weather_forecasts = get_weather_forecast(days=future_days + 2)
    weather_by_date = {w["date"]: w for w in weather_forecasts}

    # Chuẩn bị DataFrame lịch sử
    sim_df = sales_history_df.copy()
    sim_df["date"] = pd.to_datetime(sim_df["date"])
    sim_df = sim_df.sort_values("date").reset_index(drop=True)

    if len(sim_df) > 0:
        last_date = sim_df["date"].max()
    else:
        last_date = pd.Timestamp.now().floor("D")

    daily_forecasts = []

    for i in range(1, future_days + 1):
        target_date = last_date + timedelta(days=i)
        date_str = target_date.strftime("%Y-%m-%d")
        month_day = target_date.strftime("%m-%d")
        dow = target_date.weekday()
        is_wknd = 1 if dow in [5, 6] else 0
        is_hol = 1 if month_day in VIETNAM_HOLIDAYS else 0
        hol_name = VIETNAM_HOLIDAYS.get(month_day, "")

        # Xử lý thời tiết
        w_info = weather_by_date.get(date_str)
        if not w_info and len(weather_forecasts) > 0:
            w_info = weather_forecasts[min(i - 1, len(weather_forecasts) - 1)]

        cur_temp = temperature if temperature is not None else (w_info["temperature"] if w_info else 32.0)
        cur_precip = precipitation_mm if precipitation_mm is not None else (w_info["precipitation_mm"] if w_info else 0.0)
        cur_cond = weather_condition if weather_condition else (w_info["weather_condition"] if w_info else classify_weather(cur_temp, cur_precip))
        cur_desc = get_weather_description(cur_cond)
        is_rain_val = 1 if (cur_precip >= 3.0 or cur_cond in ["mua_rao", "mua_bao"]) else 0

        if len(sim_df) >= 7:
            lag_1 = float(sim_df["quantity"].iloc[-1])
            lag_7 = float(sim_df["quantity"].iloc[-7]) if len(sim_df) >= 7 else lag_1
            lag_14 = float(sim_df["quantity"].iloc[-14]) if len(sim_df) >= 14 else lag_7
            lag_28 = float(sim_df["quantity"].iloc[-28]) if len(sim_df) >= 28 else lag_14

            rolling_7 = float(sim_df["quantity"].tail(7).mean())
            rolling_14 = float(sim_df["quantity"].tail(14).mean())
            rolling_28 = float(sim_df["quantity"].tail(28).mean())
            rolling_std_7 = float(sim_df["quantity"].tail(7).std() or 0.0)
        elif len(sim_df) > 0:
            mean_val = float(sim_df["quantity"].mean())
            lag_1 = lag_7 = lag_14 = lag_28 = mean_val
            rolling_7 = rolling_14 = rolling_28 = mean_val
            rolling_std_7 = 0.0
        else:
            lag_1 = lag_7 = lag_14 = lag_28 = 20.0
            rolling_7 = rolling_14 = rolling_28 = 20.0
            rolling_std_7 = 0.0

        trend_momentum = (lag_1 + 1.0) / (rolling_7 + 1.0)
        growth_ratio = (rolling_7 + 1.0) / (rolling_28 + 1.0)
        volatility = rolling_std_7 / (rolling_7 + 1.0)

        tet_features = _compute_tet_features_for_date(target_date)

        feat_dict = {
            "category": d_cat,
            "branch_type": b_type,
            "event_flag": "none",
            "weather_condition": cur_cond,
            "temperature": cur_temp,
            "precipitation_mm": cur_precip,
            "is_rainy": is_rain_val,
            "price": d_price,
            "log_price": np.log1p(d_price),
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
            "trend_momentum_7": trend_momentum,
            "growth_ratio_28": growth_ratio,
            "volatility_7": volatility,
        }
        feat_dict.update(tet_features)

        feat_vec = pd.DataFrame([feat_dict])[FEATURE_COLUMNS]
        feat_vec = prepare_categorical_dtypes(feat_vec)

        # Baseline
        if len(sim_df) > 0:
            same_dow = sim_df[sim_df["date"].dt.dayofweek == dow]["quantity"].tail(4)
            base_val = int(round(same_dow.mean() if len(same_dow) > 0 else rolling_7))
        else:
            base_val = 20

        # Predict
        if model is not None:
            try:
                pred_val = model.predict(feat_vec)[0]
                xgb_val = int(round(max(pred_val, 0)))
            except Exception:
                xgb_val = base_val
        else:
            xgb_val = base_val

        po_qty = preorders.get(date_str, 0)
        final_qty = max(xgb_val, po_qty)

        diff = xgb_val - base_val
        diff_pct = round((diff / base_val) * 100, 1) if base_val > 0 else 0.0

        w_mult, w_impact_reason = get_weather_multiplier(d_cat, cur_cond, b_type)

        daily_forecasts.append({
            "date": date_str,
            "day_name": ["T2", "T3", "T4", "T5", "T6", "T7", "CN"][dow],
            "day_of_week": dow,
            "is_weekend": bool(is_wknd),
            "is_holiday": bool(is_hol),
            "holiday_name": hol_name,
            # Weather
            "weather_condition": cur_cond,
            "weather_desc": cur_desc,
            "temperature": cur_temp,
            "precipitation_mm": cur_precip,
            "is_rainy": bool(is_rain_val),
            "weather_impact_reason": w_impact_reason,
            # Predictions
            "baseline_quantity": base_val,
            "xgb_quantity": xgb_val,
            "xgb_forecast": xgb_val,
            "preorder_quantity": po_qty,
            "confirmed_preorders": po_qty,
            "final_forecast_quantity": final_qty,
            "expected_demand": final_qty,
            "unit_price": d_price,
            "expected_revenue": final_qty * d_price,
            "estimated_revenue": final_qty * d_price,
            "difference_vs_baseline": diff,
            "difference_percent": diff_pct,
            "days_to_tet": tet_features["days_to_tet"],
            "is_tet_period": bool(tet_features["is_tat_nien_period"] or tet_features["is_tet"])
        })

        # Append sim row
        sim_row = pd.DataFrame([{
            "date": target_date,
            "quantity": xgb_val
        }])
        sim_df = pd.concat([sim_df, sim_row], ignore_index=True)

    total_qty = sum(d["final_forecast_quantity"] for d in daily_forecasts)
    total_rev = sum(d["expected_revenue"] for d in daily_forecasts)

    return {
        "status": "success",
        "branch_type": b_type,
        "dish_category": d_cat,
        "unit_price": d_price,
        "forecast_horizon_days": future_days,
        "total_predicted_quantity": total_qty,
        "total_expected_revenue": total_rev,
        "daily_forecasts": daily_forecasts
    }
