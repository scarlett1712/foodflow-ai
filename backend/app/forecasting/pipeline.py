"""
backend/app/forecasting/pipeline.py
Pipeline huấn luyện Universal F&B XGBoost Model:
- 1 Universal Model duy nhất học mối tương quan giữa Metadata (category, branch_type, price),
  Động lượng chuỗi thời gian (Lags, Rolling, Trend Ratios), và Ngữ cảnh Lịch (Thứ, Lễ, Tết VN, Events).
- Khử phụ thuộc vào ID cố định -> Hoạt động cho bất kỳ chi nhánh, món ăn mới, hoặc dataset người dùng nhập.
- Baseline: Moving Average cùng thứ trong 4 tuần gần nhất.
- Đánh giá: WAPE và MAE.
"""

import os
import sys
import sqlite3
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
import xgboost as xgb
from sklearn.metrics import mean_absolute_error

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from .features import (
    build_features_for_dish,
    prepare_categorical_dtypes,
    FEATURE_COLUMNS,
    STANDARD_CATEGORIES,
    STANDARD_BRANCH_TYPES,
    STANDARD_EVENT_FLAGS,
)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "foodflow.db")
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_models")
os.makedirs(MODEL_DIR, exist_ok=True)

def calculate_wape(y_true, y_pred):
    sum_actual = np.sum(y_true)
    if sum_actual == 0:
        return 0.0
    return np.sum(np.abs(y_true - y_pred)) / sum_actual

def load_data_from_db(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    query = """
    SELECT 
        s.date,
        s.branch_id,
        s.branch_name,
        COALESCE(b.type, 'general') as branch_type,
        s.dish_id,
        s.dish_name,
        s.category,
        COALESCE(d.price, 50000.0) as price,
        s.quantity,
        s.revenue,
        s.event_flag,
        c.is_weekend,
        c.is_holiday,
        c.day_of_week
    FROM sales s
    JOIN calendar c ON s.date = c.date
    LEFT JOIN branches b ON s.branch_id = b.id
    LEFT JOIN dishes d ON s.dish_id = d.id
    ORDER BY s.date ASC, s.branch_id ASC, s.dish_id ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def train_and_evaluate_all():
    print("=" * 85)
    print("HUẤN LUYỆN UNIVERSAL F&B DEMAND MODEL (TỔNG QUÁT CHO MỌI QUÁN / MỌI MÓN / DATASET MỚI)")
    print("=" * 85)

    df_all = load_data_from_db()
    unique_dates = sorted(df_all["date"].unique())
    split_idx = int(len(unique_dates) * 0.85) # ~620 ngày train, ~110 ngày test
    split_date = unique_dates[split_idx]

    print(f"-> Tổng số ngày: {len(unique_dates)} ngày ({unique_dates[0]} -> {unique_dates[-1]})")
    print(f"-> Train set: {split_idx} ngày ({unique_dates[0]} -> {unique_dates[split_idx-1]})")
    print(f"-> Test set : {len(unique_dates) - split_idx} ngày ({split_date} -> {unique_dates[-1]})")
    print("-" * 85)

    branches = df_all[["branch_id", "branch_name"]].drop_duplicates().values

    # =========================================================================
    # BƯỚC 1: Build features RIÊNG từng chuỗi (branch, dish) để đảm bảo lag/rolling chuẩn
    # =========================================================================
    all_features = []
    baseline_results = []

    for b_id, b_name in branches:
        df_branch = df_all[df_all["branch_id"] == b_id]
        dish_ids = df_branch["dish_id"].unique()

        for dish_id in dish_ids:
            df_dish = df_branch[df_branch["dish_id"] == dish_id].copy()
            dish_name = df_dish["dish_name"].iloc[0]

            # Trích xuất Universal Features
            df_features = build_features_for_dish(df_dish)
            df_features["branch_id"] = b_id
            df_features["dish_id"] = dish_id

            all_features.append(df_features)

            # Tính Baseline (Moving average 4 tuần cùng thứ)
            test_df_baseline = df_features[df_features["date"] >= split_date].copy()
            baseline_preds = []
            for _, row in test_df_baseline.iterrows():
                dow = row["day_of_week"]
                past_same_dow = df_features[(df_features["date"] < row["date"]) & (df_features["day_of_week"] == dow)]["quantity"].tail(4)
                if len(past_same_dow) > 0:
                    baseline_preds.append(past_same_dow.mean())
                else:
                    baseline_preds.append(row["rolling_mean_7"])

            if len(baseline_preds) > 0:
                y_test_base = test_df_baseline["quantity"].values
                baseline_preds_arr = np.array(baseline_preds)
                mae_base = mean_absolute_error(y_test_base, baseline_preds_arr)
                wape_base = calculate_wape(y_test_base, baseline_preds_arr) * 100
                baseline_results.append({
                    "branch_id": b_id,
                    "branch_name": b_name,
                    "dish_id": dish_id,
                    "dish_name": dish_name,
                    "baseline_mae": round(mae_base, 2),
                    "baseline_wape": round(wape_base, 2),
                    "avg_test_sales": round(test_df_baseline["quantity"].mean(), 1),
                })

    # =========================================================================
    # BƯỚC 2: Gộp thành tập huấn luyện Universal & Thiết lập Categoricals chuẩn
    # =========================================================================
    df_global = pd.concat(all_features, ignore_index=True)
    df_global = prepare_categorical_dtypes(df_global)

    category_mapping = {
        "category": STANDARD_CATEGORIES,
        "branch_type": STANDARD_BRANCH_TYPES,
        "event_flag": STANDARD_EVENT_FLAGS,
        "weather_condition": [
            "nang_dep", "nang_nong", "mua_rao", "mua_bao", "lanh_ret"
        ]
    }

    train_df = df_global[df_global["date"] < split_date].copy()
    test_df = df_global[df_global["date"] >= split_date].copy()

    X_train = train_df[FEATURE_COLUMNS]
    y_train = train_df["quantity"]
    X_test = test_df[FEATURE_COLUMNS]
    y_test = test_df["quantity"]

    print(f"-> Train samples: {len(X_train):,} | Test samples: {len(X_test):,}")
    print(f"-> Số lượng đặc trưng: {len(FEATURE_COLUMNS)}")

    # =========================================================================
    # BƯỚC 3: Train Universal XGBoost Model
    # =========================================================================
    model = xgb.XGBRegressor(
        n_estimators=120,
        max_depth=5,
        learning_rate=0.06,
        subsample=0.85,
        colsample_bytree=0.85,
        enable_categorical=True,
        tree_method="hist",
        random_state=42,
    )
    model.fit(X_train, y_train)

    xgb_preds = model.predict(X_test)
    xgb_preds = np.maximum(xgb_preds, 0)

    # =========================================================================
    # BƯỚC 4: Đánh giá WAPE & MAE
    # =========================================================================
    overall_mae_xgb = mean_absolute_error(y_test, xgb_preds)
    overall_wape_xgb = calculate_wape(y_test, xgb_preds) * 100

    baseline_df = pd.DataFrame(baseline_results)
    test_df = test_df.copy()
    test_df["xgb_prediction"] = xgb_preds

    results = []
    for _, base_row in baseline_df.iterrows():
        b_id = base_row["branch_id"]
        d_id = base_row["dish_id"]

        mask = (test_df["branch_id"] == b_id) & (test_df["dish_id"] == d_id)
        subset = test_df[mask]

        if len(subset) > 0:
            y_true = subset["quantity"].values
            y_pred = subset["xgb_prediction"].values
            mae_xgb = mean_absolute_error(y_true, y_pred)
            wape_xgb = calculate_wape(y_true, y_pred) * 100
        else:
            mae_xgb = 0
            wape_xgb = 0

        results.append({
            "branch_id": b_id,
            "branch_name": base_row["branch_name"],
            "dish_id": d_id,
            "dish_name": base_row["dish_name"],
            "baseline_mae": base_row["baseline_mae"],
            "baseline_wape": base_row["baseline_wape"],
            "xgb_mae": round(mae_xgb, 2),
            "xgb_wape": round(wape_xgb, 2),
            "improvement_pct": round(((base_row["baseline_wape"] - wape_xgb) / base_row["baseline_wape"]) * 100, 2) if base_row["baseline_wape"] > 0 else 0,
            "avg_test_sales": base_row["avg_test_sales"],
        })

    # =========================================================================
    # BƯỚC 5: Train Full Model trên toàn bộ dữ liệu & Lưu Model
    # =========================================================================
    X_full = df_global[FEATURE_COLUMNS]
    y_full = df_global["quantity"]

    full_model = xgb.XGBRegressor(
        n_estimators=120,
        max_depth=5,
        learning_rate=0.06,
        subsample=0.85,
        colsample_bytree=0.85,
        enable_categorical=True,
        tree_method="hist",
        random_state=42,
    )
    full_model.fit(X_full, y_full)

    model_save_path = os.path.join(MODEL_DIR, "global_model.joblib")
    mapping_save_path = os.path.join(MODEL_DIR, "category_mapping.joblib")
    joblib.dump(full_model, model_save_path)
    joblib.dump(category_mapping, mapping_save_path)

    # In kết quả
    res_df = pd.DataFrame(results)
    avg_base_wape = res_df["baseline_wape"].mean()
    avg_xgb_wape = res_df["xgb_wape"].mean()
    improvement = ((avg_base_wape - avg_xgb_wape) / avg_base_wape) * 100 if avg_base_wape > 0 else 0

    print(f"\n{'CHI NHÁNH':<18} | {'MÃ':<5} | {'TÊN MÓN':<25} | {'AVG SALE':<8} | {'BASE WAPE':<10} | {'XGB WAPE':<10} | {'CẢI THIỆN':<10}")
    print("-" * 100)
    for r in results[:10]:
        print(f"{r['branch_name']:<18} | {r['dish_id']:<5} | {r['dish_name']:<25} | {r['avg_test_sales']:<8} | {r['baseline_wape']}%{'':<4} | {r['xgb_wape']}% | {r['improvement_pct']}%")
    print(f"... (và {len(results) - 10} cặp chi nhánh-món ăn khác)")
    print("-" * 100)

    print(f"\nTỔNG KẾT UNIVERSAL F&B MODEL:")
    print(f"-> Baseline WAPE     : {avg_base_wape:.2f}% (Sai số TB: {res_df['baseline_mae'].mean():.2f} phần)")
    print(f"-> Universal XGB WAPE: {avg_xgb_wape:.2f}% (Sai số TB: {res_df['xgb_mae'].mean():.2f} phần)")
    print(f"-> Cải thiện tương đối: {improvement:.1f}%")
    print(f"-> Overall Test WAPE : {overall_wape_xgb:.2f}%")
    print(f"-> Đã lưu Universal Model tại: {model_save_path}")
    print(f"-> Đã lưu category mapping tại: {mapping_save_path}")
    print("=" * 85)

    return res_df

if __name__ == "__main__":
    train_and_evaluate_all()
