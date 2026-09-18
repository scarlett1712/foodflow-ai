"""
backend/app/forecasting/pipeline.py
Pipeline huấn luyện mô hình XGBoost và đánh giá thời gian thực (Chronological Split) cho hệ thống Đa Chi Nhánh (3 Chi nhánh x 22 Món):
- Baseline: Moving Average cùng thứ trong 4 tuần gần nhất
- Model chính: XGBoost Regressor
- Chỉ số đánh giá: MAE, WAPE
- Lưu trữ model artifacts theo từng chi nhánh & món ăn
"""

import os
import sys
import sqlite3
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import xgboost as xgb
from sklearn.metrics import mean_absolute_error

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from .features import build_features_for_dish, FEATURE_COLUMNS

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
        s.dish_id,
        s.dish_name,
        s.category,
        s.quantity,
        s.revenue,
        c.is_weekend,
        c.is_holiday,
        c.day_of_week
    FROM sales s
    JOIN calendar c ON s.date = c.date
    ORDER BY s.date ASC, s.branch_id ASC, s.dish_id ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def train_and_evaluate_all():
    print("=" * 80)
    print("BẮT ĐẦU HUẤN LUYỆN VÀ ĐÁNH GIÁ MÔ HÌNH XGBOOST (3 CHI NHÁNH X 22 MÓN X 730 NGÀY)")
    print("=" * 80)

    df_all = load_data_from_db()
    unique_dates = sorted(df_all["date"].unique())
    split_idx = int(len(unique_dates) * 0.85) # ~620 ngày train, ~110 ngày test
    split_date = unique_dates[split_idx]

    print(f"-> Tổng số ngày: {len(unique_dates)} ngày (730 ngày)")
    print(f"-> Train set: Từ {unique_dates[0]} đến {unique_dates[split_idx-1]} ({split_idx} ngày)")
    print(f"-> Test/Val set: Từ {split_date} đến {unique_dates[-1]} ({len(unique_dates) - split_idx} ngày)")
    print("-" * 80)

    results = []
    models_dict = {}

    branches = df_all[["branch_id", "branch_name"]].drop_duplicates().values

    for b_id, b_name in branches:
        df_branch = df_all[df_all["branch_id"] == b_id]
        dish_ids = df_branch["dish_id"].unique()

        for dish_id in dish_ids:
            df_dish = df_branch[df_branch["dish_id"] == dish_id].copy()
            dish_name = df_dish["dish_name"].iloc[0]

            # Feature Engineering
            df_features = build_features_for_dish(df_dish)

            train_df = df_features[df_features["date"] < split_date].copy()
            test_df = df_features[df_features["date"] >= split_date].copy()

            X_train = train_df[FEATURE_COLUMNS]
            y_train = train_df["quantity"]
            X_test = test_df[FEATURE_COLUMNS]
            y_test = test_df["quantity"]

            # 1. Baseline Model
            baseline_preds = []
            for _, row in test_df.iterrows():
                dow = row["day_of_week"]
                past_same_dow = df_features[(df_features["date"] < row["date"]) & (df_features["day_of_week"] == dow)]["quantity"].tail(4)
                if len(past_same_dow) > 0:
                    baseline_preds.append(past_same_dow.mean())
                else:
                    baseline_preds.append(row["rolling_mean_7"])
            baseline_preds = np.array(baseline_preds)

            # 2. XGBoost Model
            model = xgb.XGBRegressor(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.07,
                subsample=0.85,
                colsample_bytree=0.85,
                random_state=42
            )
            model.fit(X_train, y_train)

            xgb_preds = model.predict(X_test)
            xgb_preds = np.maximum(xgb_preds, 0)

            # Chỉ số
            mae_base = mean_absolute_error(y_test, baseline_preds)
            wape_base = calculate_wape(y_test, baseline_preds) * 100

            mae_xgb = mean_absolute_error(y_test, xgb_preds)
            wape_xgb = calculate_wape(y_test, xgb_preds) * 100

            results.append({
                "branch_id": b_id,
                "branch_name": b_name,
                "dish_id": dish_id,
                "dish_name": dish_name,
                "baseline_mae": round(mae_base, 2),
                "baseline_wape": round(wape_base, 2),
                "xgb_mae": round(mae_xgb, 2),
                "xgb_wape": round(wape_xgb, 2),
                "improvement_pct": round(((wape_base - wape_xgb) / wape_base) * 100, 2),
                "avg_test_sales": round(y_test.mean(), 1)
            })

            # Full model trained on entire series
            full_model = xgb.XGBRegressor(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.07,
                subsample=0.85,
                colsample_bytree=0.85,
                random_state=42
            )
            full_model.fit(df_features[FEATURE_COLUMNS], df_features["quantity"])
            models_dict[f"{b_id}_{dish_id}"] = full_model

    # Lưu models
    model_save_path = os.path.join(MODEL_DIR, "xgboost_models.joblib")
    joblib.dump(models_dict, model_save_path)

    res_df = pd.DataFrame(results)
    
    # In mẫu 10 dòng kết quả
    print(f"{'CHI NHÁNH':<18} | {'MÃ':<5} | {'TÊN MÓN':<25} | {'AVG SALE':<8} | {'BASE WAPE':<10} | {'XGB WAPE':<10}")
    print("-" * 85)
    for r in results[:12]:
        print(f"{r['branch_name']:<18} | {r['dish_id']:<5} | {r['dish_name']:<25} | {r['avg_test_sales']:<8} | {r['baseline_wape']}%{'':<4} | {r['xgb_wape']}%")
    print("... (và 54 cặp chi nhánh-món ăn khác)")
    print("-" * 85)

    avg_base_wape = res_df["baseline_wape"].mean()
    avg_xgb_wape = res_df["xgb_wape"].mean()
    print(f"TỔNG KẾT TOÀN BỘ HỆ THỐNG (66 MÔ HÌNH):")
    print(f"-> Baseline WAPE: {avg_base_wape:.2f}% (Sai số TB: {res_df['baseline_mae'].mean():.2f} phần)")
    print(f"-> XGBoost WAPE : {avg_xgb_wape:.2f}% (Sai số TB: {res_df['xgb_mae'].mean():.2f} phần)")
    print(f"-> Đã lưu 66 models tại: {model_save_path}")
    print("=" * 85)

    return res_df

if __name__ == "__main__":
    train_and_evaluate_all()
