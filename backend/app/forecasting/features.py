"""
backend/app/forecasting/features.py
Trích xuất đặc trưng Phổ quát (Universal Feature Engineering) cho F&B Demand Forecasting:
- Loại bỏ phụ thuộc vào ID cứng (branch_id / dish_id) -> dùng Metadata & Scale-Free Dynamics
- Thuộc tính Phổ quát: category, branch_type, price, log_price
- Động lượng & Quy mô chuỗi thời gian: lag_1..28, rolling_mean_7..28, rolling_std_7
- Tỷ lệ tương đối (Scale-Invariant Ratios): trend_momentum_7, growth_ratio_28, volatility_7
- Calendar & Lễ hội VN: day_of_week, day_of_month, month, is_weekend, is_holiday
- Đặc trưng Thời tiết (Weather Dynamics): weather_condition, temperature, precipitation_mm, is_rainy
- 6 đặc trưng chu kỳ Tết Nguyên Đán từ vn_calendar.py
"""

import pandas as pd
import numpy as np

from .vn_calendar import add_tet_features, TET_FEATURE_NAMES
from .weather_service import STANDARD_WEATHER_CONDITIONS, classify_weather

# Từ điển chuẩn hóa Category và Branch Type (có fallback tự động cho dữ liệu mới)
STANDARD_CATEGORIES = [
    "Món Nước",
    "Món Khô",
    "Cà Phê",
    "Trà & Trái Cây",
    "Đồ Ăn Nhẹ",
    "Bánh & Tráng Miệng",
    "Hải Sản",
    "Món Nướng & Lẩu",
    "Khác"
]

STANDARD_BRANCH_TYPES = [
    "am_thuc_truyen_thong",
    "bistro",
    "tra_sua",
    "quan_nhau",
    "fastfood",
    "cafe_bakery",
    "hai_san",
    "general"
]

STANDARD_EVENT_FLAGS = [
    "none",
    "don_tiec_dot_xuat",
    "su_kien_dia_phuong",
    "thoi_tiet_cuc_doan",
    "su_co_von_hanh"
]


def normalize_category(cat: str) -> str:
    """Chuẩn hóa nhóm món về danh mục chuẩn hoặc 'Khác'."""
    if not isinstance(cat, str) or not cat.strip():
        return "Khác"
    cat_clean = cat.strip()
    for std_cat in STANDARD_CATEGORIES:
        if std_cat.lower() == cat_clean.lower():
            return std_cat
    # Gợi ý nhóm dựa trên từ khóa phổ biến
    lower = cat_clean.lower()
    if any(k in lower for k in ["nước", "bún", "phở", "mì", "hủ tiếu", "cháo", "canh", "soup"]):
        return "Món Nước"
    if any(k in lower for k in ["cơm", "bánh mì", "gỏi", "cuốn", "xôi", "khô"]):
        return "Món Khô"
    if any(k in lower for k in ["cà phê", "cafe", "coffee", "bạc xỉu", "espresso"]):
        return "Cà Phê"
    if any(k in lower for k in ["trà", "nước ép", "sinh tố", "juice", "tea", "sữa chua", "matcha"]):
        return "Trà & Trái Cây"
    if any(k in lower for k in ["hải sản", "tôm", "cua", "cá", "mực", "ốc", "seafood"]):
        return "Hải Sản"
    if any(k in lower for k in ["lẩu", "nướng", "bbq", "hotpot"]):
        return "Món Nướng & Lẩu"
    return "Khác"


def normalize_branch_type(b_type: str) -> str:
    """Chuẩn hóa loại hình chi nhánh về nhóm chuẩn hoặc 'general'."""
    if not isinstance(b_type, str) or not b_type.strip():
        return "general"
    b_type_clean = b_type.strip().lower()
    
    for std_type in STANDARD_BRANCH_TYPES:
        if std_type == b_type_clean:
            return std_type
            
    if "bistro" in b_type_clean:
        return "bistro"
    if any(k in b_type_clean for k in ["tra_sua", "trà sữa", "tra sua", "milk tea", "boba"]):
        return "tra_sua"
    if any(k in b_type_clean for k in ["hải sản", "hai_san", "seafood"]):
        return "hai_san"
    if any(k in b_type_clean for k in ["quán nhậu", "quan_nhau", "bia hơi"]):
        return "quan_nhau"
    if any(k in b_type_clean for k in ["fastfood", "fast food", "gà rán", "burger"]):
        return "fastfood"
    if any(k in b_type_clean for k in ["ẩm thực truyền thống", "am_thuc_truyen_thong"]):
        return "am_thuc_truyen_thong"
    if any(k in b_type_clean for k in ["cafe_bakery", "tiệm bánh"]):
        return "cafe_bakery"

    return "general"


def build_features_for_dish(df_dish: pd.DataFrame) -> pd.DataFrame:
    """
    Nhận vào DataFrame lịch sử của 1 món ăn tại 1 chi nhánh và tạo các cột đặc trưng.
    Hỗ trợ cả chuỗi thời gian ngắn (Cold Start / Món mới) thông qua adaptive padding.
    """
    df = df_dish.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # Đảm bảo có các cột cơ bản
    if "price" not in df.columns:
        df["price"] = 50000.0
    if "category" not in df.columns:
        df["category"] = "Khác"
    if "branch_type" not in df.columns:
        df["branch_type"] = "general"
    if "event_flag" not in df.columns:
        df["event_flag"] = "none"

    df["category"] = df["category"].apply(normalize_category)
    df["branch_type"] = df["branch_type"].apply(normalize_branch_type)
    df["event_flag"] = df["event_flag"].fillna("none").astype(str)

    # 1. Temporal Features
    df["day_of_week"] = df["date"].dt.dayofweek
    df["day_of_month"] = df["date"].dt.day
    df["month"] = df["date"].dt.month
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    
    if "is_holiday" not in df.columns:
        df["is_holiday"] = 0

    # 2. Weather Features (nếu chưa có thì suy diễn theo tháng)
    if "temperature" not in df.columns:
        # Nhiệt độ trung bình theo tháng tại VN
        df["temperature"] = df["month"].map(lambda m: 34.5 if m in [4, 5, 6, 7, 8] else (26.5 if m in [12, 1] else 31.0))
    if "precipitation_mm" not in df.columns:
        df["precipitation_mm"] = df["month"].map(lambda m: 12.0 if m in [6, 7, 8, 9, 10] else 0.0)
    if "is_rainy" not in df.columns:
        df["is_rainy"] = (df["precipitation_mm"] >= 3.0).astype(int)
    if "weather_condition" not in df.columns:
        df["weather_condition"] = [classify_weather(t, p) for t, p in zip(df["temperature"], df["precipitation_mm"])]

    # 3. Metadata món ăn & giá
    df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(50000.0)
    df["log_price"] = np.log1p(np.maximum(df["price"], 0.0))

    # 4. Lag Features
    for lag in [1, 7, 14, 28]:
        df[f"lag_{lag}"] = df["quantity"].shift(lag)

    # 5. Rolling Statistics (shift 1 tránh rò rỉ target ngày hiện tại)
    df["rolling_mean_7"] = df["quantity"].shift(1).rolling(window=7, min_periods=1).mean()
    df["rolling_mean_14"] = df["quantity"].shift(1).rolling(window=14, min_periods=1).mean()
    df["rolling_mean_28"] = df["quantity"].shift(1).rolling(window=28, min_periods=1).mean()
    df["rolling_std_7"] = df["quantity"].shift(1).rolling(window=7, min_periods=1).std().fillna(0)

    # 6. Scale-Invariant / Relative Trend Ratios (giúp mô hình tổng quát hóa mọi quy mô quán)
    df["trend_momentum_7"] = (df["lag_1"] + 1.0) / (df["rolling_mean_7"] + 1.0)
    df["growth_ratio_28"] = (df["rolling_mean_7"] + 1.0) / (df["rolling_mean_28"] + 1.0)
    df["volatility_7"] = df["rolling_std_7"] / (df["rolling_mean_7"] + 1.0)

    # 7. Tết features (6 cột chuẩn lịch Việt Nam)
    df = add_tet_features(df)

    # 8. Fill NA cho những ngày đầu chuỗi (Cold-start adaptive fill)
    df["lag_1"] = df["lag_1"].fillna(df["quantity"])
    df["lag_7"] = df["lag_7"].fillna(df["lag_1"])
    df["lag_14"] = df["lag_14"].fillna(df["lag_7"])
    df["lag_28"] = df["lag_28"].fillna(df["lag_14"])
    df["rolling_mean_7"] = df["rolling_mean_7"].fillna(df["quantity"])
    df["rolling_mean_14"] = df["rolling_mean_14"].fillna(df["rolling_mean_7"])
    df["rolling_mean_28"] = df["rolling_mean_28"].fillna(df["rolling_mean_14"])
    df["rolling_std_7"] = df["rolling_std_7"].fillna(0.0)
    df["trend_momentum_7"] = df["trend_momentum_7"].fillna(1.0)
    df["growth_ratio_28"] = df["growth_ratio_28"].fillna(1.0)
    df["volatility_7"] = df["volatility_7"].fillna(0.0)

    df = df.bfill().ffill()
    return df


def prepare_categorical_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Chuyển category, branch_type, event_flag, weather_condition sang Categorical Dtype chuẩn."""
    df = df.copy()
    df["category"] = pd.Categorical(df["category"].apply(normalize_category), categories=STANDARD_CATEGORIES)
    df["branch_type"] = pd.Categorical(df["branch_type"].apply(normalize_branch_type), categories=STANDARD_BRANCH_TYPES)
    
    # event_flag
    clean_event = df["event_flag"].fillna("none").astype(str)
    clean_event = clean_event.apply(lambda x: x if x in STANDARD_EVENT_FLAGS else "none")
    df["event_flag"] = pd.Categorical(clean_event, categories=STANDARD_EVENT_FLAGS)

    # weather_condition
    clean_weather = df["weather_condition"].fillna("nang_dep").astype(str)
    clean_weather = clean_weather.apply(lambda x: x if x in STANDARD_WEATHER_CONDITIONS else "nang_dep")
    df["weather_condition"] = pd.Categorical(clean_weather, categories=STANDARD_WEATHER_CONDITIONS)
    return df


# Danh sách Features Tổng Quát của Universal Model (Không phụ thuộc ID cứng)
FEATURE_COLUMNS = [
    # Thuộc tính bản chất (Intrinsic Categorical)
    "category",
    "branch_type",
    "event_flag",
    "weather_condition",
    # Mức giá & Phân khúc (Numerical)
    "price",
    "log_price",
    # Calendar & Thời gian
    "day_of_week",
    "day_of_month",
    "month",
    "is_weekend",
    "is_holiday",
    # Thời tiết (Weather Numerical)
    "temperature",
    "precipitation_mm",
    "is_rainy",
    # Lags
    "lag_1",
    "lag_7",
    "lag_14",
    "lag_28",
    # Rolling Statistics
    "rolling_mean_7",
    "rolling_mean_14",
    "rolling_mean_28",
    "rolling_std_7",
    # Scale-Invariant / Trend Ratios
    "trend_momentum_7",
    "growth_ratio_28",
    "volatility_7",
] + TET_FEATURE_NAMES  # 6 cột chu kỳ Tết
