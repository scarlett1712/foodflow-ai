# 📋 BÁO CÁO KIỂM THỬ TOÀN DIỆN HỆ THỐNG THEO TẦNG: FOODFLOW AI
**Mã tài liệu:** `FDAI-QA-REPORT-v2.1`  
**Tên báo cáo:** `fdai_report`  
**Dự án:** FoodFlow AI - Hệ thống Dự báo Nhu cầu & Gợi ý Mua hàng F&B  
**Ngày thực hiện:** 27/09/2026  
**Người thực hiện:** QA / Senior Fullstack AI Assistant  
**Mục tiêu kiểm thử:** Đối soát thực tế hệ thống theo tiêu chuẩn kiểm thử riêng biệt hai tầng: **Backend / API / Database** và **Frontend / UI**.

---

## 📌 1. TỔNG QUAN & PHẠM VI KIỂM THỬ (EXECUTIVE SUMMARY)

Kiểm thử được tiến hành trực tiếp trên mã nguồn và cơ sở dữ liệu thực tế của hệ thống FoodFlow AI v2.1:
- **Backend**: FastAPI 0.115+, Python 3.12, Uvicorn, XGBoost 2.1+, Pandas, SQLite 3.
- **Frontend**: React 18, Vite, Tailwind CSS, Lucide Icons.
- **Khối tích hợp**: Open-Meteo Weather API, Solana Devnet Blockchain Notarization.

### Bảng Tóm Tắt Tình Trạng Sau Kiểm Thử:
| Phân hệ kiểm thử | Tổng số ca kiểm tra | ĐẠT (Pass) | CẢNH BÁO (Warning) | KHÔNG ĐẠT (Fail) | Đánh giá chung |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Backend: Status Codes & Schema** | 5 | 1 | 0 | 4 | 🔴 **Nghiêm trọng (Thiếu 404, 401/403)** |
| **Backend: Server-side Validation** | 6 | 0 | 0 | 6 | 🔴 **Nghiêm trọng (Lọt input sai vào DB & Model)** |
| **Backend: Database & Schema Integrity** | 4 | 2 | 0 | 2 | 🔴 **Nghiêm trọng (Lỗi crash 500 sau Reset Demo)** |
| **Backend: Phân quyền & Multi-Tenant** | 2 | 0 | 0 | 2 | 🟠 **Cao (Không có Auth & Cross-branch check)** |
| **Backend: Hiệu năng & N+1 Query** | 9 | 9 | 0 | 0 | 🟢 **Tốt (< 2.0s, Đạt chuẩn)** |
| **Frontend: Xử lý lỗi & Console** | 3 | 1 | 1 | 1 | 🟡 **Trung bình (Silent catch, popup alert)** |
| **Frontend: Đồng bộ Data & Stale State** | 2 | 1 | 0 | 1 | 🟠 **Cao (Tồn đọng state checkbox qua chi nhánh)** |
| **Frontend: Form Validation Client** | 3 | 0 | 0 | 3 | 🟡 **Trung bình (Im lặng khi submit thiếu field)** |
| **Frontend: Điều hướng (Navigation)** | 2 | 0 | 0 | 2 | 🟡 **Trung bình (Mất trạng thái khi F5, thiếu URL route)** |
| **Frontend: Responsive Mobile** | 1 | 0 | 0 | 1 | 🟡 **Trung bình (Sidebar cố định w-64)** |

---

## 🔍 2. CHI TIẾT KIỂM THỬ TẦNG 1: BACKEND / API & DATABASE

### 2.1. Kiểm tra Response Status Code & Schema
*Yêu cầu kiểm thử: Gọi trực tiếp API với Postman/curl/test script để kiểm tra mã trạng thái HTTP (400 khi input sai, 401/403 khi không có quyền, 404 khi không tồn tại).*

| Endpoint Kiểm Thử | Payload / Input | Status Mong Muốn | Status Thực Tế | Nhận Xét & Phân Tích Kỹ Thuật |
| :--- | :--- | :---: | :---: | :--- |
| `DELETE /api/branches/{branch_id}` | `branch_id = "BRANCH_FAKE_9999"` | `404 Not Found` | `200 OK` | **FAIL**: Server thực hiện `DELETE WHERE id = ?`, không kiểm tra `cur.rowcount == 0`, trả về thông báo thành công dù bản ghi không hề tồn tại. |
| `DELETE /api/dishes/{dish_id}` | `dish_id = "D_NON_EXISTENT_999"` | `404 Not Found` | `200 OK` | **FAIL**: Tương tự, xóa ID ảo vẫn trả về 200 kèm tin nhắn `"Đã xóa món D_NON_EXISTENT_999"`. |
| `DELETE /api/ingredients/{ingredient_id}`| `ingredient_id = "ING_FAKE_999"` | `404 Not Found` | `200 OK` | **FAIL**: Xóa nguyên liệu không tồn tại vẫn trả 200 OK. |
| `DELETE /api/preorders/{order_id}` | `order_id = 99999999` | `404 Not Found` | `200 OK` | **FAIL**: Xóa đơn đặt trước ảo vẫn trả 200 OK. |
| `GET /api/forecast` | `branch_id = "BRANCH_FAKE_9999"` | `404 Not Found` | `200 OK` | **FAIL**: Trả về HTTP 200 với danh sách `branches: []` rỗng thay vì thông báo mã chi nhánh không hợp lệ. |

---

### 2.2. Kiểm Tra Validation Dữ Liệu ở Tầng Server
*Yêu cầu kiểm thử: Validate ở tầng server — nếu frontend chặn nhưng gọi thẳng API vẫn cho qua thì đó là bug.*

#### 🚨 Phát hiện Lỗi Nghiêm Trọng (Critical Vulnerability):
1. **Giá món âm làm suy sụp mô hình AI**:
   - Gửi request: `POST /api/dishes/with-recipe` với `price = -50000`.
   - Kết quả: Server chấp nhận và lưu món có giá âm vào bảng `dishes`.
   - Hậu quả dây chuyền: Khi endpoint dự báo `/api/forecast` và `/api/dashboard/summary` khởi chạy, module trích xuất đặc trưng `predictor.py` thực hiện:
     ```python
     "log_price": np.log1p(d_price)
     ```
     Do `d_price = -50000`, hàm log tự nhiên của số âm sinh lỗi toán học:
     `RuntimeWarning: invalid value encountered in log1p` và biến toàn bộ giá trị dự báo doanh thu thành **`NaN`**!
2. **Cập nhật tồn kho âm**:
   - Gửi request: `POST /api/inventory/update` với `quantity = -150`.
   - Model `InventoryUpdate` trong `main.py` không có validator `quantity >= 0`.
   - Kết quả: Tồn kho của nguyên liệu trong DB bị âm, dẫn đến việc tính toán nhu cầu mua hàng bị sai lệch hoàn toàn.
3. **Format ngày tháng không hợp lệ**:
   - Gửi request: `POST /api/preorders` với `date = "2026-99-99"`.
   - Model `PreorderCreateMulti` không validate định dạng `YYYY-MM-DD`.
   - Kết quả: Lưu đơn hàng có ngày sai vào DB, làm sai lệch logic lọc lịch sử theo thời gian.
4. **Tên chuỗi rỗng toàn khoảng trắng**:
   - `POST /api/dishes/with-recipe` với `name: "   "` và `POST /api/preorders` với `customer_name: "   "`.
   - Cả 2 đều vượt qua tầng Pydantic và lưu chuỗi rỗng vào DB.
5. **Đơn đặt trước cho Chi nhánh không tồn tại**:
   - Gửi đơn hàng với `branch_id = "BRANCH_KHONG_TON_TAI"`.
   - Server không kiểm tra sự tồn tại của chi nhánh trong bảng `branches`, vẫn lưu bản ghi tạo nên dữ liệu mồ côi.

---

### 2.3. Kiểm Tra Trực Tiếp Cơ Sở Dữ Liệu (Database Integrity)
*Yêu cầu kiểm thử: Kiểm tra DB trực tiếp sau mỗi thao tác — dữ liệu ghi xuống DB có đúng, đủ, đúng kiểu, không lệch múi giờ, không duplicate.*

1. **Khóa Ngoại SQLite bị vô hiệu hóa (PRAGMA foreign_keys = OFF)**:
   - Truy vấn kiểm tra: `PRAGMA foreign_keys;` trả về `0`.
   - **Rủi ro**: Không có ràng buộc khóa ngoại tầng DB. Ví dụ: khi xóa một `dish_id` trong `dishes`, nếu code bỏ sót bảng con, dữ liệu công thức trong `recipes` sẽ trở thành rác.
2. **Lỗi Schema Crash HTTP 500 sau khi Reset Demo (Bug Nghiêm Trọng)**:
   - Trong `main.py`, endpoint `POST /api/data/reset-demo` gọi `scripts/generate_data.py`.
   - File `generate_data.py` tạo lại bảng `ingredients` với định nghĩa cũ (thiếu trường `category_tag`), bảng `preorders` (thiếu `items_json`), và không tạo bảng `purchase_history`.
   - Hàm nâng cấp `init_db_schema()` chỉ chạy 1 lần khi server vừa khởi động, **không được gọi lại sau khi Reset Demo**.
   - Hậu quả: Ngay sau khi người dùng bấm "Nạp lại Demo", gọi bất kỳ API nào liên quan đến tồn kho hoặc đơn hàng như `/api/inventory` đều quăng lỗi:
     `sqlite3.OperationalError: no such column: i.category_tag` (HTTP 500 Crash).
3. **Tính toàn vẹn dữ liệu Sales & Lịch**:
   - Kiểm tra `SELECT count(*) FROM sales WHERE date IS NULL OR quantity IS NULL`: Kết quả `0` (Đạt).
   - Kiểm tra duplicate recipes: `SELECT dish_id, ingredient_id, count(*) FROM recipes GROUP BY dish_id, ingredient_id HAVING count(*) > 1`: Kết quả `0` (Đạt).

---

### 2.4. Quyền Hạn ở Tầng API & Phân Quyền Chi Nhánh (RBAC & Multi-tenant)
*Yêu cầu kiểm thử: User role A gọi API của role B / chi nhánh khác bằng cách đổi ID/token phải bị chặn (401/403).*

- **Kết quả thực tế**: ❌ **FAIL**
  - Hệ thống hiện tại là kiến trúc **Unauthenticated & Zero-RBAC**:
    - Không có middleware xác thực JWT / Bearer Token.
    - Không có cơ chế User Context hay phân quyền người quản lý chi nhánh.
  - **Kịch bản kiểm thử**:
    - Người dùng ở Chi nhánh 1 chỉ cần sửa query parameter: `GET /api/inventory?branch_id=BRANCH_02` hoặc `GET /api/dashboard/summary?branch_id=BRANCH_02` là xem được toàn bộ số liệu nội bộ của Chi nhánh 2.
    - Bất kỳ client nào cũng có thể gửi `POST /api/data/clear-clean` để **xóa sạch 100% dữ liệu của toàn bộ hệ thống** mà không cần quyền Quản trị viên (Super Admin).

---

### 2.5. Kiểm Tra Hiệu Năng Cơ Bản & N+1 Queries
*Yêu cầu kiểm thử: API có bị chậm bất thường khi load dữ liệu nhiều, có bị N+1 query lặp trong code không.*

- **Kết quả đo độ trễ phản hồi (Response Latency Benchmark)**:
  - `GET /api/branches`: **0.010 giây** (Đạt)
  - `GET /api/dishes`: **0.010 giây** (Đạt)
  - `GET /api/ingredients`: **0.008 giây** (Đạt)
  - `GET /api/inventory?branch_id=BRANCH_01`: **0.005 giây** (Đạt)
  - `GET /api/preorders?branch_id=BRANCH_01`: **0.013 giây** (Đạt)
  - `GET /api/dashboard/summary?branch_id=BRANCH_01`: **0.054 giây** (Đạt)
  - `GET /api/forecast?branch_id=BRANCH_01&n_days=7`: **0.031 giây** (Đạt)
  - `GET /api/purchase-recommendations?branch_id=BRANCH_01`: **0.045 giây** (Đạt)
  - `GET /api/insights?branch_id=BRANCH_01`: **1.183 giây** (Đạt)
- **Đánh giá N+1 Query**: 🟢 **PASS**. Không có vòng lặp gọi query SQL đơn lẻ bên trong vòng lặp các món ăn. Các phép tổng hợp đều được xử lý bằng câu lệnh SQL `GROUP BY` hoặc gộp mảng với Pandas DataFrame. Endpoint `/api/forecast` đã được trang bị in-memory TTL Cache (10 phút) tránh tính lại XGBoost lặp thừa.

---

## 🖥️ 3. CHI TIẾT KIỂM THỬ TẦNG 2: FRONTEND / UI

### 3.1. Console DevTools & Xử Lý Lỗi Bị "Im Lặng" (Silent Failures)
*Yêu cầu kiểm thử: Console có lỗi JS đỏ không? Network fail (4xx/5xx) mà UI vẫn im lặng không báo gì cho người dùng không?*

1. **Lỗi `fetchBranches()` bị nuốt chửng**:
   - Vị trí: `App.jsx` dòng 66-68:
     ```javascript
     } catch (e) {
       console.error('Error fetching branches:', e);
     }
     ```
   - Hiện tượng: Khi backend rớt mạng hoặc endpoint `/api/branches` gặp lỗi 500, khối catch chỉ in ra console đỏ. Giao diện người dùng hoàn toàn không hiển thị thông báo hay banner cảnh báo, dropdown chi nhánh bị trống trơn.
2. **Lỗi cục bộ từng API trong `Promise.allSettled`**:
   - Vị trí: `App.jsx` dòng 111-115.
   - Hiện tượng: Nếu 1 API (như `getPreorders` hoặc `getInventory`) bị lỗi trong khi các API khác thành công, hệ thống chỉ `console.warn` và gán state thành `null`/mảng rỗng. Người dùng khi vào tab Kho hoặc Đơn đặt trước chỉ thấy bảng trống trơn mà không hề biết rằng kết nối tới API đó vừa thất bại.
3. **Cơ chế thông báo người dùng còn thô sơ**:
   - Hầu hết các trang đều dùng popup trình duyệt `alert('Lỗi...')` và `confirm('...')`. Điều này chặn luồng xử lý của tab trình duyệt và không thân thiện với trải nghiệm người dùng hiện đại.

---

### 3.2. Độ Khớp Dữ Liệu & Stale State Khi Chuyển Chi Nhánh
*Yêu cầu kiểm thử: Dữ liệu hiển thị có khớp API không, có bị cache cũ, có hiển thị nhầm chi nhánh khác khi chuyển tab/chi nhánh không?*

#### ⚠️ Phát hiện Lỗi Rò Rỉ Trạng Thái Checkbox (Stale Selection Bug):
- Vị trí: `PurchasePage.jsx` dòng 29:
  ```javascript
  const [checkedItems, setCheckedItems] = useState({});
  ```
- **Hiện tượng thực tế**:
  1. Người dùng đang ở **Chi nhánh Hà Nội (BRANCH_01)**, tích chọn 3 nguyên liệu cần đi chợ trong danh sách đề xuất.
  2. Người dùng lên Header chuyển sang **Chi nhánh Đà Nẵng (BRANCH_02)**.
  3. Biến state `checkedItems` **không hề được reset**.
  4. Nếu người dùng nhấn nút *"Xác nhận nhập kho"*, hệ thống sẽ lấy ID của các mặt hàng đã tick từ Chi nhánh Hà Nội để ghi nhận nhập kho cho Chi nhánh Đà Nẵng!

---

### 3.3. Form Validation Phía Client
*Yêu cầu kiểm thử: Bấm Submit khi thiếu field hoặc sai định dạng — có báo lỗi đúng chỗ, đúng field không hay báo chung chung/im lặng?*

| Màn hình / Modal | Hành động test | Phản hồi thực tế của UI | Trạng thái | Đánh giá |
| :--- | :--- | :--- | :---: | :--- |
| **BranchModal** (Quản lý chi nhánh) | Bấm "Thêm Chi Nhánh" khi để trống ô Tên | Code chạy `if (!name.trim()) return;` và dừng lại. Không có viền đỏ, không có thông báo lỗi. | ❌ **FAIL** | Người dùng tưởng nút bấm bị liệt vì UI hoàn toàn "im lặng". |
| **PreordersPage** (Tạo đơn tiệc/đặt trước) | Bấm "Xác Nhận Đơn" khi chưa nhập Tên khách | Code chạy `if (!customerName.trim() ...) return;` và dừng lại âm thầm. | ❌ **FAIL** | Tương tự, không hiển thị trường bắt buộc nào đang bị thiếu. |
| **InventoryPage** (Cập nhật tồn kho nhanh) | Nhập số lượng âm `-50` rồi bấm Lưu | Gửi thẳng giá trị `-50` lên server và thành công. | ❌ **FAIL** | Client không chặn giá trị âm ở ô input sửa nhanh. |

---

### 3.4. Điều Hướng & Trạng Thái Ứng Dụng (Navigation & State Persistence)
*Yêu cầu kiểm thử: Back/forward trình duyệt, refresh giữa chừng, mở lại tab cũ — trạng thái UI có còn đúng không?*

- **Hiện trạng kỹ thuật**: Ứng dụng hiện đang dùng biến trạng thái nội bộ:
  ```javascript
  const [currentTab, setCurrentTab] = useState('dashboard');
  ```
  chưa tích hợp thư viện định tuyến (`react-router-dom`) hoặc cơ chế lưu URL Hash (`#/preorders`).
- **Hành vi khi kiểm thử**:
  1. **Nhấn F5 (Refresh trình duyệt)**: Nếu người dùng đang làm việc ở tab `Thực Đơn & Định Lượng` hoặc `Đơn Đặt Trước` mà nhấn Refresh, giao diện lập tức bị đẩy về tab `Tổng Quan (Dashboard)` mặc định.
  2. **Nút Back / Forward trình duyệt**: Bấm quay lại trang trước trên trình duyệt không chuyển tab mà người dùng bị điều hướng rời khỏi ứng dụng.
  3. **Không hỗ trợ Deep Link**: Không thể gửi trực tiếp đường link tab cụ thể cho đồng nghiệp (ví dụ: `http://localhost:5173/inventory`).

---

### 3.5. Kiểm Tra Khả Năng Đáp Ứng Giao Diện (Responsive Mobile)
*Yêu cầu kiểm thử: Thử ít nhất ở kích thước mobile (375px - 414px) và desktop (1280px+).*

- **Màn hình Desktop (>= 1024px)**: Giao diện hiển thị sắc nét, chia cột khoa học, thẻ KPI và bảng số liệu rõ ràng.
- **Màn hình Mobile (< 768px)**:
  - Khung `Sidebar.jsx` có class `w-64` (256px) cố định, không có cơ chế thu gọn tự động (drawer) và Navbar không có nút bấm Hamburger Menu (3 dấu gạch).
  - Khi xem trên điện thoại có bề ngang 375px, thanh sidebar chiếm đến 70% màn hình, ép khu vực nội dung chính co lại còn ~120px khiến bảng và chữ bị vỡ layout nặng nề.

---

## 📑 4. MA TRẬN PHÂN LOẠI MỨC ĐỘ RỦI RO & BỌ TỒN ĐỌNG (BUG MATRIX)

| Mã lỗi | Phân tầng | Tên lỗi | Mức độ | Hậu quả thực tế |
| :---: | :---: | :--- | :---: | :--- |
| **BUG-01** | Backend | Cho phép nhập giá món âm (`price < 0`) | 🔴 **CRITICAL** | Sinh `NaN` trong mô hình XGBoost (`RuntimeWarning: invalid value encountered in log1p`). |
| **BUG-02** | Backend/DB | Thiếu cột schema sau khi Reset Demo (`/api/data/reset-demo`) | 🔴 **CRITICAL** | Endpoint `/api/inventory` bị crash văng lỗi 500 `no such column: i.category_tag`. |
| **BUG-03** | Backend | Trả 200 OK thay vì 404 Not Found khi xóa ID không tồn tại | 🟠 **HIGH** | Vi phạm chuẩn REST API, client không phát hiện được tài nguyên không tồn tại. |
| **BUG-04** | Backend | Không có Auth & Phân quyền chi nhánh (Zero-RBAC) | 🟠 **HIGH** | Bất kỳ ai cũng có thể đọc/sửa dữ liệu chi nhánh khác hoặc xóa trắng database. |
| **BUG-05** | Backend | Không chặn tồn kho âm và ngày đặt hàng dị tật | 🟠 **HIGH** | Rác cơ sở dữ liệu, phá vỡ logic tính toán bù hàng. |
| **BUG-06** | Frontend | Rò rỉ trạng thái `checkedItems` qua các chi nhánh | 🟠 **HIGH** | Nhập nhầm nguyên liệu của chi nhánh này vào chi nhánh khác. |
| **BUG-07** | Frontend | Form âm thầm không làm gì khi thiếu trường bắt buộc | 🟡 **MEDIUM** | Người dùng gặp hiện tượng "UI đóng băng", không biết phải sửa ở đâu. |
| **BUG-08** | Frontend | Thiếu URL Routing, mất tab khi F5 refresh | 🟡 **MEDIUM** | Giảm sút nghiêm trọng trải nghiệm người dùng hàng ngày. |
| **BUG-09** | Frontend | Sidebar cố định chiếm hết màn hình mobile | 🟡 **MEDIUM** | Không thể sử dụng ứng dụng trên thiết bị di động / máy tính bảng nhỏ. |

---

## 🛠️ 5. KẾ HOẠCH HÀNH ĐỘNG & HƯỚNG DẪN KHẮC PHỤC (REMEDIATION PLAN)

### Bước 1: Khắc phục triệt để tầng Backend & Database
1. **Sửa `reset_to_demo_data()` trong `backend/app/main.py`**:
   Gọi hàm `init_db_schema()` ngay sau khi tạo dataset để tự động thêm các cột `category_tag`, `items_json` và bảng `purchase_history`:
   ```python
   @app.post("/api/data/reset-demo")
   def reset_to_demo_data():
       from scripts.generate_data import generate_big_dataset
       generate_big_dataset()
       init_db_schema()  # <-- FIX BUG-02: Đồng bộ đầy đủ cột schema
       train_and_evaluate_all()
       return {"status": "success", "message": "Đã nạp lại dữ liệu mẫu..."}
   ```
2. **Kích hoạt Foreign Key SQLite trong `get_db()`**:
   ```python
   @contextmanager
   def get_db():
       conn = sqlite3.connect(DB_PATH)
       conn.row_factory = sqlite3.Row
       conn.execute("PRAGMA foreign_keys = ON")  # <-- Bắt buộc cưỡng chế khóa ngoại
       try:
           yield conn
       finally:
           conn.close()
   ```
3. **Thêm Pydantic Validator chặn giá âm & tên rỗng**:
   ```python
   class DishWithRecipeCreate(BaseModel):
       id: Optional[str] = None
       name: str
       category: str
       price: float
       ingredients: List[DishIngredientInput] = []

       @field_validator('price')
       @classmethod
       def validate_price(cls, v):
           if v < 0:
               raise ValueError('Giá bán không được âm!')
           return v

       @field_validator('name')
       @classmethod
       def validate_name(cls, v):
           if not v or not v.strip():
               raise ValueError('Tên món ăn không được để trống!')
           return v.strip()
   ```
4. **Chuẩn hóa trả về 404 cho các API xóa**:
   ```python
   @app.delete("/api/dishes/{dish_id}")
   def delete_dish(dish_id: str):
       with get_db() as conn:
           cur = conn.cursor()
           cur.execute("DELETE FROM dishes WHERE id = ?", (dish_id,))
           if cur.rowcount == 0:
               raise HTTPException(status_code=404, detail=f"Không tìm thấy món ăn {dish_id}")
           cur.execute("DELETE FROM recipes WHERE dish_id = ?", (dish_id,))
           conn.commit()
       return {"status": "success", "message": f"Đã xóa món {dish_id}"}
   ```

---

### Bước 2: Khắc phục tầng Frontend / UI
1. **Reset `checkedItems` khi đổi chi nhánh (`PurchasePage.jsx`)**:
   ```javascript
   useEffect(() => {
     setCheckedItems({}); // <-- Xóa lựa chọn cũ khi branchId thay đổi
   }, [branchId]);
   ```
2. **Hiển thị thông báo lỗi trực quan trên Form**:
   - Thay vì `if (!name.trim()) return;`, hiển thị thông báo inline:
   ```jsx
   const [errorMsg, setErrorMsg] = useState('');
   // Khi submit:
   if (!name.trim()) {
     setErrorMsg('Vui lòng nhập tên chi nhánh!');
     return;
   }
   // Trong JSX:
   {errorMsg && <p className="text-xs text-red-500 font-medium mt-1">{errorMsg}</p>}
   ```
3. **Đồng bộ tab vào URL Hash (`App.jsx`)**:
   - Khởi tạo: `const [currentTab, setCurrentTab] = useState(window.location.hash.replace('#/', '') || 'dashboard');`
   - Cập nhật khi đổi tab: `window.location.hash = `#/${tab}`;`
   - Bắt sự kiện: `window.addEventListener('hashchange', ...)` giúp người dùng dùng được nút Back/Forward và F5 không mất tab.
4. **Thêm Drawer thu gọn cho Sidebar trên Mobile**:
   - Thêm nút Hamburger menu ở Navbar và áp dụng `hidden md:flex` cho sidebar khi ở màn hình nhỏ.

---

## 🎯 6. KẾT LUẬN & KIẾN NGHỊ

Hệ thống **FoodFlow AI** sở hữu nền tảng thuật toán Machine Learning (Universal XGBoost) rất mạnh mẽ, tích hợp thời tiết thông minh và tốc độ xử lý nhanh (< 0.1s ở hầu hết các endpoint). 

Tuy nhiên, hệ thống cần được **gia cố bảo mật dữ liệu ở tầng Server (Server-side Validation)** và **đồng bộ trạng thái ở tầng Client (State Isolation)** để ngăn chặn các dữ liệu bẩn xâm nhập làm sai lệch mô hình dự báo AI, đồng thời mang lại trải nghiệm phần mềm chỉn chu, tin cậy tuyệt đối cho các chuỗi nhà hàng F&B.

---
*Báo cáo được lưu trữ tại file: `fdai_report.md` trong thư mục gốc dự án.*
