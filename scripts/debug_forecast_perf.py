"""
scripts/debug_forecast_perf.py
Standalone perf diagnostic - does NOT modify existing code.
Usage:  python scripts/debug_forecast_perf.py
"""

import sys
import os
import time
import logging

# Fix Windows encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Setup logging BEFORE importing forecast modules
# This is the KEY fix - without this, _log.info() messages are swallowed
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(os.path.dirname(__file__), "perf_debug.log"),
            mode='w',
            encoding='utf-8'
        ),
    ]
)

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

print("=" * 70)
print("  FoodFlow AI - Forecast Performance Diagnostic")
print("=" * 70)
print(f"  Project root: {PROJECT_ROOT}")
print(f"  Python: {sys.version}")
print()

# Import AFTER logging is configured
print("[1/5] Importing modules...")
t_import_start = time.time()

from backend.app.forecasting.predictor import (
    _execute_raw_forecast,
    get_forecast_for_next_days,
    _FORECAST_CACHE,
    CACHE_TTL,
    DB_PATH,
    MODEL_PATH,
)
from backend.app.forecasting.weather_service import (
    _WEATHER_CACHE,
    WEATHER_CACHE_TTL,
)

t_import = time.time() - t_import_start
print(f"    OK Import done in {t_import:.3f}s")
print(f"    DB_PATH: {DB_PATH}")
print(f"    MODEL_PATH: {MODEL_PATH}")
print(f"    DB exists: {os.path.exists(DB_PATH)}")
print(f"    Model exists: {os.path.exists(MODEL_PATH)}")
print()

# Clear all caches to measure REAL compute time
print("[2/5] Clearing forecast cache + weather cache...")
_FORECAST_CACHE.clear()
_WEATHER_CACHE.clear()
print(f"    OK Caches cleared")
print()

# Call _execute_raw_forecast() DIRECTLY (bypass cache)
# The [PERF] logs from predictor.py will print to console here
print("[3/5] Calling _execute_raw_forecast() DIRECTLY (no cache)...")
print("    branch_id=BRANCH_01, n_days=7, city=ho_chi_minh")
print("-" * 70)

t1 = time.time()
result = _execute_raw_forecast(
    n_days=7,
    branch_id="BRANCH_01",
    db_path=DB_PATH,
    model_path=MODEL_PATH,
    city="ho_chi_minh"
)
t1_elapsed = time.time() - t1

print("-" * 70)
print(f"    Total _execute_raw_forecast(): {t1_elapsed:.3f}s")

if result and "branches" in result:
    for b in result["branches"]:
        n_dishes = len(b.get("dishes", []))
        total_forecasts = sum(len(d.get("daily_forecasts", [])) for d in b.get("dishes", []))
        print(f"    Branch {b['branch_id']}: {n_dishes} dishes, {total_forecasts} day-forecasts")
print()

# Call with cache API - round 1 (compute + store cache)
print("[4/5] Calling get_forecast_for_next_days() ROUND 1 (compute + cache)...")
_FORECAST_CACHE.clear()

t2 = time.time()
result2 = get_forecast_for_next_days(
    n_days=7,
    branch_id="BRANCH_01",
    city="ho_chi_minh"
)
t2_elapsed = time.time() - t2
print(f"    Round 1 (fresh compute): {t2_elapsed:.3f}s")
print(f"    Cache entries after: {len(_FORECAST_CACHE)}")
print()

# Call round 2 - must hit cache, near 0s
print("[5/5] Calling get_forecast_for_next_days() ROUND 2 (must hit cache)...")
t3 = time.time()
result3 = get_forecast_for_next_days(
    n_days=7,
    branch_id="BRANCH_01",
    city="ho_chi_minh"
)
t3_elapsed = time.time() - t3
print(f"    Round 2 (cache hit): {t3_elapsed:.6f}s")
print()

# Summary
print("=" * 70)
print("  PERFORMANCE SUMMARY")
print("=" * 70)
print(f"  Import modules:            {t_import:.3f}s")
print(f"  Forecast (no cache):       {t1_elapsed:.3f}s")
print(f"  Forecast (cache API r1):   {t2_elapsed:.3f}s")
print(f"  Forecast (cache API r2):   {t3_elapsed:.6f}s")
if t3_elapsed > 0:
    print(f"  Cache speedup:             {t2_elapsed / t3_elapsed:.0f}x faster")
print()

if t1_elapsed > 10:
    print("  [WARN] Forecast > 10s - XGBoost predict loop needs vectorization!")
    print("     Check [PERF] logs above to see which step is slowest:")
    print("     - DB queries > 5s  -> SQL index needed")
    print("     - Weather API > 5s -> Weather cache not working")
    print("     - Prediction loop > 5s -> Need batch predict instead of 154 loops")
elif t1_elapsed > 3:
    print("  [OK] Forecast 3-10s - acceptable for first call, cache handles the rest.")
else:
    print("  [GOOD] Forecast < 3s - performance is fine!")

print()
log_path = os.path.join(os.path.dirname(__file__), "perf_debug.log")
print(f"  Log saved to: {log_path}")
print("=" * 70)
