"""
backend/app/forecasting/vn_calendar.py
Module dùng chung cho lịch Việt Nam — Tết Nguyên Đán, ngày lễ, hệ số sinh dữ liệu, và feature engineering.
Được import bởi cả generate_data.py (sinh dữ liệu) và features.py/predictor.py (train + predict).
"""

import pandas as pd

try:
    from lunarcalendar import Converter, Lunar
    HAS_LUNARCALENDAR = True
except ImportError:
    HAS_LUNARCALENDAR = False

# ============================================================
# 1. Ngày Tết Nguyên Đán — hard-code đã verify chính xác
# ============================================================
TET_DATES = {
    2025: pd.Timestamp("2025-01-29"),   # Ất Tỵ — verified bằng lunarcalendar
    2026: pd.Timestamp("2026-02-17"),   # Bính Ngọ — verified bằng lunarcalendar
}

def get_tet_date(year: int) -> pd.Timestamp:
    """Ưu tiên tra bảng hard-code (đã verify); fallback bằng lunarcalendar nếu năm khác."""
    if year in TET_DATES:
        return TET_DATES[year]
    if HAS_LUNARCALENDAR:
        solar = Converter.Lunar2Solar(Lunar(year, 1, 1, isleap=False))
        return pd.Timestamp(solar.year, solar.month, solar.day)
    raise ValueError(f"Không tìm được ngày Tết cho năm {year}. Cài lunarcalendar: pip install lunarcalendar")

# ============================================================
# 2. Danh sách ngày lễ Việt Nam (dương lịch cố định)
# ============================================================
VIETNAM_HOLIDAYS = {
    "01-01": "Tết Dương Lịch",
    "02-14": "Lễ Tình Nhân Valentine",
    "03-08": "Quốc tế Phụ nữ",
    "04-30": "Giải phóng miền Nam",
    "05-01": "Quốc tế Lao động",
    "09-02": "Quốc khánh 2/9",
    "10-20": "Ngày Phụ nữ VN",
    "11-20": "Ngày Nhà giáo VN",
    "12-24": "Đêm Giáng Sinh",
    "12-25": "Lễ Giáng Sinh",
}

# ============================================================
# 3. Hệ số Tết — CHỈ dùng trong generate_data.py (sinh ground-truth)
#    Kịch bản: cả 3 chi nhánh MỞ CỬA xuyên Tết
#    Hệ số đã sửa theo review: mùng 1 = 1.35 (tăng, không giảm)
# ============================================================
def get_tet_synthetic_multiplier(date, tet_date):
    """CHỈ dùng trong generate_data.py để tạo ra ground-truth qty.
    Các hệ số là ƯỚC LƯỢNG THẬN TRỌNG dựa trên xu hướng đã xác nhận,
    KHÔNG phải số liệu tuyệt đối — có thể chỉnh lại nếu cần.

    Kịch bản: chi nhánh MỞ CỬA xuyên Tết.
    - Trước Tết: tất niên đẩy nhu cầu tăng mạnh
    - Đúng Tết: khách dồn từ quán đóng cửa xung quanh → vẫn cao hơn bình thường
    - Sau Tết: hạ nhiệt dần về mức bình thường
    """
    if isinstance(date, str):
        date = pd.Timestamp(date)
    if isinstance(tet_date, str):
        tet_date = pd.Timestamp(tet_date)

    delta = (date - tet_date).days

    if -30 <= delta < -21:
        return 1.10   # bắt đầu tăng nhẹ
    elif -21 <= delta < -14:
        return 1.20   # tất niên bắt đầu rõ
    elif -14 <= delta < -3:
        return 1.45   # cao điểm tất niên
    elif -3 <= delta <= -1:
        return 1.15   # 28-30 Tết
    elif delta == 0:
        return 1.35   # mùng 1 — mở cửa, khách dồn từ quán đóng
    elif 1 <= delta <= 2:
        return 1.15   # mùng 2-3, vẫn cao hơn bình thường
    elif 3 <= delta <= 4:
        return 1.0    # mùng 4-5, trở lại bình thường
    elif 5 <= delta <= 7:
        return 1.0    # gần bình thường
    else:
        return 1.0

# ============================================================
# 4. Tết features — dùng trong features.py (train + predict)
#    CHỈ đưa nhãn giai đoạn, KHÔNG hard-code hệ số số nhân
#    → để model TỰ HỌC mức độ tác động từ dữ liệu
# ============================================================
def add_tet_features(df, tet_dates_for_years=None):
    """Thêm 6 cột Tết features vào DataFrame.

    Args:
        df: DataFrame có cột 'date' (datetime hoặc string)
        tet_dates_for_years: dict {year: tet_date} — nếu None sẽ dùng TET_DATES mặc định

    Returns:
        DataFrame với 6 cột mới: days_to_tet, days_to_tet_abs,
        is_pre_tet, is_tat_nien_period, is_tet, is_post_tet
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    if tet_dates_for_years is None:
        tet_dates_for_years = TET_DATES

    # Tính delta so với Tết gần nhất (của năm hiện tại hoặc năm trước/sau)
    def _get_nearest_tet_delta(row_date):
        year = row_date.year
        best_delta = 999
        for y in [year - 1, year, year + 1]:
            try:
                tet = get_tet_date(y)
                d = (row_date - tet).days
                if abs(d) < abs(best_delta):
                    best_delta = d
            except (ValueError, KeyError):
                continue
        return best_delta

    df["days_to_tet"] = df["date"].apply(_get_nearest_tet_delta)
    df["days_to_tet_abs"] = df["days_to_tet"].abs()
    df["is_pre_tet"] = ((df["days_to_tet"] >= -30) & (df["days_to_tet"] <= -1)).astype(int)
    df["is_tat_nien_period"] = ((df["days_to_tet"] >= -21) & (df["days_to_tet"] <= -1)).astype(int)
    df["is_tet"] = ((df["days_to_tet"] >= 0) & (df["days_to_tet"] <= 2)).astype(int)
    df["is_post_tet"] = ((df["days_to_tet"] >= 3) & (df["days_to_tet"] <= 7)).astype(int)

    return df

# Danh sách tên 6 cột Tết — dùng để thêm vào FEATURE_COLUMNS
TET_FEATURE_NAMES = [
    "days_to_tet",
    "days_to_tet_abs",
    "is_pre_tet",
    "is_tat_nien_period",
    "is_tet",
    "is_post_tet",
]
