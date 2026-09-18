@echo off
echo ========================================================
echo       FOODFLOW AI - CHUẨN BỊ KHỞI ĐỘNG HỆ THỐNG
echo ========================================================
echo 1. Kiem tra va sinh du lieu F&B (Neu chua co)...
python scripts\generate_data.py

echo.
echo 2. Huan luyen mo hinh XGBoost...
python -m backend.app.forecasting.pipeline

echo.
echo 3. Khoi dong Backend FastAPI tai http://localhost:8000
start "FoodFlow AI Backend" cmd /k "python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload"

echo.
echo 4. Khoi dong Frontend React tai http://localhost:5173
start "FoodFlow AI Frontend" cmd /k "cd frontend && npm.cmd run dev"

echo.
echo ========================================================
echo    FOODFLOW AI DA SAN SANG!
echo    - Frontend : http://localhost:5173
echo    - Backend  : http://localhost:8000
echo    - API Docs : http://localhost:8000/docs
echo ========================================================
pause
