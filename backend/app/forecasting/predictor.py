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
import json
import sqlite3
import time
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple

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


# PERF FIX: Cache model trong RAM - chi doc dia 1 lan duy nhat
_MODEL_CACHE = {"model": None, "path": None}

def _load_universal_model(model_path=MODEL_PATH):
    """Tai model Universal XGBoost voi application-level cache."""
    if _MODEL_CACHE["model"] is not None and _MODEL_CACHE["path"] == model_path:
        return _MODEL_CACHE["model"]
    if os.path.exists(model_path):
        try:
            model = joblib.load(model_path)
            _MODEL_CACHE["model"] = model
            _MODEL_CACHE["path"] = model_path
            return model
        except Exception:
            return None
    return None


# ==========================================
# PERFORMANCE FIX: In-Memory TTL Cache cho Forecast
# Khi Frontend gọi cùng lúc 3 API (dashboard/summary, forecast, purchase-recommendations),
# chỉ 1 phép tính duy nhất được thực hiện, 2 API còn lại nhận ngay kết quả từ cache.
# ==========================================
_FORECAST_CACHE: Dict[str, Tuple[float, Any]] = {}
CACHE_TTL = 600  # Lưu kết quả trong 10 phút


def clear_forecast_cache():
    """Xóa cache dự báo khi có dữ liệu mới được tải lên hoặc cập nhật."""
    _FORECAST_CACHE.clear()


def get_forecast_for_next_days(n_days=7, branch_id=None, db_path=DB_PATH, model_path=MODEL_PATH, city="ho_chi_minh"):
    """
    Sinh dự báo cho n_days ngày tiếp theo cho các chi nhánh trong Database.
    Hỗ trợ tích hợp Dự báo thời tiết tự động theo từng ngày.
    Có In-Memory TTL Cache để tránh tính toán trùng lặp.
    """
    # 1. Kiểm tra cache
    cache_key = f"{branch_id}_{city}_{n_days}"
    now = time.time()
    if cache_key in _FORECAST_CACHE:
        cached_time, cached_result = _FORECAST_CACHE[cache_key]
        if now - cached_time < CACHE_TTL:
            return cached_result

    # 2. Nếu chưa có cache → Tính toán
    result = _execute_raw_forecast(n_days, branch_id, db_path, model_path, city)
    _FORECAST_CACHE[cache_key] = (now, result)
    return result


def _execute_raw_forecast(n_days=7, branch_id=None, db_path=DB_PATH, model_path=MODEL_PATH, city="ho_chi_minh"):
    import logging
    _log = logging.getLogger("foodflow.forecast")
    t0 = time.time()

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

    t_db = time.time()
    _log.info(f"[PERF] DB queries: {t_db - t0:.3f}s (branches={len(df_branches)}, sales={len(df_sales)}, dishes={len(df_dishes)})")

    preorders_dict = {}
    for row in preorders_rows:
        b_id, p_date, d_id, qty, items_json = row
        if items_json:
            # BUG-009 FIX: import json đã được di chuyển ra đầu file
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
    t_model = time.time()
    _log.info(f"[PERF] Model load: {t_model - t_db:.3f}s (model={'loaded' if model else 'NONE'})")

    # Lấy dự báo thời tiết N ngày tới
    weather_list = get_weather_forecast(city_key=city, days=n_days + 2)
    t_weather = time.time()
    _log.info(f"[PERF] Weather API: {t_weather - t_model:.3f}s (days={len(weather_list)})")
    weather_by_date = {w["date"]: w for w in weather_list}


    # Ngày bắt đầu dự báo
    if len(df_sales) > 0:
        last_date_str = df_sales["date"].max()
        last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
    else:
        last_date = datetime.now()

    branch_results = []

    for _, b_row in df_branches.iterrows():
        b_id = b_row["id"]
        b_name = b_row["name"]
        b_type = normalize_branch_type(b_row.get("type", "general"))

        dish_forecasts = []

        # ---------------------------------------------------------------
        # PERF FIX: Pre-compute per-day features OUTSIDE dish loop
        # (weather, calendar, tet) - same for all 22 dishes on same day
        # ---------------------------------------------------------------
        day_features = []
        for i in range(1, n_days + 1):
            target_date = last_date + timedelta(days=i)
            date_str = target_date.strftime("%Y-%m-%d")
            month_day = target_date.strftime("%m-%d")
            dow = target_date.weekday()
            is_wknd = 1 if dow in [5, 6] else 0
            is_hol = 1 if month_day in VIETNAM_HOLIDAYS else 0
            hol_name = VIETNAM_HOLIDAYS.get(month_day, "")

            # Weather - computed once per day, not 22x
            w_info = weather_by_date.get(date_str)
            if not w_info and len(weather_list) > 0:
                w_info = weather_list[min(i - 1, len(weather_list) - 1)]

            temp_val = w_info["temperature"] if w_info else 32.0
            precip_val = w_info["precipitation_mm"] if w_info else 0.0
            is_rain_val = w_info["is_rainy"] if w_info else 0
            cond_val = w_info["weather_condition"] if w_info else classify_weather(temp_val, precip_val)
            cond_desc = w_info["weather_desc"] if w_info else get_weather_description(cond_val)

            # Tet features - computed once per day
            tet_features = _compute_tet_features_for_date(target_date)

            day_features.append({
                "target_date": target_date,
                "date_str": date_str,
                "dow": dow,
                "is_wknd": is_wknd,
                "is_hol": is_hol,
                "hol_name": hol_name,
                "temp_val": temp_val,
                "precip_val": precip_val,
                "is_rain_val": is_rain_val,
                "cond_val": cond_val,
                "cond_desc": cond_desc,
                "tet_features": tet_features,
            })

        # BRANCH ISOLATION: Lọc các món thực sự thuộc chi nhánh này (qua lịch sử bán hàng hoặc đơn đặt trước)
        branch_sales_dish_ids = set(df_sales[df_sales["branch_id"] == b_id]["dish_id"].unique())
        for (p_bid, _, p_did) in preorders_dict.keys():
            if p_bid == b_id and p_did:
                branch_sales_dish_ids.add(p_did)

        if len(branch_sales_dish_ids) > 0:
            df_target_dishes = df_dishes[df_dishes["id"].isin(branch_sales_dish_ids)]
        else:
            df_target_dishes = df_dishes

        for _, d_row in df_target_dishes.iterrows():
            d_id = d_row["id"]
            d_name = d_row["name"]
            d_cat = normalize_category(d_row.get("category", "Khac"))
            d_price = float(d_row.get("price", 50000.0) or 50000.0)

            # Filter sales history for this branch+dish
            sim_df = df_sales[(df_sales["branch_id"] == b_id) & (df_sales["dish_id"] == d_id)].copy()
            sim_df = sim_df.sort_values("date").reset_index(drop=True)

            # PERF FIX: Track quantity history as list (not pd.concat)
            # Use statistics.stdev (ddof=1, matches pandas .std()) for rolling_std_7
            import statistics
            sim_quantities = sim_df["quantity"].tolist()
            sim_dates = pd.to_datetime(sim_df["date"]).dt.dayofweek.tolist() if len(sim_df) > 0 else []

            daily_list = []

            for day_info in day_features:
                date_str = day_info["date_str"]
                dow = day_info["dow"]
                is_wknd = day_info["is_wknd"]
                is_hol = day_info["is_hol"]
                hol_name = day_info["hol_name"]
                temp_val = day_info["temp_val"]
                precip_val = day_info["precip_val"]
                is_rain_val = day_info["is_rain_val"]
                cond_val = day_info["cond_val"]
                cond_desc = day_info["cond_desc"]
                tet_features = day_info["tet_features"]
                target_date = day_info["target_date"]

                # Time-series stats from list (matching original pandas logic)
                n_hist = len(sim_quantities)
                if n_hist >= 7:
                    lag_1 = float(sim_quantities[-1])
                    lag_7 = float(sim_quantities[-7])
                    lag_14 = float(sim_quantities[-14]) if n_hist >= 14 else lag_7
                    lag_28 = float(sim_quantities[-28]) if n_hist >= 28 else lag_14

                    tail_7 = sim_quantities[-7:]
                    tail_14 = sim_quantities[-14:]
                    tail_28 = sim_quantities[-28:]
                    rolling_7 = sum(tail_7) / len(tail_7)
                    rolling_14 = sum(tail_14) / len(tail_14)
                    rolling_28 = sum(tail_28) / len(tail_28)
                    # statistics.stdev uses ddof=1 (same as pandas .std())
                    rolling_std_7 = statistics.stdev(tail_7) if len(tail_7) >= 2 else 0.0
                elif n_hist > 0:
                    mean_val = sum(sim_quantities) / n_hist
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
                if n_hist > 0:
                    same_dow_vals = [sim_quantities[k] for k in range(len(sim_dates)) if sim_dates[k] == dow]
                    same_dow_tail4 = same_dow_vals[-4:] if len(same_dow_vals) >= 4 else same_dow_vals
                    base_val = int(round(sum(same_dow_tail4) / len(same_dow_tail4))) if len(same_dow_tail4) > 0 else int(round(rolling_7))
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
                    "weather_condition": cond_val,
                    "weather_desc": cond_desc,
                    "temperature": temp_val,
                    "precipitation_mm": precip_val,
                    "is_rainy": bool(is_rain_val),
                    "weather_impact_reason": w_impact_reason,
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

                # PERF FIX: Append to list instead of pd.concat (O(1) vs O(n))
                sim_quantities.append(xgb_val)
                sim_dates.append(dow)

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

    t_pred = time.time()
    _log.info(f"[PERF] Prediction loop: {t_pred - t_weather:.3f}s | TOTAL: {t_pred - t0:.3f}s (branches={len(df_branches)}, dishes={len(df_dishes)}, days={n_days})")

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
