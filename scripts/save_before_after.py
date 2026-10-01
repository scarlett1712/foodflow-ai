"""
scripts/save_before_after.py
Luu ket qua forecast truoc/sau khi fix de so sanh.
Usage:
  python scripts/save_before_after.py before
  python scripts/save_before_after.py after
  python scripts/save_before_after.py compare
"""

import sys
import os
import json
import time
import logging

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(name)s | %(message)s', datefmt='%H:%M:%S')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

def save_snapshot(label):
    from backend.app.forecasting.predictor import _execute_raw_forecast, _FORECAST_CACHE, DB_PATH, MODEL_PATH
    from backend.app.forecasting.weather_service import _WEATHER_CACHE
    
    # Clear caches
    _FORECAST_CACHE.clear()
    _WEATHER_CACHE.clear()
    
    print(f"Running forecast for snapshot '{label}'...")
    t0 = time.time()
    result = _execute_raw_forecast(n_days=7, branch_id="BRANCH_01", db_path=DB_PATH, model_path=MODEL_PATH, city="ho_chi_minh")
    elapsed = time.time() - t0
    print(f"Done in {elapsed:.3f}s")
    
    filepath = os.path.join(SCRIPTS_DIR, f"{label}.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Saved to {filepath}")

def compare():
    before_path = os.path.join(SCRIPTS_DIR, "before.json")
    after_path = os.path.join(SCRIPTS_DIR, "after.json")
    
    if not os.path.exists(before_path) or not os.path.exists(after_path):
        print("ERROR: Need both before.json and after.json")
        return
    
    with open(before_path, 'r', encoding='utf-8') as f:
        before = json.load(f)
    with open(after_path, 'r', encoding='utf-8') as f:
        after = json.load(f)
    
    # Compare dish by dish
    b_dishes = {d["dish_id"]: d for b in before["branches"] for d in b["dishes"]}
    a_dishes = {d["dish_id"]: d for b in after["branches"] for d in b["dishes"]}
    
    total_checks = 0
    mismatches = 0
    max_diff = 0.0
    
    for dish_id in sorted(b_dishes.keys()):
        if dish_id not in a_dishes:
            print(f"  MISSING in after: {dish_id}")
            mismatches += 1
            continue
        
        b_daily = b_dishes[dish_id]["daily_forecasts"]
        a_daily = a_dishes[dish_id]["daily_forecasts"]
        
        for j, (bd, ad) in enumerate(zip(b_daily, a_daily)):
            total_checks += 1
            b_xgb = bd["xgb_quantity"]
            a_xgb = ad["xgb_quantity"]
            diff = abs(b_xgb - a_xgb)
            if diff > max_diff:
                max_diff = diff
            if diff > 0:
                mismatches += 1
                print(f"  DIFF {dish_id} day {bd['date']}: before={b_xgb} after={a_xgb} (diff={diff})")
    
    print(f"\n{'='*60}")
    print(f"  COMPARISON RESULT")
    print(f"  Total checks: {total_checks}")
    print(f"  Mismatches: {mismatches}")
    print(f"  Max absolute diff: {max_diff}")
    if mismatches == 0:
        print(f"  RESULT: IDENTICAL - safe to proceed")
    elif max_diff <= 1:
        print(f"  RESULT: MINOR ROUNDING DIFFS ONLY - acceptable")
    else:
        print(f"  RESULT: SIGNIFICANT DIFFS - investigate!")
    print(f"{'='*60}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/save_before_after.py [before|after|compare]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == "before":
        save_snapshot("before")
    elif cmd == "after":
        save_snapshot("after")
    elif cmd == "compare":
        compare()
    else:
        print(f"Unknown command: {cmd}")
