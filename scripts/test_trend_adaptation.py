"""
scripts/test_trend_adaptation.py
Thực nghiệm kiểm chứng: Khả năng bắt kịp xu hướng tăng trưởng mới (Trend Adaptation vs Old Baseline)
"""
import sys
import os
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.app.forecasting.predictor import predict_custom_timeseries

def test_trend():
    # 60 ngày lịch sử:
    # - 40 ngày đầu: bán ổn định mức 50 phần/ngày
    # - 20 ngày gần đây: quán bắt đầu viral / tăng trưởng đều đặn từ 50 lên 100 phần/ngày
    data = []
    start = datetime(2026, 7, 1)
    for i in range(40):
        data.append({'date': (start + timedelta(days=i)).strftime('%Y-%m-%d'), 'quantity': 50})
    for i in range(20):
        qty = int(round(50 + i * 2.5)) # 50, 52, 55, ..., 98, 100
        data.append({'date': (start + timedelta(days=40+i)).strftime('%Y-%m-%d'), 'quantity': qty})

    df = pd.DataFrame(data)
    res = predict_custom_timeseries(df, future_days=7, branch_type='bistro', dish_category='Món Nước', price=60000)

    print("=" * 85)
    print("KẾT QUẢ THỰC NGHIỆM: QUÁN ĐANG TRONG GIAI ĐOẠN TĂNG TRƯỞNG NÓNG (50 -> 100 PHẦN)")
    print("=" * 85)
    print("3 ngày gần nhất trước khi dự báo:", [d['quantity'] for d in data[-3:]], "(Mức bán hiện tại ~98 - 100 phần)")
    print("-" * 85)
    print(f"{'NGÀY':<12} | {'THỨ':<6} | {'BASELINE (CŨ)':<16} | {'XGBOOST (HỌC XU HƯỚNG)':<25} | {'CHÊNH LỆCH':<12}")
    print("-" * 85)
    for d in res['daily_forecasts']:
        print(f"{d['date']:<12} | {d['day_name']:<6} | {d['baseline_quantity']:<16} | {d['xgb_quantity']:<25} | {d['difference_vs_baseline']:+d} phần ({d['difference_percent']:+.1f}%)")
    print("-" * 85)

if __name__ == "__main__":
    test_trend()
