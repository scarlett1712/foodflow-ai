"""
backend/app/forecasting/weather_service.py
Dịch vụ Dự báo Thời tiết & Tác động Nhu cầu F&B (Weather Forecasting Service):
- Lấy dữ liệu thời tiết thực tế từ Open-Meteo API (miễn phí, không cần API key)
- Fallback tự động thông minh theo khí hậu Việt Nam khi offline
- Phân loại thời tiết: nang_nong (Nắng nóng), nang_dep (Nắng đẹp), mua_rao (Mưa rào), mua_bao (Mưa bão), lanh_ret (Lạnh rét)
- Tính toán hệ số tác động thời tiết lên từng nhóm món ăn (Món Nước, Món Khô, Đồ Uống, Lẩu/Nướng)
"""

import urllib.request
import json
import random
from datetime import datetime, timedelta
import pandas as pd

# Toạ độ các thành phố lớn tại Việt Nam
VIETNAM_CITIES = {
    "ho_chi_minh": {"name": "TP. Hồ Chí Minh", "lat": 10.8231, "lon": 106.6297},
    "ha_noi": {"name": "Hà Nội", "lat": 21.0285, "lon": 105.8542},
    "da_nang": {"name": "Đà Nẵng", "lat": 16.0544, "lon": 108.2022},
    "can_tho": {"name": "Cần Thơ", "lat": 10.0452, "lon": 105.7469},
    "hai_phong": {"name": "Hải Phòng", "lat": 20.8449, "lon": 106.6881},
    "da_lat": {"name": "Đà Lạt", "lat": 11.9404, "lon": 108.4583},
}

STANDARD_WEATHER_CONDITIONS = [
    "nang_dep",     # Trời mát/nắng đẹp (26 - 32°C, không mưa)
    "nang_nong",    # Nắng nóng gay gắt (> 33°C, kích cầu đồ uống)
    "mua_rao",      # Mưa rào / mưa dông (kích cầu món nước, giảm đồ lạnh)
    "mua_bao",      # Mưa bão lớn / ngập úng (giảm khách ra đường)
    "lanh_ret"      # Lạnh rét / mùa đông miền Bắc (kích cầu lẩu/món nước)
]


def classify_weather(temp_max: float, precipitation_mm: float, weathercode: int = 0) -> str:
    """Phân loại điều kiện thời tiết dựa trên nhiệt độ và lượng mưa."""
    if precipitation_mm >= 30.0 or weathercode in [95, 96, 99]:
        return "mua_bao"
    elif precipitation_mm >= 3.0 or weathercode in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
        return "mua_rao"
    elif temp_max < 20.0:
        return "lanh_ret"
    elif temp_max >= 34.0:
        return "nang_nong"
    else:
        return "nang_dep"


def get_weather_description(condition: str) -> str:
    """Mô tả tiếng Việt cho trạng thái thời tiết."""
    desc_map = {
        "nang_dep": "Nắng dịu / Thời tiết đẹp",
        "nang_nong": "Nắng nóng gay gắt",
        "mua_rao": "Mưa rào / Mưa dông",
        "mua_bao": "Mưa bão / Mưa rất to",
        "lanh_ret": "Trời lạnh / Rét buốt"
    }
    return desc_map.get(condition, "Bình thường")


def get_weather_forecast(city_key: str = "ho_chi_minh", days: int = 7) -> list:
    """
    Lấy dự báo thời tiết cho N ngày tiếp theo.
    Ưu tiên gọi Open-Meteo API thực tế, nếu offline sẽ dùng cơ chế mô phỏng khí hậu chuẩn VN.
    """
    city = VIETNAM_CITIES.get(city_key.lower(), VIETNAM_CITIES["ho_chi_minh"])
    lat = city["lat"]
    lon = city["lon"]
    
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode&timezone=Asia%2FBangkok"
    
    forecasts = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'FoodFlowAI/1.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
            daily = data.get("daily", {})
            dates = daily.get("time", [])
            temp_maxs = daily.get("temperature_2m_max", [])
            precips = daily.get("precipitation_sum", [])
            wcodes = daily.get("weathercode", [])

            for i in range(min(days, len(dates))):
                t_max = float(temp_maxs[i]) if i < len(temp_maxs) else 32.0
                precip = float(precips[i]) if i < len(precips) else 0.0
                wcode = int(wcodes[i]) if i < len(wcodes) else 0
                cond = classify_weather(t_max, precip, wcode)

                forecasts.append({
                    "date": dates[i],
                    "temperature": round(t_max, 1),
                    "precipitation_mm": round(precip, 1),
                    "is_rainy": 1 if precip >= 3.0 else 0,
                    "weather_condition": cond,
                    "weather_desc": get_weather_description(cond)
                })
    except Exception:
        # Fallback mô phỏng khí hậu chuẩn theo mùa tại Việt Nam
        today = datetime.now()
        for i in range(1, days + 1):
            target_d = today + timedelta(days=i)
            d_str = target_d.strftime("%Y-%m-%d")
            month = target_d.month

            # Khí hậu mùa hè / mùa mưa
            if month in [5, 6, 7, 8, 9, 10]:
                is_rain = random.random() < 0.35
                temp = random.uniform(32.0, 36.0) if not is_rain else random.uniform(28.0, 31.0)
                precip = random.uniform(5.0, 25.0) if is_rain else 0.0
            else:
                is_rain = random.random() < 0.10
                temp = random.uniform(29.0, 33.0)
                precip = random.uniform(3.0, 10.0) if is_rain else 0.0

            cond = classify_weather(temp, precip)
            forecasts.append({
                "date": d_str,
                "temperature": round(temp, 1),
                "precipitation_mm": round(precip, 1),
                "is_rainy": 1 if precip >= 3.0 else 0,
                "weather_condition": cond,
                "weather_desc": get_weather_description(cond)
            })

    return forecasts


def get_weather_multiplier(category: str, weather_condition: str, branch_type: str = "general") -> tuple[float, str]:
    """
    Tính hệ số tác động thời tiết và giải thích lý do cho từng nhóm món:
    - Nắng nóng: Đồ uống tăng (+20% đến +35%), Món nước nóng giảm nhẹ (-10%)
    - Mưa rào: Món Nước, Lẩu tăng (+15% đến +25%), Trà sữa/đồ đá giảm (-15%)
    - Mưa bão: Giảm toàn diện do khách ngại ra ngoài (-30% đến -50%)
    - Trời lạnh: Món Nước, Lẩu nướng tăng mạnh (+30%)
    """
    cat = category.strip()
    cond = weather_condition.strip()

    if cond == "mua_bao":
        return 0.55, "Mưa bão lớn / ngập nước làm giảm mạnh lưu lượng khách (-45%)"

    if cond == "nang_nong":
        if cat in ["Trà & Trái Cây", "Cà Phê", "Đồ Ăn Nhẹ"]:
            return 1.28, "Nắng nóng gay gắt kích cầu đồ uống giải khát (+28%)"
        elif cat in ["Món Nước", "Món Nướng & Lẩu"]:
            return 0.90, "Thời tiết oi bức làm giảm nhẹ nhu cầu món nước nóng (-10%)"
        return 1.0, "Thời tiết nắng nóng, nhu cầu ổn định"

    elif cond == "mua_rao":
        if cat in ["Món Nước", "Món Nướng & Lẩu"]:
            return 1.22, "Trời mưa làm tăng nhu cầu các món nước ấm nóng, lẩu (+22%)"
        elif cat in ["Trà & Trái Cây"]:
            return 0.85, "Trời mưa làm giảm nhu cầu đồ uống lạnh ngoài trời (-15%)"
        return 1.0, "Trời mưa vừa, nhu cầu giao hàng ổn định"

    elif cond == "lanh_ret":
        if cat in ["Món Nước", "Món Nướng & Lẩu", "Hải Sản"]:
            return 1.30, "Trời lạnh thúc đẩy mạnh nhu cầu ăn đồ nóng, lẩu, nướng (+30%)"
        elif cat in ["Trà & Trái Cây"]:
            return 0.75, "Trời lạnh làm giảm đáng kể đồ uống lạnh (-25%)"
        return 1.0, "Thời tiết lạnh, nhu cầu ấm nóng tăng"

    # nang_dep
    return 1.0, "Thời tiết đẹp, nhu cầu đạt mức chuẩn"
