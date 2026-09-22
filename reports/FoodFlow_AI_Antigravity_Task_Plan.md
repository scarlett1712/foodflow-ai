# FoodFlow AI — Plan chi tiết cho Antigravity
**Phạm vi: chỉ 3 mục ưu tiên cao nhất — (1) Tăng độ phức tạp dữ liệu, (2) Chuyển Personalized → Global Model, (3) Thêm Tết Nguyên Đán. Mục GridSearchCV/LazyPredict để sau.**

**Môi trường:** chạy local, chưa cần branch git riêng, chưa cần backup model Personalized cũ (hướng đi sai, bỏ luôn không giữ). Làm tuần tự Task 1 → 2 → 3, vì Task 2 và 3 đều phụ thuộc vào dữ liệu đã sinh lại ở Task 1.

---

## Về chỉ số đánh giá (WAPE) — đọc trước khi làm

```
WAPE = Σ|Thực tế − Dự đoán| / Σ|Thực tế| × 100%
```
Chuẩn ngành cho demand forecasting (thay vì MAPE vì không bị méo bởi ngày bán thấp). Không có ngưỡng tuyệt đối cố định — **tiêu chí thành công là khoảng cách tương đối với baseline**, không phải 1 con số WAPE cụ thể.

**Kết quả hiện tại (trước khi sửa):** Baseline WAPE 5.38%, XGBoost WAPE 5.11% — chỉ cải thiện ~5% tương đối, một số món XGBoost còn THUA baseline. Đây là dấu hiệu dữ liệu quá đơn giản (chỉ 5% nhiễu Gauss thuần túy trong công thức sinh dữ liệu), không phải do sai sót ở model.

**Tiêu chí thành công sau khi sửa (Definition of Done cho cả 3 task):**
- Baseline WAPE tăng lên (dự kiến ~12-20%, vì baseline không bắt được các yếu tố phi tuyến/sự kiện mới thêm vào)
- XGBoost WAPE thấp hơn baseline **tối thiểu 20-30% tương đối** (ví dụ baseline ~15% thì XGBoost nên ~10-12%)
- XGBoost không được thua baseline ở bất kỳ món nào quá 0.5 điểm % (nếu có, đây là dấu hiệu model cần xem lại feature/hyperparameter — ghi log lại để xử lý ở bước GridSearchCV sau)

---

## TASK 1 — Tăng độ phức tạp dữ liệu (`scripts/generate_data.py`)

### Vấn đề hiện tại
```python
qty = base * b_weight * day_mult * hol_mult * trend * weather_mult * noise
noise = random.gauss(1.0, 0.05)   # chỉ 5% nhiễu
```
Công thức gần như tất định — baseline (trung bình cùng thứ 4 tuần gần nhất) nắm bắt gần hết tín hiệu, XGBoost không có "đất diễn".

### Thay đổi cụ thể cần làm

**1.1. Tăng nhiễu ngẫu nhiên cơ bản**
```python
# Từ:
noise = random.gauss(1.0, 0.05)
# Đổi thành:
noise = random.gauss(1.0, 0.12)
```

**1.2. Thêm sự kiện bất thường (event spike) — GẮN VỚI LÝ DO CỤ THỂ**
*(Giả định: chọn cách gắn lý do cụ thể thay vì random spike thuần túy, để sau này khớp được với tính năng `preorders`/AI Variance Evaluator khi demo — nếu bạn muốn đơn giản hơn, có thể bỏ phần "reason" và chỉ giữ hệ số spike)*

```python
import random

EVENT_TYPES = [
    {"name": "don_tiec_dot_xuat", "prob": 0.02, "mult_range": (1.6, 2.3)},   # đơn đặt tiệc đột xuất
    {"name": "su_kien_dia_phuong", "prob": 0.015, "mult_range": (1.4, 1.9)}, # sự kiện gần chi nhánh (concert, thể thao...)
    {"name": "thoi_tiet_cuc_doan", "prob": 0.02, "mult_range": (0.4, 0.65)}, # mưa bão lớn, giảm mạnh
    {"name": "su_co_von_hanh", "prob": 0.01, "mult_range": (0.3, 0.5)},     # sự cố vận hành (thiếu nhân viên, hỏng thiết bị)
]

def get_event_multiplier():
    """Trả về (multiplier, event_name hoặc None) cho 1 ngày"""
    for event in EVENT_TYPES:
        if random.random() < event["prob"]:
            return random.uniform(*event["mult_range"]), event["name"]
    return 1.0, None
```

Áp dụng vào công thức chính, đồng thời **ghi lại `event_name` vào 1 cột mới trong bảng `sales`** (ví dụ `event_flag`) — mục đích: sau này dùng chính cột này để tạo dữ liệu mẫu cho `purchase_history`/AI Variance Evaluator (khi có event, chênh lệch mua hàng thực tế so với dự đoán AI là "có lý do chính đáng", đúng 1 trong các case 🟡/🟢 mà AI Variance Evaluator cần thẩm định).

**1.3. Thêm tương tác phi tuyến giữa các yếu tố** (đây là phần quan trọng nhất để XGBoost thể hiện ưu thế so với baseline tuyến tính):
```python
# Ví dụ: cuối tuần + mưa ảnh hưởng KHÁC với (cuối tuần một mình + mưa một mình cộng lại)
# Tùy loại hình quán (branch profile) mà tương tác này khác nhau
if is_weekend and weather_mult < 1.0:  # cuối tuần mà mưa
    if branch_type == "tra_sua":
        interaction_mult = 0.85   # trà sữa: cuối tuần mưa giảm MẠNH hơn bình thường (khách sinh viên ngại ra ngoài)
    elif branch_type == "am_thuc_truyen_thong":
        interaction_mult = 1.1    # ẩm thực truyền thống: cuối tuần mưa lại TĂNG nhẹ (gia đình thích tụ tập ăn uống trong nhà hàng khi mưa)
    else:
        interaction_mult = 1.0
else:
    interaction_mult = 1.0

qty = base * b_weight * day_mult * hol_mult * trend * weather_mult * event_mult * interaction_mult * noise
```

**1.4. Random seed — CẦN GIỮ CỐ ĐỊNH để tái lập kết quả**
*(Giả định: có, vì cần so sánh trước/sau khi báo cáo, và demo phải cho ra đúng số liệu đã show trong slide)*
```python
random.seed(42)   # đặt ở đầu file, trước khi bắt đầu vòng lặp sinh dữ liệu
```

### Việc cần làm
- [ ] Sửa `noise` từ `gauss(1.0, 0.05)` → `gauss(1.0, 0.12)`
- [ ] Thêm hàm `get_event_multiplier()` với 4 loại sự kiện ở trên
- [ ] Thêm cột `event_flag` vào bảng `sales` khi insert (giá trị: tên event hoặc NULL)
- [ ] Thêm logic tương tác phi tuyến (branch_type × weekend × weather) — cần định nghĩa hệ số riêng cho từng loại hình trong 3 chi nhánh hiện có (Bistro, Trà Sữa, Ẩm Thực Truyền Thống)
- [ ] Thêm `random.seed(42)` đầu file
- [ ] Chạy lại script, xác nhận bảng `sales` có thêm cột `event_flag`, dữ liệu không có giá trị âm/bất thường (âm số lượng bán ra là bug, cần clip về 0 nếu công thức cho ra âm)

---

## TASK 2 — Chuyển Personalized → Global Model

*(Giả định các điểm chưa chốt: KHÔNG giữ code Personalized cũ — thay thế hoàn toàn theo đúng yêu cầu "hướng đi sai, không cần backup". CÓ cập nhật `main.py` nếu endpoint gọi trực tiếp cấu trúc model cũ. Dùng categorical feature NATIVE của XGBoost (`enable_categorical=True`), không one-hot — vì gọn hơn, đúng version XGBoost 2.0+ đã có trong `requirements.txt`, và là cách chuẩn công nghiệp (Walmart M5, Amazon Forecast dùng cách này).*)

### 2.1. Sửa `backend/app/forecasting/features.py`

Thêm `branch_id` và `dish_id` vào `FEATURE_COLUMNS`, đổi dtype sang `category`:

```python
FEATURE_COLUMNS = [
    "branch_id", "dish_id",   # MỚI — categorical, để model học sự khác biệt giữa các chi nhánh/món
    "day_of_week", "day_of_month", "month", "is_weekend", "is_holiday",
    "lag_1", "lag_7", "lag_14", "lag_28",
    "rolling_mean_7", "rolling_mean_14", "rolling_mean_28", "rolling_std_7",
    "event_flag",   # MỚI từ Task 1 — nếu có event thì feature này giúp model học pattern bất thường
]

def prepare_categorical_dtypes(df):
    df["branch_id"] = df["branch_id"].astype("category")
    df["dish_id"] = df["dish_id"].astype("category")
    df["event_flag"] = df["event_flag"].fillna("none").astype("category")
    return df
```

**Quan trọng — sửa hàm build feature:** hiện tại `build_features_for_dish()` đang xử lý riêng từng `(branch, dish)` để tính lag/rolling — **giữ nguyên logic này** (lag/rolling PHẢI tính riêng theo từng chuỗi thời gian của từng branch+dish, không được trộn lẫn), chỉ khác là **sau khi tính xong feature cho tất cả các cặp, gộp lại thành 1 DataFrame lớn duy nhất** trước khi đưa vào train, thay vì train riêng từng cặp.

### 2.2. Sửa `backend/app/forecasting/pipeline.py`

```python
# XÓA vòng lặp cũ:
# for b_id, b_name in branches:
#     for dish_id in dish_ids:
#         model = xgb.XGBRegressor(...)
#         model.fit(X_train, y_train)
#         models_dict[f"{b_id}_{dish_id}"] = model

# THAY BẰNG:
all_features = []
for b_id, b_name in branches:
    for dish_id in dish_ids:
        df_dish = get_raw_series(b_id, dish_id)          # lấy dữ liệu thô như cũ
        df_feat = build_features_for_dish(df_dish)        # tính lag/rolling như cũ, RIÊNG từng chuỗi
        df_feat["branch_id"] = b_id
        df_feat["dish_id"] = dish_id
        all_features.append(df_feat)

df_all = pd.concat(all_features, ignore_index=True)
df_all = prepare_categorical_dtypes(df_all)

train_df = df_all[df_all["date"] < split_date]
test_df  = df_all[df_all["date"] >= split_date]

X_train, y_train = train_df[FEATURE_COLUMNS], train_df["quantity"]
X_test,  y_test  = test_df[FEATURE_COLUMNS],  test_df["quantity"]

model = xgb.XGBRegressor(
    n_estimators=100, max_depth=4, learning_rate=0.07,
    subsample=0.85, colsample_bytree=0.85,
    enable_categorical=True, tree_method="hist",
    random_state=42,
)
model.fit(X_train, y_train)

joblib.dump(model, "saved_models/global_model.joblib")   # 1 FILE DUY NHẤT thay vì 66
```

**Đánh giá WAPE:** tính tổng thể (toàn bộ test set gộp) VÀ tính riêng theo từng `(branch_id, dish_id)` (dùng `groupby` trên `test_df` sau khi có cột `prediction`) — để vẫn giữ được bảng so sánh chi tiết theo món như bản cũ, phục vụ demo/debug.

### 2.3. Sửa `backend/app/forecasting/predictor.py`

- Đổi hàm load model: từ đọc dict `{branch_dish_key: model}` → đọc 1 file `global_model.joblib` duy nhất.
- Hàm predict: khi cần dự đoán cho 1 `(branch_id, dish_id, date)` cụ thể, build đúng feature row (bao gồm `branch_id`, `dish_id` dạng category khớp với categories đã thấy lúc train — **lưu ý: cần lưu lại danh sách categories đã dùng lúc train, ví dụ bằng `df_all["branch_id"].cat.categories`, để xử lý đúng khi có giá trị mới lạ lúc serving**), rồi gọi `model.predict()`.
- Cập nhật lại `VIETNAM_HOLIDAYS` theo Task 3 ở file này luôn (đang bị duplicate với `generate_data.py`).

### 2.4. `backend/app/main.py` — ĐÃ KIỂM TRA, KHÔNG CẦN SỬA

Đã rà soát trực tiếp: `main.py` chỉ import đúng 2 hàm cấp cao từ module forecasting —
```python
from .forecasting.predictor import get_forecast_for_next_days
from .forecasting.pipeline import train_and_evaluate_all
```
Không có chỗ nào trong `main.py` đụng trực tiếp vào cấu trúc `models_dict` bên trong — tách bạch tốt. Nghĩa là **chỉ cần giữ nguyên chữ ký (signature) và schema output của 2 hàm này**, `main.py` sẽ chạy được ngay không cần sửa dòng nào:
- `get_forecast_for_next_days(n_days=7, branch_id=None, db_path=DB_PATH, model_path=MODEL_PATH)` — giữ nguyên tham số đầu vào, và **DataFrame trả về phải giữ đúng các cột hiện có** (đang gồm `date, branch_id, branch_name, dish_id, dish_name, category, quantity, revenue, is_weekend, is_holiday, day_of_week` — xem cụ thể phần cuối hàm để copy đúng danh sách cột output).
- `train_and_evaluate_all()` — không tham số, giữ nguyên.

**Việc cần làm duy nhất ở đây:** trong `predictor.py`, đổi `MODEL_PATH` trỏ sang `saved_models/global_model.joblib` (thay vì `xgboost_models.joblib`), và đổi dòng `models_dict = joblib.load(model_path)` → `model = joblib.load(model_path)` (bỏ việc index theo dict, vì giờ chỉ có 1 model duy nhất) — chỉ sửa nội bộ hàm, chữ ký hàm bên ngoài không đổi.

- [ ] Sau khi hoàn thành Task 2, chạy thử `GET /forecast` (hoặc endpoint tương ứng) qua Swagger UI (`/docs`) để xác nhận response vẫn đúng format cũ.

### Việc cần làm (tóm tắt)
- [ ] `features.py`: thêm `branch_id`, `dish_id`, `event_flag` vào `FEATURE_COLUMNS`, thêm hàm `prepare_categorical_dtypes()`
- [ ] `pipeline.py`: gộp toàn bộ feature các cặp (branch, dish) thành 1 DataFrame, train 1 model Global duy nhất với `enable_categorical=True`
- [ ] `pipeline.py`: xóa toàn bộ code Personalized cũ (vòng lặp train riêng, dict 66 model)
- [ ] `predictor.py`: đổi logic load/predict sang model Global, lưu lại category mapping dùng lúc train
- [ ] `main.py`: rà soát và sửa các endpoint nếu cần
- [ ] Chạy lại, so sánh WAPE tổng thể + WAPE theo từng món với kết quả cũ (5.38%/5.11%), ghi log lại cả 2 để có số liệu "trước/sau" dùng khi pitch

---

## TASK 3 — Thêm Tết Nguyên Đán

*(Đã chốt theo yêu cầu: dùng CẢ hard-code lẫn thư viện `lunarcalendar` — hard-code cho 2025/2026 để chắc chắn đúng ngay lập tức, `lunarcalendar` để tự tính cho các năm khác nếu sau này mở rộng dữ liệu. Đã tham khảo báo cáo Tết 2026 bạn gửi, có kiểm chứng lại nguồn — xem lưu ý quan trọng ở Mục 3.2.)*

### 3.1. Cài đặt thư viện & ngày Tết chính xác (đã verify bằng code thật, khớp 100%)

```bash
pip install lunarcalendar
```

Đã test trực tiếp, `lunarcalendar` cho ra đúng kết quả khớp với tra cứu thực tế:
```python
from lunarcalendar import Converter, Lunar
Converter.Lunar2Solar(Lunar(2025, 1, 1, isleap=False))  # → 2025-01-29 ✓
Converter.Lunar2Solar(Lunar(2026, 1, 1, isleap=False))  # → 2026-02-17 ✓
```

- Tết Nguyên Đán 2025 (Ất Tỵ): **29/01/2025**
- Tết Nguyên Đán 2026 (Bính Ngọ): **17/02/2026**

### 3.2. ⚠️ Lưu ý quan trọng — về báo cáo Tết bạn gửi

Đã tra lại đúng bài báo Tuổi Trẻ gốc mà báo cáo trích dẫn. **Xu hướng chung là đúng và có thật** (nhu cầu tăng rõ rệt trước Tết nhờ tiệc tất niên/tổng kết, một số nhà hàng/TTTM đông nghẹt khách đầu năm mới) — nhưng **không tìm thấy đúng 2 con số "35% trong tháng trước Tết" và "50-60% trong 10 ngày cao điểm"** trong bài báo thật. Bài gốc chỉ ghi nhận: 1 khách sạn tại TP.HCM có lượng khách tăng **hơn 20%** từ tháng 12/2025 (không phải 35%), nhờ tiệc tất niên/hội nghị tổng kết. Có thể con số 35%/50-60% trong báo cáo đến từ 1 nguồn khác không xác định được, nên **plan này KHÔNG dùng nguyên các con số đó**, thay vào đó dùng hệ số ước lượng thận trọng hơn, ghi rõ là "có thể điều chỉnh" chứ không khẳng định là số liệu chính xác tuyệt đối.

### 3.3. Thiết kế — tách bạch 2 mục đích khác nhau (điểm cải tiến quan trọng nhất so với bản plan trước)

Báo cáo bạn gửi có 1 gợi ý rất đúng, cần áp dụng: **đừng nhồi cứng % tác động vào feature dùng để dự đoán — chỉ nên hard-code % khi SINH dữ liệu giả lập (ground truth), còn khi làm feature cho model học thì chỉ nên đưa "nhãn giai đoạn" (is_pre_tet, is_tat_nien...) và để model TỰ HỌC mức độ tác động từ chính dữ liệu.** Đây là 2 việc khác nhau, cần 2 hàm riêng:

**(A) Dùng khi SINH dữ liệu (`generate_data.py`) — cần con số cụ thể để tạo ra số liệu giả lập:**
```python
def get_tet_synthetic_multiplier(date, tet_date):
    """CHỈ dùng trong generate_data.py để tạo ra ground-truth qty.
    Các hệ số dưới đây là ƯỚC LƯỢNG THẬN TRỌNG dựa trên xu hướng đã xác nhận
    (tất niên đẩy nhu cầu tăng rõ trước Tết, nhiều quán đóng/giảm giờ đúng dịp Tết),
    KHÔNG phải số liệu tuyệt đối — có thể chỉnh lại param_grid này sau khi xem kết quả WAPE.
    """
    delta = (date - tet_date).days
    if -30 <= delta <= -21:   return 1.10   # bắt đầu tăng nhẹ
    elif -21 <= delta <= -14: return 1.20   # tất niên bắt đầu rõ
    elif -14 <= delta <= -3:  return 1.45   # cao điểm tất niên
    elif -2 <= delta <= -1:   return 1.15   # 29-30 Tết, tùy loại hình (xem ghi chú bên dưới)
    elif delta == 0:          return 0.30   # mùng 1 — giả định quán ĐÓNG CỬA/giảm mạnh (xem lưu ý)
    elif 1 <= delta <= 2:     return 0.55   # mùng 2-3, dần phục hồi
    elif 3 <= delta <= 4:     return 0.80   # mùng 4-5, tăng dần
    elif 5 <= delta <= 7:     return 0.95   # gần bình thường
    else:                     return 1.0
```

**(B) Dùng làm FEATURE cho model học (`features.py`, dùng chung cho cả train và predict) — chỉ đưa nhãn, KHÔNG đưa số nhân:**
```python
def add_tet_features(df, tet_date):
    delta = (df["date"] - tet_date).dt.days
    df["days_to_tet"] = delta
    df["days_to_tet_abs"] = delta.abs()
    df["is_pre_tet"] = ((delta >= -30) & (delta <= -1)).astype(int)
    df["is_tat_nien_period"] = ((delta >= -21) & (delta <= -1)).astype(int)
    df["is_tet"] = ((delta >= 0) & (delta <= 2)).astype(int)
    df["is_post_tet"] = ((delta >= 3) & (delta <= 7)).astype(int)
    return df
```
→ 6 cột này được **thêm vào `FEATURE_COLUMNS`** (cùng với `branch_id`/`dish_id` ở Task 2) — XGBoost sẽ tự học ra mức độ ảnh hưởng thật của từng giai đoạn **từ chính dữ liệu đã sinh ở phần (A)**, đúng tinh thần "để model tự học, đừng hard-code vào feature" mà báo cáo đã gợi ý.

### 3.4. ⚠️ Cần team quyết định — quán trong dữ liệu có ĐÓNG CỬA dịp Tết không?

Tra cứu thêm cho thấy thực tế có **2 kịch bản trái ngược** tùy loại hình: (1) quán ăn nhỏ/gia đình thường đóng cửa mùng 1-3 → nhu cầu giảm mạnh đúng như hệ số `0.30` ở trên; (2) quán ở khu vực trung tâm/TTTM/nhà hàng lớn thường **mở xuyên Tết** và ghi nhận đông khách bất thường (ít lựa chọn hơn nên khách dồn vào) — nếu vậy hệ số ngày mùng 1 phải là **tăng**, không phải giảm. Plan này **mặc định cả 3 chi nhánh demo đều mở cửa xuyên Tết** (đơn giản hơn cho MVP, và câu chuyện "dự đoán chính xác lúc cao điểm bất thường" demo ấn tượng hơn) — nếu team muốn mô phỏng đúng kịch bản "đóng cửa", cần thêm cờ `is_open_during_tet` riêng theo từng `branch_id`. Antigravity: hỏi lại team trước khi code phần này nếu chưa rõ, mặc định dùng kịch bản "mở cửa xuyên Tết" nếu không có phản hồi.

### 3.5. Áp dụng vào cả 2 nơi bị duplicate

**`scripts/generate_data.py`:** dùng `get_tet_synthetic_multiplier()` nhân vào công thức chính ở Task 1.3.

**`backend/app/forecasting/features.py`:** thêm `add_tet_features()`, đưa 6 cột mới vào `FEATURE_COLUMNS` — dùng chung cho cả lúc train (`pipeline.py`) và lúc dự đoán tương lai (`predictor.py`), đảm bảo nhất quán.

**Khuyến nghị kỹ thuật:** tách `TET_DATES` (hard-code 2025/2026 + fallback tính bằng `lunarcalendar` cho năm khác), `VIETNAM_HOLIDAYS`, `get_tet_synthetic_multiplier()`, `add_tet_features()` ra **1 file dùng chung** `backend/app/forecasting/vn_calendar.py`, import vào cả `generate_data.py` và `features.py`/`predictor.py` — tránh lặp lại logic ở nhiều nơi như lỗi cũ.

```python
# backend/app/forecasting/vn_calendar.py — khung sườn
from lunarcalendar import Converter, Lunar
import pandas as pd

TET_DATES = {
    2025: pd.Timestamp("2025-01-29"),   # hard-code, đã verify
    2026: pd.Timestamp("2026-02-17"),   # hard-code, đã verify
}

def get_tet_date(year: int) -> pd.Timestamp:
    """Ưu tiên tra bảng hard-code (đã verify chắc chắn đúng); 
    nếu năm không có trong bảng, tự tính bằng lunarcalendar."""
    if year in TET_DATES:
        return TET_DATES[year]
    solar = Converter.Lunar2Solar(Lunar(year, 1, 1, isleap=False))
    return pd.Timestamp(solar.year, solar.month, solar.day)
```

### Việc cần làm
- [ ] `pip install lunarcalendar`, thêm vào `requirements.txt`
- [ ] Tạo file mới `backend/app/forecasting/vn_calendar.py` — gồm `TET_DATES`, `get_tet_date()`, `VIETNAM_HOLIDAYS` (copy từ code cũ), `get_tet_synthetic_multiplier()`, `add_tet_features()`
- [ ] Xác nhận với team kịch bản Mục 3.4 (mở cửa hay đóng cửa xuyên Tết) trước khi code, mặc định "mở cửa" nếu không có phản hồi
- [ ] Sửa `scripts/generate_data.py`: import `get_tet_synthetic_multiplier()` từ `vn_calendar.py`, áp dụng vào công thức sinh dữ liệu
- [ ] Sửa `backend/app/forecasting/features.py`: import `add_tet_features()` từ `vn_calendar.py`, gọi trong `build_features_for_dish()`, thêm 6 cột Tết mới vào `FEATURE_COLUMNS`
- [ ] Sửa `backend/app/forecasting/predictor.py`: xóa `VIETNAM_HOLIDAYS` hard-code cũ trong file này, import từ `vn_calendar.py` thay thế (đảm bảo lúc dự đoán tương lai cũng tính đúng `days_to_tet`/`is_tet`... như lúc train)
- [ ] Chạy lại `generate_data.py`, kiểm tra dữ liệu quanh 29/01/2025 và 17/02/2026 có thể hiện đúng pattern tăng trước/giảm trong/phục hồi sau Tết không (in thử ra vài dòng quanh các ngày đó để mắt kiểm tra trực quan)

---

## Trình tự chạy & kiểm tra cuối cùng

1. Chạy `scripts/generate_data.py` (đã áp dụng cả Task 1 + Task 3) → tạo lại `foodflow.db`
2. Chạy `backend/app/forecasting/pipeline.py` (đã áp dụng Task 2 — Global Model) → train, in ra WAPE tổng thể + theo từng món
3. So sánh với kết quả cũ:

| | Trước (Personalized, data cũ) | Sau (Global Model, data mới) |
|---|---|---|
| Baseline WAPE | 5.38% | ??? (dự kiến tăng, ~12-20%) |
| Model WAPE | 5.11% | ??? (mục tiêu: thấp hơn baseline 20-30%) |
| Số model lưu | 66 file | 1 file (`global_model.joblib`) |

4. Ghi lại bảng này — đây chính là bằng chứng "trước/sau" mạnh nhất để đưa vào slide pitch, cho thấy team đã tự phát hiện và sửa vấn đề kỹ thuật, không phải chỉ nộp bản đầu tiên.

---

*Sau khi hoàn thành 3 task này, quay lại Mục 4 (GridSearchCV với TimeSeriesSplit) và Mục 5 (LazyPredict sanity-check) đã nêu ở file Brainstorm Plan.*
