"""
tests/test_full_system_and_chaos.py
Bộ Kiểm Thử Toàn Diện & Chaos Testing Cho FoodFlow AI:
- Thử thách mô hình và toàn bộ hệ thống với dữ liệu bẩn, dị biệt, giá trị biên cực đoan (Chaos Data)
- Kiểm thử các module lõi: Features, Universal Predictor, Weather, Insights, Recipe BOM, API Endpoints
"""

import os
import sys
import unittest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

# Thêm đường dẫn project vào sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from backend.app.main import app
from backend.app.forecasting.features import (
    build_features_for_dish,
    prepare_categorical_dtypes,
    normalize_category,
    normalize_branch_type,
    FEATURE_COLUMNS
)
from backend.app.forecasting.predictor import (
    predict_custom_timeseries,
    get_forecast_for_next_days
)
from backend.app.forecasting.weather_service import (
    classify_weather,
    get_weather_multiplier,
    get_weather_description,
    get_weather_forecast
)
from backend.app.services.insight_service import (
    generate_store_insights,
    _compute_insights_from_dataframe
)
from backend.app.services.recommendation_service import (
    get_purchase_recommendations
)


class TestFoodFlowChaosAndSystem(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    # =========================================================================
    # NHÓM 1: CHAOS & DIRTY DATA TESTING TRÊN FEATURE EXTRACTOR
    # =========================================================================

    def test_01_normalize_weird_categories(self):
        """Kiểm thử chuẩn hóa các danh mục dị biệt, ký tự lạ, emojis"""
        self.assertEqual(normalize_category("Phở bò tái lăn nóng"), "Món Nước")
        self.assertEqual(normalize_category("Bún riêu cua đồng"), "Món Nước")
        self.assertEqual(normalize_category("Cơm tấm sườn bì chả ốp la"), "Món Khô")
        self.assertEqual(normalize_category("Cà phê muối béo ngậy ☕"), "Cà Phê")
        self.assertEqual(normalize_category("Trà mãng cầu đắk lắk"), "Trà & Trái Cây")
        self.assertEqual(normalize_category("Lẩu gà lá é"), "Món Nướng & Lẩu")
        self.assertEqual(normalize_category("Tôm hùm nướng bơ tỏi"), "Hải Sản")
        self.assertEqual(normalize_category("🛸 Thức Ăn Người Ngoài Hành Tinh"), "Khác")
        self.assertEqual(normalize_category(""), "Khác")
        self.assertEqual(normalize_category(None), "Khác")

    def test_02_normalize_weird_branch_types(self):
        """Kiểm thử chuẩn hóa loại hình chi nhánh dị biệt"""
        self.assertEqual(normalize_branch_type("Quán Trà Sữa Giới Trẻ"), "tra_sua")
        self.assertEqual(normalize_branch_type("Bistro Cơm Văn Phòng"), "bistro")
        self.assertEqual(normalize_branch_type("Nhà hàng ẩm thực truyền thống"), "am_thuc_truyen_thong")
        self.assertEqual(normalize_branch_type("Hải Sản Biển Mỹ Khê"), "hai_san")
        self.assertEqual(normalize_branch_type("Quán Cà Phê Dưới Đáy Biển 🌊"), "general")
        self.assertEqual(normalize_branch_type(None), "general")

    def test_03_features_dirty_and_extreme_dataframe(self):
        """Kiểm thử trích xuất đặc trưng với DataFrame lộn xộn ngày, thiếu cột, giá âm, NaN"""
        dirty_data = [
            {"date": "2026-09-20", "quantity": 120, "price": -50000},  # Ngày sau nhưng xếp trước
            {"date": "2026-09-01", "quantity": 0, "price": "InvalidPrice"},  # Giá dạng text
            {"date": "2026-09-05", "quantity": 9999, "price": None},   # Số lượng đột biến, giá None
            {"date": "2026-09-10", "quantity": 50, "category": "Món Lạ Kỳ"},
        ]
        df_dirty = pd.DataFrame(dirty_data)
        
        # Không được ném Exception và phải trả về đủ cột FEATURE_COLUMNS
        df_feats = build_features_for_dish(df_dirty)
        df_feats = prepare_categorical_dtypes(df_feats)
        
        self.assertEqual(len(df_feats), 4)
        for col in FEATURE_COLUMNS:
            self.assertIn(col, df_feats.columns)
        # Đảm bảo không còn giá trị NaN trong features
        self.assertEqual(df_feats[FEATURE_COLUMNS].isna().sum().sum(), 0)

    # =========================================================================
    # NHÓM 2: CHAOS TESTING TRÊN UNIVERSAL MODEL PREDICTOR
    # =========================================================================

    def test_04_predict_super_short_single_day_history(self):
        """Kiểm thử dự báo khi quán chỉ có đúng 1 ngày dữ liệu (Extreme Cold Start)"""
        df_single = pd.DataFrame([{"date": "2026-09-17", "quantity": 30}])
        res = predict_custom_timeseries(
            sales_history_df=df_single,
            future_days=7,
            branch_type="tra_sua",
            dish_category="Trà & Trái Cây",
            price=35000.0
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["daily_forecasts"]), 7)
        for d in res["daily_forecasts"]:
            self.assertGreaterEqual(d["final_forecast_quantity"], 0)
            self.assertGreater(d["expected_revenue"], 0)

    def test_05_predict_with_massive_preorders(self):
        """Kiểm thử dự báo khi có đơn đặt trước khổng lồ vượt xa năng lực (5000 phần)"""
        df_history = pd.DataFrame([
            {"date": "2026-09-15", "quantity": 25},
            {"date": "2026-09-16", "quantity": 28},
            {"date": "2026-09-17", "quantity": 30},
        ])
        target_preorder_date = "2026-09-18"
        res = predict_custom_timeseries(
            sales_history_df=df_history,
            future_days=3,
            branch_type="bistro",
            dish_category="Món Khô",
            price=60000.0,
            preorders={target_preorder_date: 5000}
        )
        day1 = res["daily_forecasts"][0]
        self.assertEqual(day1["date"], target_preorder_date)
        self.assertEqual(day1["final_forecast_quantity"], 5000)
        self.assertEqual(day1["expected_revenue"], 5000 * 60000.0)

    def test_06_predict_extreme_weather_inputs(self):
        """Kiểm thử dự báo dưới các kịch bản thời tiết cực đoan (50°C, -10°C, 200mm bão lũ)"""
        df_history = pd.DataFrame([
            {"date": f"2026-08-{i:02d}", "quantity": 40} for i in range(1, 20)
        ])
        
        # Nắng nóng 48°C
        res_super_hot = predict_custom_timeseries(
            sales_history_df=df_history, future_days=2,
            dish_category="Trà & Trái Cây", weather_condition="nang_nong", temperature=48.0
        )
        self.assertEqual(res_super_hot["status"], "success")
        self.assertGreater(res_super_hot["daily_forecasts"][0]["xgb_quantity"], 0)

        # Mưa bão ngập 150mm
        res_storm = predict_custom_timeseries(
            sales_history_df=df_history, future_days=2,
            dish_category="Món Nước", weather_condition="mua_bao", precipitation_mm=150.0
        )
        self.assertEqual(res_storm["status"], "success")
        self.assertGreater(res_storm["daily_forecasts"][0]["xgb_quantity"], 0)

    # =========================================================================
    # NHÓM 3: WEATHER SERVICE & DYNAMICS
    # =========================================================================

    def test_07_weather_classification_and_multipliers(self):
        """Kiểm thử logic phân loại thời tiết và hệ số tác động"""
        self.assertEqual(classify_weather(36.0, 0.0), "nang_nong")
        self.assertEqual(classify_weather(28.0, 15.0), "mua_rao")
        self.assertEqual(classify_weather(25.0, 45.0), "mua_bao")
        self.assertEqual(classify_weather(16.0, 0.0), "lanh_ret")
        self.assertEqual(classify_weather(29.0, 0.0), "nang_dep")

        mult_drink_hot, _ = get_weather_multiplier("Trà & Trái Cây", "nang_nong")
        self.assertGreater(mult_drink_hot, 1.15)

        mult_soup_rain, _ = get_weather_multiplier("Món Nước", "mua_rao")
        self.assertGreater(mult_soup_rain, 1.10)

        mult_storm, _ = get_weather_multiplier("Món Nước", "mua_bao")
        self.assertLess(mult_storm, 0.8)

    # =========================================================================
    # NHÓM 4: AI DATA INSIGHTS SERVICE
    # =========================================================================

    def test_08_generate_insights_empty_and_valid(self):
        """Kiểm thử engine sinh AI Data Insights"""
        # Test trên DB hiện tại
        insights = generate_store_insights(branch_id="BRANCH_01", city="ho_chi_minh")
        self.assertEqual(insights["status"], "success")
        self.assertIn("menu_engineering", insights)
        self.assertIn("weather_sensitivity", insights)
        self.assertIn("day_of_week_pattern", insights)
        self.assertIn("actionable_recommendations", insights)
        self.assertGreater(len(insights["actionable_recommendations"]), 0)

        # Test trên custom DataFrame rời rạc
        custom_df = pd.DataFrame([
            {"date": f"2026-08-{i:02d}", "dish_id": "D99", "dish_name": "Trà Xanh", "category": "Trà & Trái Cây", "quantity": 50 + i, "revenue": (50 + i) * 30000, "is_weekend": 1 if i % 7 in [5, 6] else 0, "day_of_week": i % 7}
            for i in range(1, 25)
        ])
        custom_dishes = pd.DataFrame([{"id": "D99", "name": "Trà Xanh", "category": "Trà & Trái Cây", "price": 30000}])
        custom_insights = _compute_insights_from_dataframe(custom_df, custom_dishes, {"id": "CUST", "name": "Custom Shop", "type": "tra_sua"}, "da_nang")
        self.assertEqual(custom_insights["status"], "success")
        self.assertEqual(custom_insights["menu_engineering"]["top_stars"][0]["dish_name"], "Trà Xanh")

    # =========================================================================
    # NHÓM 5: RECIPE BOM & PURCHASE RECOMMENDATIONS
    # =========================================================================

    def test_09_purchase_recommendations_workflow(self):
        """Kiểm thử dịch vụ quy đổi công thức & sinh đề xuất mua hàng đi chợ"""
        res = get_purchase_recommendations(branch_id="BRANCH_01")
        self.assertIn("summary", res)
        self.assertIn("recommendations", res)
        self.assertIn("dish_demands", res)
        self.assertGreater(len(res["recommendations"]), 0)
        self.assertGreater(res["summary"]["total_estimated_purchase_cost"], 0)

    # =========================================================================
    # NHÓM 6: FASTAPI ENDPOINTS INTEGRATION TESTING (REST API)
    # =========================================================================

    def test_10_api_branches(self):
        """Kiểm thử API Chi nhánh"""
        resp = self.client.get("/api/branches")
        self.assertEqual(resp.status_code, 200)
        branches = resp.json()
        self.assertIsInstance(branches, list)
        self.assertGreater(len(branches), 0)

    def test_11_api_weather_locations(self):
        """Kiểm thử API Danh sách địa điểm thời tiết"""
        resp = self.client.get("/api/weather/locations")
        self.assertEqual(resp.status_code, 200)
        locations = resp.json()
        self.assertIsInstance(locations, list)
        self.assertGreaterEqual(len(locations), 6)

    def test_12_api_forecast_with_city(self):
        """Kiểm thử API Dự báo nhu cầu tích hợp thời tiết địa phương"""
        resp = self.client.get("/api/forecast?branch_id=BRANCH_01&n_days=5&city=da_nang")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("branches", data)
        self.assertEqual(data["city"], "da_nang")
        first_branch = data["branches"][0]
        self.assertGreater(len(first_branch["dishes"]), 0)
        day1 = first_branch["dishes"][0]["daily_forecasts"][0]
        self.assertIn("weather_condition", day1)
        self.assertIn("weather_desc", day1)
        self.assertIn("expected_demand", day1)

    def test_13_api_insights(self):
        """Kiểm thử API Thấu cảm dữ liệu quán"""
        resp = self.client.get("/api/insights?branch_id=BRANCH_01&city=ha_noi")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("menu_engineering", data)
        self.assertIn("weather_sensitivity", data)
        self.assertIn("actionable_recommendations", data)

    def test_14_api_smart_tag_ingredients(self):
        """Kiểm thử AI Smart Tagging nguyên liệu mới"""
        resp = self.client.post("/api/ingredients/smart-tag", json={
            "names": ["Thịt bò Wagyu A5", "Sữa tươi trân châu", "Cải thìa tươi", "Trà Ô Long Mộc Châu"]
        })
        self.assertEqual(resp.status_code, 200)
        tags = resp.json().get("tags", [])
        self.assertEqual(len(tags), 4)
        self.assertIn("Thịt", tags[0]["suggested_tag"])
        self.assertIn("Sữa", tags[1]["suggested_tag"])
        self.assertIn("Rau", tags[2]["suggested_tag"])
        self.assertIn("Cà phê & Trà", tags[3]["suggested_tag"])

    def test_15_api_solana_status(self):
        """Kiểm thử API kiểm toán chuỗi khối Solana Devnet"""
        resp = self.client.get("/api/solana/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("cluster", data)
        self.assertIn("authority_pubkey", data)


if __name__ == "__main__":
    print("=" * 80)
    print("BẮT ĐẦU CHẠY BỘ TEST UNIT & CHAOS TESTING TOÀN DIỆN CHO FOODFLOW AI")
    print("=" * 80)
    unittest.main(verbosity=2)
