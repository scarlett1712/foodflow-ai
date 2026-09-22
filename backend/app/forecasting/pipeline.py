"""
backend/app/forecasting/pipeline.py
Pipeline huấn luyện mô hình XGBoost Global Model v2:
- 1 model duy nhất cho toàn bộ hệ thống (3 chi nhánh × 22 món)
- XGBoost với enable_categorical=True (native categorical, không one-hot)
- Baseline: Moving Average cùng thứ trong 4 tuần gần nhất
- Chỉ số đánh giá: MAE, WAPE (tổng thể + theo từng branch/dish)
- Lưu model + category mapping cho predictor
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

from .features import build_features_for_dish, prepare_categorical_dtypes, FEATURE_COLUMNS

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
        s.event_flag,
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
    print("HUẤN LUYỆN GLOBAL MODEL v2 (1 MODEL DUY NHẤT — 3 CHI NHÁNH × 22 MÓN × 730 NGÀY)")
    print("=" * 80)

    df_all = load_data_from_db()
    unique_dates = sorted(df_all["date"].unique())
    split_idx = int(len(unique_dates) * 0.85) # ~620 ngày train, ~110 ngày test
    split_date = unique_dates[split_idx]

    print(f"-> Tổng số ngày: {len(unique_dates)} ngày (730 ngày)")
    print(f"-> Train set: Từ {unique_dates[0]} đến {unique_dates[split_idx-1]} ({split_idx} ngày)")
    print(f"-> Test/Val set: Từ {split_date} đến {unique_dates[-1]} ({len(unique_dates) - split_idx} ngày)")
    print("-" * 80)

    branches = df_all[["branch_id", "branch_name"]].drop_duplicates().values

    # =========================================================================
    # BƯỚC 1: Build features RIÊNG từng chuỗi (branch, dish) — giữ nguyên logic cũ
    #         rồi GỘP lại thành 1 DataFrame lớn duy nhất
    # =========================================================================
    all_features = []
    baseline_results = []

    for b_id, b_name in branches:
        df_branch = df_all[df_all["branch_id"] == b_id]
        dish_ids = df_branch["dish_id"].unique()

        for dish_id in dish_ids:
            df_dish = df_branch[df_branch["dish_id"] == dish_id].copy()
            dish_name = df_dish["dish_name"].iloc[0]

            # Feature Engineering — lag/rolling tính RIÊNG từng chuỗi
            df_features = build_features_for_dish(df_dish)
            df_features["branch_id"] = b_id
            df_features["dish_id"] = dish_id

            all_features.append(df_features)

            # Tính baseline RIÊNG theo từng (branch, dish) — baseline vẫn cần xử lý cá nhân
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
    # BƯỚC 2: Gộp toàn bộ → 1 DataFrame lớn, chuẩn bị categorical
    # =========================================================================
    df_global = pd.concat(all_features, ignore_index=True)
    df_global = prepare_categorical_dtypes(df_global)

    # Lưu category mapping (cần cho predictor)
    category_mapping = {
        "branch_id": df_global["branch_id"].cat.categories.tolist(),
        "dish_id": df_global["dish_id"].cat.categories.tolist(),
        "event_flag": df_global["event_flag"].cat.categories.tolist(),
    }

    train_df = df_global[df_global["date"] < split_date].copy()
    test_df = df_global[df_global["date"] >= split_date].copy()

    X_train = train_df[FEATURE_COLUMNS]
    y_train = train_df["quantity"]
    X_test = test_df[FEATURE_COLUMNS]
    y_test = test_df["quantity"]

    print(f"-> Train samples: {len(X_train):,} | Test samples: {len(X_test):,}")
    print(f"-> Features: {len(FEATURE_COLUMNS)} ({FEATURE_COLUMNS[:5]}...)")

    # =========================================================================
    # BƯỚC 3: Train 1 Global XGBoost Model
    # =========================================================================
    model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.07,
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
    # BƯỚC 4: Đánh giá — tổng thể + theo từng (branch, dish)
    # =========================================================================

    # 4a. WAPE tổng thể
    overall_mae_xgb = mean_absolute_error(y_test, xgb_preds)
    overall_wape_xgb = calculate_wape(y_test, xgb_preds) * 100

    baseline_df = pd.DataFrame(baseline_results)
    overall_wape_base = baseline_df["baseline_wape"].mean()
    overall_mae_base = baseline_df["baseline_mae"].mean()

    # 4b. WAPE theo từng (branch, dish)
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
    # BƯỚC 5: Train Full Model (trên toàn bộ dữ liệu) để lưu vào production
    # =========================================================================
    X_full = df_global[FEATURE_COLUMNS]
    y_full = df_global["quantity"]

    full_model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.07,
        subsample=0.85,
        colsample_bytree=0.85,
        enable_categorical=True,
        tree_method="hist",
        random_state=42,
    )
    full_model.fit(X_full, y_full)

    # Lưu model + category mapping
    model_save_path = os.path.join(MODEL_DIR, "global_model.joblib")
    mapping_save_path = os.path.join(MODEL_DIR, "category_mapping.joblib")
    joblib.dump(full_model, model_save_path)
    joblib.dump(category_mapping, mapping_save_path)

    # =========================================================================
    # BƯỚC 6: In kết quả
    # =========================================================================
    res_df = pd.DataFrame(results)

    print(f"\n{'CHI NHÁNH':<18} | {'MÃ':<5} | {'TÊN MÓN':<25} | {'AVG SALE':<8} | {'BASE WAPE':<10} | {'XGB WAPE':<10} | {'CẢI THIỆN':<10}")
    print("-" * 100)
    for r in results[:12]:
        print(f"{r['branch_name']:<18} | {r['dish_id']:<5} | {r['dish_name']:<25} | {r['avg_test_sales']:<8} | {r['baseline_wape']}%{'':<4} | {r['xgb_wape']}% | {r['improvement_pct']}%")
    print(f"... (và {len(results) - 12} cặp chi nhánh-món ăn khác)")
    print("-" * 100)

    # Kiểm tra món nào XGBoost thua baseline quá 0.5 điểm %
    losers = [r for r in results if r["xgb_wape"] > r["baseline_wape"] + 0.5]
    if losers:
        print(f"\n⚠️  CÓ {len(losers)} MÓN XGBOOST THUA BASELINE > 0.5 ĐIỂM %:")
        for r in losers:
            print(f"   {r['branch_id']}_{r['dish_id']} ({r['dish_name']}): Base {r['baseline_wape']}% vs XGB {r['xgb_wape']}%")
        print("   → Ghi log để xử lý ở bước GridSearchCV/hyperparameter tuning sau.")

    avg_base_wape = res_df["baseline_wape"].mean()
    avg_xgb_wape = res_df["xgb_wape"].mean()
    improvement = ((avg_base_wape - avg_xgb_wape) / avg_base_wape) * 100 if avg_base_wape > 0 else 0

    print(f"\nTỔNG KẾT GLOBAL MODEL v2:")
    print(f"-> Baseline WAPE: {avg_base_wape:.2f}% (Sai số TB: {res_df['baseline_mae'].mean():.2f} phần)")
    print(f"-> XGBoost WAPE : {avg_xgb_wape:.2f}% (Sai số TB: {res_df['xgb_mae'].mean():.2f} phần)")
    print(f"-> Cải thiện tương đối: {improvement:.1f}%")
    print(f"-> Overall XGBoost WAPE (tính trên toàn bộ test set gộp): {overall_wape_xgb:.2f}%")
    print(f"-> Đã lưu 1 Global Model tại: {model_save_path}")
    print(f"-> Đã lưu category mapping tại: {mapping_save_path}")
    print("=" * 100)

    return res_df

if __name__ == "__main__":
    train_and_evaluate_all()
