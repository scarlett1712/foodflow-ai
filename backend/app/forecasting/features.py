"""
backend/app/forecasting/features.py
Trích xuất đặc trưng (Feature Engineering) cho bài toán dự báo chuỗi thời gian F&B:
- Calendar/Temporal: day_of_week, day_of_month, month, is_weekend, is_holiday
- Lags: lag_1, lag_7, lag_14, lag_28
- Rolling Statistics: rolling_mean_7, rolling_mean_14, rolling_mean_28, rolling_std_7
"""

import pandas as pd
import numpy as np

def build_features_for_dish(df_dish: pd.DataFrame) -> pd.DataFrame:
    """
    Nhận vào DataFrame của 1 món ăn (gồm date, quantity, is_weekend, is_holiday,...)
    và tạo các cột đặc trưng lag, rolling, calendar.
    """
    df = df_dish.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # 1. Temporal Features
    df["day_of_week"] = df["date"].dt.dayofweek
    df["day_of_month"] = df["date"].dt.day
    df["month"] = df["date"].dt.month
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

    # 2. Lag Features
    for lag in [1, 7, 14, 28]:
        df[f"lag_{lag}"] = df["quantity"].shift(lag)

    # 3. Rolling Statistics Features (dùng shift 1 để không rò rỉ dữ liệu target của ngày hiện tại)
    df["rolling_mean_7"] = df["quantity"].shift(1).rolling(window=7, min_periods=1).mean()
    df["rolling_mean_14"] = df["quantity"].shift(1).rolling(window=14, min_periods=1).mean()
    df["rolling_mean_28"] = df["quantity"].shift(1).rolling(window=28, min_periods=1).mean()
    df["rolling_std_7"] = df["quantity"].shift(1).rolling(window=7, min_periods=1).std().fillna(0)

    # 4. Fill NA cho những ngày đầu tiên (khi lag chưa đủ)
    df = df.bfill().ffill()

    return df

FEATURE_COLUMNS = [
    "day_of_week",
    "day_of_month",
    "month",
    "is_weekend",
    "is_holiday",
    "lag_1",
    "lag_7",
    "lag_14",
    "lag_28",
    "rolling_mean_7",
    "rolling_mean_14",
    "rolling_mean_28",
    "rolling_std_7"
]
