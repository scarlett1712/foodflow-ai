# 🍲 FoodFlow AI — Intelligent F&B Inventory & Supply Chain Optimization with Solana Audit Layer

> **Hệ Thống Trí Tuệ Nhân Tạo Dự Báo Nhu Cầu & Tối Ưu Chuỗi Cung Ứng F&B Tích Hợp Kiểm Toán Bất Biến Trên Solana Devnet**  
> *Hạng mục tranh tài: BEST TECHNICAL BUILD TRACK*

---

## 🌟 1. Tổng Quan Dự Án (Overview)

**FoodFlow AI** là giải pháp kết hợp giữa **Trí Tuệ Nhân Tạo (Machine Learning Off-Chain)** và **Blockchain (Solana Devnet On-Chain)** nhằm tối ưu hóa toàn bộ chuỗi cung ứng, tồn kho và quy trình đi chợ cho các quán ăn, nhà hàng và chuỗi F&B.

### 🎯 Các Trụ Cột Kỹ Thuật Chính:
1. **Dự Báo Nhu Cầu XGBoost (1–7 ngày)**: Học quy luật từ doanh số bán hàng lịch sử, ngày trong tuần, xu hướng tăng trưởng và đơn đặt bàn trước.
2. **Bóc Tách Định Lượng Tự Động (BOM Decomposition)**: Tự động phân rã từng món ăn thành khối lượng nguyên liệu cấu thành chính xác (kg thịt, phở, gia vị...).
3. **Quản Lý Tồn Kho Hạn Dùng FEFO (First-Expired, First-Out)**: Theo dõi từng lô hàng, cảnh báo hết hạn và tối ưu thứ tự xuất kho.
4. **AI Thẩm Định Chênh Lệch & Tự Động Thích Ứng (Adaptive Feedback)**: Khi giá hoặc lượng mua bị vượt định mức, AI thẩm định lý do giải trình (bão giá, tiệc lớn, hỏng kho) và tự động cân chỉnh mô hình ML tuần sau.
5. **Tầng Kiểm Toán Bất Biến Solana Devnet (Audit Trail)**:
   - **Lô Hàng FEFO (Tamper-Proof Batches)**: Băm SHA-256 mã lô và hạn dùng on-chain, chống sửa lùi ngày hết hạn.
   - **Kiểm Toán Tuân Thủ AI (Dual-Commitment Proof)**: Khóa đồng thời *Kế hoạch AI + Thực tế mua + Lý do giải trình + Kết luận AI* lên Solana Devnet.

---

## 🏗️ 2. Kiến Trúc Hệ Thống (System Architecture)

```
┌────────────────────────────────────────────────────────────────────────┐
│                        OFF-CHAIN (AI & BUSINESS ENGINE)                │
├──────────────────┬─────────────────────────────────────────────────────┤
│ Frontend         │ React 18, TailwindCSS, Lucide Icons, Vite           │
│ Backend API      │ FastAPI (Python 3.11), Uvicorn                      │
│ Database         │ SQLite (Hỗ trợ PostgreSQL migration)                │
│ Data Processing  │ Pandas, NumPy, OpenPyXL (Excel & CSV Hub)           │
│ AI / ML Core     │ XGBoost Regression (Dự báo 1–7 ngày)                │
│ Nghiệp Vụ F&B   │ BOM Recipes, FEFO Batches, Multi-dish Preorders     │
└──────────────────┴─────────────────────────────────────────────────────┘
                                   │
                                   ▼ (Deterministic SHA-256 Hashing)
┌────────────────────────────────────────────────────────────────────────┐
│                    ON-CHAIN (SOLANA DEVNET AUDIT TRAIL)                │
├──────────────────┬─────────────────────────────────────────────────────┤
│ Smart Contract   │ Anchor Framework (Rust) @ programs/foodflow-audit/ │
│ Network / Cluster│ Solana Devnet (RPC: https://api.devnet.solana.com)  │
│ Authority Keypair│ Ed25519 Server Keypair / PDA Signatures             │
│ On-chain Data    │ SHA-256 Hashes, Batch Codes, PO Dates, Timestamps  │
│ Verification     │ Solana Explorer Links & Client Verification Modal   │
└──────────────────┴─────────────────────────────────────────────────────┘
```

---

## 🚀 3. Hướng Dẫn Cài Đặt & Khởi Chạy (Quick Start)

### Yêu Cầu Môi Trường:
- **Node.js**: $\ge 18$
- **Python**: $\ge 3.10$

### Cách 1: 1-Click Khởi Động trên Windows
Nhấp đúp chuột vào file:
👉 **`run_app.bat`**

### Cách 2: Chạy Thủ Công

#### 1. Backend (FastAPI):
```bash
# Cài đặt thư viện
pip install fastapi uvicorn pandas numpy openpyxl xgboost scikit-learn pydantic solders solana

# Khởi chạy server
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### 2. Frontend (React + Vite):
```bash
cd frontend
npm install
npm run dev
```

---

## 🌐 4. Đường Dẫn Truy Cập
- **Giao Diện Ứng Dụng**: [http://localhost:5173](http://localhost:5173)
- **Tài Liệu Swagger API**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Solana Devnet Explorer**: [https://explorer.solana.com/?cluster=devnet](https://explorer.solana.com/?cluster=devnet)
