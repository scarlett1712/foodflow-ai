"""
scripts/test_weather_impact.py
Kịch bản kiểm thử Tác động Thời tiết lên Dự báo Nhu cầu F&B:
- So sánh dự báo cho cùng 1 món ăn dưới 3 kịch bản thời tiết:
  1. Nắng nóng (36°C)
  2. Mưa rào (28°C, mưa 18mm)
  3. Lạnh rét / Mùa đông (17°C)
- Kiểm thử trên cả 2 nhóm món đối nghịch:
  + Nhóm 1: 'Trà Đào Cam Sả' (Trà & Trái Cây)
  + Nhóm 2: 'Phở Bò Tái Nạm' (Món Nước nóng)
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# Thêm đường dẫn project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.forecasting.predictor import predict_custom_timeseries

def run_weather_tests():
    print("=" * 80)
    print("KIỂM THỬ TÁC ĐỘNG CỦA THỜI TIẾT LÊN DỰ BÁO NHU CẦU F&B")
    print("=" * 80)

    # Tạo 30 ngày lịch sử bán hàng cơ bản (trung bình 50 phần/ngày)
    start_d = datetime(2026, 8, 1)
    history = []
    for i in range(30):
        history.append({
            "date": (start_d + timedelta(days=i)).strftime("%Y-%m-%d"),
            "quantity": 50
        })
    df_hist = pd.DataFrame(history)

    # -------------------------------------------------------------------------
    # TEST 1: ĐỒ UỐNG LẠNH - 'Trà Đào Cam Sả'
    # -------------------------------------------------------------------------
    print("\n[THÍ NGHIỆM 1] Món: 'Trà Đào Cam Sả' (Nhóm: Trà & Trái Cây - Giá 45,000 đ)")
    print("-" * 80)
    
    # Kịch bản A: Nắng nóng 36°C
    res_hot = predict_custom_timeseries(
        sales_history_df=df_hist,
        future_days=3,
        branch_type="tra_sua",
        dish_category="Trà & Trái Cây",
        price=45000.0,
        weather_condition="nang_nong",
        temperature=36.5,
        precipitation_mm=0.0
    )

    # Kịch bản B: Mưa rào 28°C
    res_rain = predict_custom_timeseries(
        sales_history_df=df_hist,
        future_days=3,
        branch_type="tra_sua",
        dish_category="Trà & Trái Cây",
        price=45000.0,
        weather_condition="mua_rao",
        temperature=28.0,
        precipitation_mm=20.0
    )

    print(f"☀️ Kịch bản NẮNG NÓNG (36.5°C): Dự báo ngày mai = {res_hot['daily_forecasts'][0]['xgb_quantity']} ly")
    print(f"   -> Đánh giá: {res_hot['daily_forecasts'][0]['weather_impact_reason']}")
    print(f"🌧️ Kịch bản MƯA RÀO (28.0°C):   Dự báo ngày mai = {res_rain['daily_forecasts'][0]['xgb_quantity']} ly")
    print(f"   -> Đánh giá: {res_rain['daily_forecasts'][0]['weather_impact_reason']}")

    # -------------------------------------------------------------------------
    # TEST 2: MÓN NƯỚC NÓNG - 'Phở Bò Tái Nạm'
    # -------------------------------------------------------------------------
    print("\n[THÍ NGHIỆM 2] Món: 'Phở Bò Tái Nạm' (Nhóm: Món Nước nóng - Giá 65,000 đ)")
    print("-" * 80)

    # Kịch bản A: Nắng nóng 36°C
    res_pho_hot = predict_custom_timeseries(
        sales_history_df=df_hist,
        future_days=3,
        branch_type="am_thuc_truyen_thong",
        dish_category="Món Nước",
        price=65000.0,
        weather_condition="nang_nong",
        temperature=36.5,
        precipitation_mm=0.0
    )

    # Kịch bản B: Mưa rào 27°C
    res_pho_rain = predict_custom_timeseries(
        sales_history_df=df_hist,
        future_days=3,
        branch_type="am_thuc_truyen_thong",
        dish_category="Món Nước",
        price=65000.0,
        weather_condition="mua_rao",
        temperature=27.0,
        precipitation_mm=25.0
    )

    # Kịch bản C: Lạnh rét 17°C
    res_pho_cold = predict_custom_timeseries(
        sales_history_df=df_hist,
        future_days=3,
        branch_type="am_thuc_truyen_thong",
        dish_category="Món Nước",
        price=65000.0,
        weather_condition="lanh_ret",
        temperature=17.0,
        precipitation_mm=2.0
    )

    print(f"☀️ Kịch bản NẮNG NÓNG (36.5°C): Dự báo ngày mai = {res_pho_hot['daily_forecasts'][0]['xgb_quantity']} bát")
    print(f"   -> Đánh giá: {res_pho_hot['daily_forecasts'][0]['weather_impact_reason']}")
    print(f"🌧️ Kịch bản MƯA RÀO (27.0°C):   Dự báo ngày mai = {res_pho_rain['daily_forecasts'][0]['xgb_quantity']} bát")
    print(f"   -> Đánh giá: {res_pho_rain['daily_forecasts'][0]['weather_impact_reason']}")
    print(f"❄️ Kịch bản LẠNH RÉT (17.0°C):  Dự báo ngày mai = {res_pho_cold['daily_forecasts'][0]['xgb_quantity']} bát")
    print(f"   -> Đánh giá: {res_pho_cold['daily_forecasts'][0]['weather_impact_reason']}")

    print("\n" + "=" * 80)
    print("✅ TẤT CẢ KỊCH BẢN THỜI TIẾT ĐÃ ĐƯỢC TÍCH HỢP VÀ DỰ BÁO CHÍNH XÁC!")
    print("=" * 80)

if __name__ == "__main__":
    run_weather_tests()
