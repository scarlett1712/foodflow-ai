# FOODFLOW AI - PROJECT RULES & GUIDELINES

## 1. Mục Tiêu Dự Án (Core Objectives)
- Xây dựng sản phẩm MVP hoàn chỉnh: **AI dự đoán nhu cầu nguyên liệu và gợi ý mua hàng cho quán ăn/nhà hàng nhỏ**.
- Tập trung vào luồng giá trị cốt lõi:
  `Doanh số lịch sử -> Dự báo AI (1-7 ngày) -> Cộng dồn Đơn đặt trước -> Quy đổi Công thức món -> Đối chiếu Tồn kho -> Gợi ý Mua hàng thông minh -> Dashboard trực quan`.

## 2. Phạm Vi Nghiêm Ngặt (Strict Constraints)
- **TUYỆT ĐỐI KHÔNG**:
  - Không Web3 / Blockchain / Solana / Smart Contracts / Rust.
  - Không tích hợp cổng thanh toán phức tạp.
  - Không xây dựng hệ thống ERP cồng kềnh hay Auth đa tầng phức tạp.
  - Không hardcode kết quả số liệu trên UI (kết quả phải tính thật từ backend ML/database).

## 3. Nguyên Tắc Kỹ Thuật (Engineering Best Practices)
- **Tech Stack**:
  - Backend: Python FastAPI + SQLite / SQLAlchemy + Pydantic.
  - ML / Data: Pandas, NumPy, Scikit-learn, XGBoost.
  - Frontend: React + Vite + Tailwind CSS + Lucide Icons + Recharts.
- **Machine Learning**:
  - Tách tập dữ liệu theo thời gian thực (Chronological Split: train trên quá khứ, test trên ngày gần nhất).
  - So sánh giữa Baseline (Trung bình theo thứ trong tuần) vs XGBoost/ML Model.
  - Đánh giá bằng **MAE** và **WAPE** (Weighted Absolute Percentage Error).
- **Business Logic**:
  - Nhu cầu kỳ vọng = Dự báo ML + Đơn đặt trước đã xác nhận.
  - Nguyên liệu cần = Tổng (Nhu cầu món × Định lượng công thức).
  - Khuyến nghị mua = Max(Nguyên liệu cần - Tồn kho hiện tại, 0).
- **Dễ triển khai & Demo**:
  - Có sẵn script sinh dữ liệu mẫu thực tế (`scripts/generate_data.py`).
  - Chạy local mượt mà với hướng dẫn rõ ràng trong `README.md`.
