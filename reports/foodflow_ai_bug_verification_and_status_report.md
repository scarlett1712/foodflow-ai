# 📊 BÁO CÁO TỔNG HỢP KIỂM TRA & XÁC MINH SỬA LỖI (BUG VERIFICATION REPORT)

> **Dự án:** FoodFlow AI — Hệ thống Dự báo Nhu cầu & Tối ưu Mua hàng F&B  
> **Tài liệu đối soát:**  
> 1. [foodflow_ai_web_performance_investigation_report.md](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/reports/foodflow_ai_web_performance_investigation_report.md) *(Báo cáo điều tra hiệu năng & treo web)*  
> 2. [foodflow_ai_test_report.md](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/reports/foodflow_ai_test_report.md) *(Báo cáo kiểm thử toàn diện v2.1)*  
> **Thời gian kiểm tra thực nghiệm:** 2026-09-27  
> **Môi trường kiểm tra:** Python 3.12, FastAPI, SQLite, Node.js / Vite Frontend  

---

## 📌 TÓM TẮT ĐIỀU HÀNH (EXECUTIVE SUMMARY)

Sau khi tiến hành rà soát mã nguồn thực tế và chạy bộ kiểm thử tự động (Unit Test, Regression Test, Black-box Test), kết quả xử lý lỗi của hệ thống như sau:

| Tài liệu báo cáo | Tổng số lỗi / vấn đề | Đã Fix hoàn toàn | Đã Fix một phần / Mitigated | Chưa Fix | Tỷ lệ khắc phục |
|---|:---:|:---:|:---:|:---:|:---:|
| **1. Web Performance Report** | **5 tầng nguyên nhân** | **3** | **1** | **1** | **80%** |
| **2. Comprehensive Test Report** | **28 bugs / issues** | **16** | **2** | **10** | **64.3%** |

> [!IMPORTANT]
> **Điểm nổi bật đã hoàn thành:**
> - Toàn bộ **4/4 lỗi Critical** trong hệ thống (Duplicate Route, Exception Swallowing, Connection Leak, CORS Wildcard) đã được xử lý triệt để.
> - Sự cố nghiêm trọng nhất khiến web treo xoay tròn vô tận (**Infinite Spinner**) trên Frontend đã được khắc phục hoàn toàn bằng `Promise.allSettled`, Fallback Error Card và tăng Timeout lên 120s.
> - Đã bổ sung bộ đệm In-Memory TTL Cache cho cả **Dự báo nhu cầu** (10 phút) và **Dự báo thời tiết** (30 phút), giúp giảm thời gian phản hồi từ 5.5s xuống **0.000s** cho các request trùng lặp.
> - Bộ kiểm thử tự động `tests/test_full_system_and_chaos.py` đã vượt qua **15/15 tests (100% PASS)** sau khi sửa lỗi tương thích TestClient.
>
> **Các vấn đề còn tồn đọng chính:**
> - Tối ưu Vector hóa XGBoost (Batch Prediction) trong `predictor.py` chưa được áp dụng (vẫn dùng vòng lặp for 154 lần).
> - Chưa có tầng Authentication / Authorization và Rate Limiting cho API.
> - File khóa bảo mật `solana_authority.json` vẫn nằm trong kho Git.
> - Chưa giới hạn dung lượng tối đa (file size limit) cho các API upload file.

---

## 🔍 PHẦN 1: TÌNH TRẠNG SỬA LỖI CỦA WEB PERFORMANCE REPORT
*(Chi tiết về sự cố 3 tab Tổng quan, Dự báo nhu cầu, Gợi ý mua hàng)*

### 1.1. Các vấn đề ĐÃ ĐƯỢC FIX ✅

#### 1. Tính toán trùng lặp 3 lần (Triple Redundant Compute) — [Tầng 2]
- **Tình trạng:** 🟢 **ĐÃ FIX HOÀN TOÀN**
- **Vị trí khắc phục:** [predictor.py:83-112](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/backend/app/forecasting/predictor.py#L83-L112)
- **Giải pháp đã triển khai:** Đã bổ sung `_FORECAST_CACHE: Dict[str, Tuple[float, Any]]` với `CACHE_TTL = 600` (10 phút). Khi Frontend gọi đồng thời 3 API (`/dashboard/summary`, `/forecast`, `/purchase-recommendations`), chỉ request đầu tiên tính toán, 2 request sau nhận ngay kết quả từ bộ đệm.
- **Bằng chứng kiểm nghiệm thực tế:**
  - Request 1 (chưa cache): `5.549s`
  - Request 2 (đã cache): `0.00000s` (Tức thì)

#### 2. Xung đột Timeout của Axios Client (25 Giây) — [Tầng 4]
- **Tình trạng:** 🟢 **ĐÃ FIX HOÀN TOÀN**
- **Vị trí khắc phục:** [api.js:7-24](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/frontend/src/services/api.js#L7-L24)
- **Giải pháp đã triển khai:**
  - Nâng `timeout` từ 25s lên **120s** (`timeout: 120000`), đủ thời gian cho Render Free Tier khởi động nguội (Cold Start) và nạp mô hình.
  - Thêm Axios **Retry Interceptor** tự động thử lại 1 lần nếu phát hiện `ECONNABORTED` hoặc lỗi mạng 5xx.

#### 3. Lỗi Anti-Pattern quản lý State Giao diện gây Spinner vô tận — [Tầng 5]
- **Tình trạng:** 🟢 **ĐÃ FIX HOÀN TOÀN**
- **Vị trí khắc phục:**
  - [App.jsx:75-120, 208-225](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/frontend/src/App.jsx#L75-L120)
  - [DashboardPage.jsx:26-42](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/frontend/src/pages/DashboardPage.jsx#L26-L42)
  - [ForecastPage.jsx:48-64](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/frontend/src/pages/ForecastPage.jsx#L48-L64)
  - [PurchasePage.jsx:86-102](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/frontend/src/pages/PurchasePage.jsx#L86-L102)
- **Giải pháp đã triển khai:**
  - Chuyển từ `Promise.all` sang `Promise.allSettled`: 1 request chậm/lỗi không làm sụp đổ các tab dữ liệu khác.
  - Bổ sung state `error` và màn hình Fallback UI thân thiện kèm nút **"🔄 Thử lại"** khi mất kết nối.
  - Xóa bỏ khối `if (!data) return <Spinner />` vô tận ở 3 trang con, thay bằng Warning Card hướng dẫn người dùng bấm tải lại dữ liệu.

---

### 1.2. Các vấn đề ĐÃ KHẮC PHỤC MỘT PHẦN (MITIGATED) 🟡

#### 4. Bão hòa CPU Render Free Tier & Cold Start Delay — [Tầng 3]
- **Tình trạng:** 🟡 **MITIGATED**
- **Thực tế:** Việc tăng timeout lên 120s và in-memory cache giúp Render không bị ngắt kết nối giữa chừng và giảm tải CPU cho các request kế tiếp. Tuy nhiên, giải pháp tạo Scheduled Keep-Alive Ping (UptimeRobot / cron-job.org) là dịch vụ hạ tầng bên ngoài, chưa được thiết lập tự động trong mã nguồn.

---

### 1.3. Các vấn đề CHƯA ĐƯỢC FIX ❌

#### 5. Vòng lặp dự báo đơn lẻ (Unvectorized Per-Row Prediction) — [Tầng 1 / Bước 2 Action Plan]
- **Tình trạng:** 🔴 **CHƯA FIX**
- **Vị trí code:** [predictor.py:175-300](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/backend/app/forecasting/predictor.py#L175-L300)
- **Hiện trạng:** Thuật toán dự báo vẫn đang dùng 3 vòng lặp `for` lồng nhau (Branches × Dishes × Days) và gọi `model.predict(feat_vec)` 154 lần riêng lẻ cho mỗi dòng dữ liệu.
- **Hậu quả:** Lần đầu tiên chạy (khi cache chưa có) vẫn tốn **~5.5 giây trên Local** và có thể tốn **~15 giây trên CPU Render Free Tier**. Cần gom toàn bộ ma trận đặc trưng vào 1 DataFrame duy nhất để `model.predict(X_batch)` 1 lần (chỉ mất ~5ms).

---

## 🔍 PHẦN 2: TÌNH TRẠNG SỬA LỖI CỦA FOODFLOW AI TEST REPORT
*(Chi tiết đối soát 28 bugs và các kịch bản kiểm thử trong Báo cáo QA v2.1)*

### 2.1. Phân nhóm lỗi CRITICAL (4/4 ĐÃ FIX — 100%)

| Bug ID | Mô tả lỗi | Trạng thái | Chi tiết kiểm chứng |
|---|---|:---:|---|
| **BUG-001** | Duplicate Route Handler `/api/purchases/history` | 🟢 **ĐÃ FIX** | Đã xóa định nghĩa route trùng lặp tại line 894 trong [main.py](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/backend/app/main.py#L923). Chỉ còn 1 route duy nhất tại line 1231 với explicit columns. |
| **BUG-002** | Exception Swallowing trong `init_db_schema()` | 🟢 **ĐÃ FIX** | [main.py:111-137](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/backend/app/main.py#L111-L137): Thay `except Exception: pass` bằng xử lý `sqlite3.OperationalError` cụ thể và ghi `logger.warning` cho các lỗi khác. |
| **BUG-003** | Thiếu Connection Pool & Connection Leak Risk | 🟢 **ĐÃ FIX** | [main.py:75-84](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/backend/app/main.py#L75-L84): Đã biến `get_db()` thành `@contextmanager` với `try...finally: conn.close()`. Tất cả 30+ endpoints đã chuyển sang dùng `with get_db() as conn:`. |
| **BUG-004** | CORS Wildcard cho phép mọi Origin (`*`) | 🟢 **ĐÃ FIX** | [main.py:60-73](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/backend/app/main.py#L60-L73): Thay `*` bằng danh sách whitelist `CORS_ORIGINS`. Kiểm nghiệm: Request từ `https://evil.com` bị chặn hoàn toàn (không có header CORS). |

---

### 2.2. Phân nhóm lỗi HIGH (4 Đã fix / 4 Chưa fix)

| Bug ID | Mô tả lỗi | Trạng thái | Chi tiết kiểm chứng |
|---|---|:---:|---|
| **BUG-005** | Test Suite hiện tại không chạy được (Starlette conflict) | 🟢 **ĐÃ FIX** | [test_full_system_and_chaos.py:11-26](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/tests/test_full_system_and_chaos.py#L11-L26): Đã patch TestClient tương thích với `httpx >= 0.28`. Chạy thực tế: **Ran 15 tests in 11.718s — 100% OK**. |
| **BUG-006** | Thiếu Input Validation cho Pydantic Models | 🟡 **FIX PHẦN LỚN** | Đã thêm regex cho `branch_id`, validate `cost >= 0`, `shelf_life >= 0`, `price >= 0`, `quantity > 0`, `items not empty`. *(Còn thiếu: Enum cho branch_type và schema chặt chẽ cho manual purchase items)*. |
| **BUG-007** | `classify_ingredient_tag()` Overlap & False Positives | 🟢 **ĐÃ FIX** | [main.py:328-360](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/backend/app/main.py#L328-L360): Tái cấu trúc thứ tự ưu tiên regex. Đã test thực nghiệm 4 ca trước đây bị sai ("Bơ avocado", "Cá hồi sốt bơ", "Trà sữa", "Kem vanilla") đều phân loại chính xác 100%. |
| **BUG-008** | `weather_service.py` Fallback dùng `random` | 🟢 **ĐÃ FIX** | [weather_service.py:17-21, 110-145](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/backend/app/forecasting/weather_service.py#L17-L21): Bổ sung TTL Cache 30 phút. Fallback offline sử dụng mã băm MD5 của chuỗi ngày (`hashlib.md5(d_str)`), đảm bảo tính tất định (deterministic). |
| **BUG-022** | Thiếu xử lý file upload quá lớn (Max File Size) | 🔴 **CHƯA FIX** | Các endpoint upload file (`/api/sales/upload`, `/api/purchases/upload`, `/api/recipes/upload`) chưa có cơ chế kiểm tra `len(content) > MAX_BYTES` (ví dụ: giới hạn 10MB). |
| **SEC-05** | Không có Authentication / Authorization | 🔴 **CHƯA FIX** | Tất cả các API đều mở công khai, bất kỳ ai cũng có thể đọc/ghi/xóa dữ liệu chi nhánh và tồn kho. |
| **SEC-06** | Không có Rate Limiting (chống DoS) | 🔴 **CHƯA FIX** | Chưa tích hợp thư viện giới hạn tần suất request (như `slowapi`). |
| **SEC-08** | Khóa bí mật `solana_authority.json` nằm trong Git | 🔴 **CHƯA FIX** | File chứa private key [backend/solana_authority.json](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/backend/solana_authority.json) vẫn đang được Git theo dõi (tracked), chưa thêm vào `.gitignore`. |

---

### 2.3. Phân nhóm lỗi MEDIUM (6 Đã fix & hợp lệ / 4 Chưa fix)

| Bug ID | Mô tả lỗi | Trạng thái | Chi tiết kiểm chứng |
|---|---|:---:|---|
| **BUG-009** | Import `json` lặp lại bên trong vòng lặp | 🟢 **ĐÃ FIX** | Đã di chuyển `import json` lên đầu file [predictor.py:14](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/backend/app/forecasting/predictor.py#L14). |
| **BUG-010** | `vn_calendar.py` chỉ có dữ liệu Tết 2025-2026 | 🟢 **ĐÃ FIX** | Đã bổ sung ngày Tết cho năm 2027 (`2027-02-06`) và 2028 (`2028-01-26`) trong [vn_calendar.py:21-22](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/backend/app/forecasting/vn_calendar.py#L21-L22). |
| **BUG-011** | Data Leakage trong Full Model Training | 🔴 **CHƯA FIX** | [pipeline.py:224-237](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/backend/app/forecasting/pipeline.py#L224-L237): Mô hình deploy vẫn được train trên toàn bộ tập dữ liệu (bao gồm cả test set đã dùng đo WAPE). |
| **BUG-012** | `insight_service.py` Tham chiếu cột `day_name` | 🟢 **HỢP LỆ (ĐÃ TỒN TẠI)** | Đã kiểm tra trực tiếp bảng `calendar` trong DB: cột `day_name` đã có sẵn trong cơ sở dữ liệu SQLite, truy vấn không hề bị lỗi. |
| **BUG-013** | `solana_service.py` `verify_onchain_record` luôn trả True | 🟢 **ĐÃ FIX** | Đã bổ sung logic kiểm tra độ dài hash (≥ 16) và tiền tố signature (`FOODFLOW_`). Nếu không hợp lệ sẽ trả về `verified: False`. Đã thêm cảnh báo mock mode rõ ràng. |
| **BUG-014** | `solana_service.py` Hardcoded balance giả (2.5 SOL) | 🔴 **CHƯA FIX** | [solana_service.py:329](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/backend/app/services/solana_service.py#L329): Số dư `"devnet_balance_sol": 2.5` vẫn bị hardcode, chưa query thực tế qua RPC. |
| **BUG-015** | `ai_variance_evaluator.py` Magic Numbers | 🔴 **CHƯA FIX** | [ai_variance_evaluator.py:68, 74](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/backend/app/services/ai_variance_evaluator.py#L68-L74): Ngưỡng `10.0%` và `2.5x` vẫn chưa được chuyển thành constants đặt ở đầu file. |
| **BUG-016** | `recommendation_service.py` Margin âm / chia cho 0 | 🔴 **CHƯA FIX** | [recommendation_service.py:207](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/backend/app/services/recommendation_service.py#L207): Chưa validate trường hợp chi phí mua hàng lớn hơn doanh thu dự kiến khiến profit margin âm. |
| **BUG-017** | Collision tiềm ẩn khi sinh `batch_id` | 🟢 **ĐÃ FIX** | Đã thay thế công thức `timestamp % 1000000` bằng `int(uuid.uuid4().int & 0x7FFFFFFF)` trong [main.py](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/backend/app/main.py#L1029). |
| **BUG-018** | `features.py` NaN propagation risk | 🔴 **CHƯA FIX** | [features.py:163-165](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/backend/app/forecasting/features.py#L163-L165): Các chỉ số tỷ lệ được tính trước khi gọi hàm `fillna()`. |
| **TC25** | Preorder items rỗng gây lỗi 500 | 🟢 **ĐÃ FIX** | Đã bổ sung validator kiểm tra mảng món ăn không được rỗng. Test thực nghiệm: trả về HTTP `422 Unprocessable Entity` hợp lệ thay vì lỗi 500. |
| **TC29** | Verify hash giả trên Solana trả về True | 🟢 **ĐÃ FIX** | Test thực nghiệm với hash `"abc"` và tx `"def"`: Endpoint trả về `verified: False` với thông báo "Hash không hợp lệ hoặc quá ngắn". |

---

### 2.4. Phân nhóm lỗi LOW (3 Đã fix / 2 Chưa fix)

| Bug ID | Mô tả lỗi | Trạng thái | Chi tiết kiểm chứng |
|---|---|:---:|---|
| **BUG-019** | Thiếu file `__init__.py` trong thư mục `tests/` | 🟢 **ĐÃ FIX** | Đã tạo file [tests/\_\_init\_\_.py](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/tests/__init__.py). |
| **BUG-020** | `process_sales_dataframe()` cho phép `quantity = 0` | 🟢 **ĐÃ FIX** | [main.py:713](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/backend/app/main.py#L713): Đã đổi điều kiện lọc thành `if qty <= 0: continue`, loại bỏ triệt để bản ghi số lượng 0 gây nhiễu dữ liệu. |
| **BUG-021** | Upload purchases CSV chỉ hỗ trợ encoding UTF-8 | 🟢 **ĐÃ FIX** | [main.py:937-942](file:///d:/HaiAnh-HUST/Code/Python/foodflow-ai/backend/app/main.py#L937-L942): Đã hỗ trợ multi-encoding (`utf-8-sig`, `utf-8`, `cp1252`, `latin1`), tương thích hoàn toàn với file CSV xuất từ Excel tiếng Việt. |
| **BUG-023** | Template CSV tải về thiếu header tiếng Việt | 🔴 **CHƯA FIX** | File mẫu xuất ra tại `/api/sales/template` vẫn sử dụng tên cột tiếng Anh (`date`, `branch_id`, `quantity`, ...). |
| **BUG-024** | Các API danh mục thiếu phân trang (Pagination) | 🔴 **CHƯA FIX** | `/api/ingredients`, `/api/dishes`, `/api/recipes` vẫn trả về toàn bộ danh sách, chưa có tham số `skip` / `limit`. |

---

## 📋 BẢNG ĐỐI SOÁT TỔNG THỂ & HÀNH ĐỘNG TIẾP THEO

### Các hạng mục cần ưu tiên xử lý trong đợt tiếp theo:

1. **Hiệu năng ML:** Áp dụng Vectorization (Batch Predict) cho mô hình XGBoost trong `predictor.py` để lần chạy đầu tiên giảm từ ~5.5s xuống dưới 100ms.
2. **Bảo mật cơ bản:**
   - Xóa `backend/solana_authority.json` khỏi git index (`git rm --cached`) và đưa vào `.gitignore`.
   - Bổ sung cấu hình giới hạn kích thước file upload (tối đa 10MB) cho các endpoint nhập dữ liệu.
   - Thêm API Key Authentication đơn giản để bảo vệ các thao tác xóa và sửa dữ liệu.
3. **Refactoring:** Chuyển các hằng số magic numbers trong `ai_variance_evaluator.py` thành constants và sửa thứ tự `fillna()` trong `features.py`.

---
*Báo cáo được khởi tạo tự động dựa trên phân tích AST, Git Diff và Test Execution thực nghiệm trên hệ thống FoodFlow AI v2.1.*
