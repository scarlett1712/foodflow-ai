import React, { useState } from 'react';
import { UploadCloud, FileText, Download, CheckCircle2, AlertTriangle, X, ShoppingCart, ArrowRight } from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export default function UploadPurchaseModal({ isOpen, onClose, onUploaded, branchId }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewRows, setPreviewRows] = useState([]);
  const [totalRowsCount, setTotalRowsCount] = useState(0);
  const [totalSpentEstimated, setTotalSpentEstimated] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  if (!isOpen) return null;

  const handleDownloadTemplate = () => {
    window.open(`${API_BASE_URL}/purchases/template`, '_blank');
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setSelectedFile(file);
    setErrorMessage('');

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target.result;
        const lines = text.split('\n').filter(l => l.trim().length > 0);
        if (lines.length <= 1) {
          setErrorMessage('File CSV trống hoặc không đúng định dạng');
          return;
        }

        const headers = lines[0].split(',').map(h => h.trim());
        const parsed = [];
        let totalCost = 0;

        for (let i = 1; i < lines.length; i++) {
          const values = lines[i].split(',').map(v => v.trim());
          const rowObj = {};
          headers.forEach((h, idx) => {
            rowObj[h] = values[idx] || '';
          });
          const rowCost = parseFloat(rowObj.total_cost || 0) || (parseFloat(rowObj.quantity_purchased || 0) * parseFloat(rowObj.unit_price || 0));
          totalCost += rowCost;

          if (i <= 5) parsed.push(rowObj);
        }

        setPreviewRows(parsed);
        setTotalRowsCount(lines.length - 1);
        setTotalSpentEstimated(totalCost);
      } catch (err) {
        setErrorMessage('Lỗi đọc file: ' + err.message);
      }
    };
    reader.readAsText(file);
  };

  const [varianceReason, setVarianceReason] = useState('');

  const QUICK_REASONS = [
    { label: '🌩️ Bão giá thị trường', text: 'Nhà cung cấp điều chỉnh tăng giá do biến động thị trường và chi phí vận chuyển nông sản.' },
    { label: '🎉 Nhập tiệc đột xuất', text: 'Nhà hàng nhận đặt thêm tiệc lớn đột xuất cuối tuần nên cần nhập dôi dư nguyên liệu dự trữ.' },
    { label: '📦 Bù hao hụt kho', text: 'Nhập bổ sung khẩn cấp do lô nguyên liệu cũ bị hao hụt và hỏng trong quá trình bảo quản.' },
    { label: '🏷️ Mua sỉ chiết khấu', text: 'Tận dụng chương trình chiết khấu mua sỉ số lượng lớn từ nhà cung cấp để tối ưu giá vốn.' }
  ];

  const handleConfirmUpload = async () => {
    if (!selectedFile) return;
    try {
      setIsUploading(true);
      setErrorMessage('');
      const formData = new FormData();
      formData.append('file', selectedFile);
      if (varianceReason) {
        formData.append('variance_reason', varianceReason);
      }

      const res = await axios.post(`${API_BASE_URL}/purchases/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      setUploadSuccess(true);
      setTimeout(() => {
        onUploaded();
        onClose();
      }, 1500);
    } catch (err) {
      setErrorMessage(err.response?.data?.detail || 'Lỗi tải lên dữ liệu đi chợ: ' + err.message);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4 my-8">
        
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-amber-50 rounded-xl text-amber-600">
              <ShoppingCart className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Tải Lên Lịch Sử Đi Chợ & Nhập Kho</h3>
              <p className="text-xs text-slate-500">
                Tự động cộng dồn tồn kho, tạo lô FEFO và ký chứng thực kiểm toán trên Solana Devnet.
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 cursor-pointer">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Template Download Banner */}
        <div className="bg-amber-50 border border-amber-200 p-3.5 rounded-xl flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <FileText className="w-5 h-5 text-amber-600 shrink-0" />
            <div>
              <p className="text-xs font-bold text-amber-900">File Mẫu Đi Chợ (Purchase CSV Template)</p>
              <p className="text-[11px] text-amber-700">Các cột: <code>date</code>, <code>branch_id</code>, <code>ingredient_name</code>, <code>quantity_purchased</code>, <code>unit</code>, <code>unit_price</code>, <code>expiry_date</code></p>
            </div>
          </div>
          <button
            onClick={handleDownloadTemplate}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-semibold cursor-pointer shadow-2xs shrink-0"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Tải File Mẫu</span>
          </button>
        </div>

        {/* File Dropzone */}
        {!selectedFile ? (
          <label className="border-2 border-dashed border-slate-300 hover:border-amber-500 bg-slate-50/50 hover:bg-amber-50/30 rounded-2xl p-8 flex flex-col items-center justify-center gap-2 cursor-pointer transition-all">
            <UploadCloud className="w-10 h-10 text-slate-400" />
            <span className="text-sm font-semibold text-slate-700">Chọn hoặc Kéo thả file CSV Lịch Sử Đi Chợ vào đây</span>
            <span className="text-xs text-slate-400">Hệ thống sẽ cập nhật kho ngay sau khi tải lên</span>
            <input type="file" accept=".csv" onChange={handleFileChange} className="hidden" />
          </label>
        ) : (
          /* Preview Data Table */
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-700 flex items-center gap-1.5">
                <FileText className="w-4 h-4 text-amber-600" />
                {selectedFile.name} (<strong>{totalRowsCount} mặt hàng</strong> • Tổng tiền: <strong className="text-emerald-700">{totalSpentEstimated.toLocaleString('vi-VN')} đ</strong>)
              </span>
              <button 
                onClick={() => setSelectedFile(null)} 
                className="text-red-500 hover:text-red-700 font-medium cursor-pointer"
              >
                Chọn file khác
              </button>
            </div>

            <div className="border border-slate-200 rounded-xl overflow-hidden max-h-48">
              <table className="w-full text-left text-xs table-fixed">
                <thead>
                  <tr className="bg-slate-100 text-slate-600 font-bold border-b border-slate-200">
                    <th className="py-2 px-2.5 w-[18%]">Ngày Mua</th>
                    <th className="py-2 px-2.5 w-[14%]">Chi Nhánh</th>
                    <th className="py-2 px-2.5 w-[28%]">Tên Nguyên Liệu</th>
                    <th className="py-2 px-2.5 text-right w-[14%]">Số Lượng</th>
                    <th className="py-2 px-2.5 text-right w-[14%]">Đơn Giá</th>
                    <th className="py-2 px-2.5 w-[12%]">Hạn Dùng</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {previewRows.map((r, i) => (
                    <tr key={i} className="hover:bg-slate-50">
                      <td className="py-2 px-2.5 font-mono break-words">{r.date}</td>
                      <td className="py-2 px-2.5 break-words">{r.branch_id}</td>
                      <td className="py-2 px-2.5 font-semibold text-slate-900 break-words leading-tight">{r.ingredient_name || r.ingredient_id}</td>
                      <td className="py-2 px-2.5 text-right font-bold text-amber-600 break-words">
                        {r.quantity_purchased} {r.unit}
                      </td>
                      <td className="py-2 px-2.5 text-right break-words">{r.unit_price ? Number(r.unit_price).toLocaleString('vi-VN') + ' đ' : '-'}</td>
                      <td className="py-2 px-2.5 text-slate-500 break-words">{r.expiry_date || 'Không có'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Optional Variance Reason Input */}
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-slate-700">
                  Lý Do Giải Trình Chênh Lệch (Nếu Có Biến Động Giá/Lượng):
                </label>
                <span className="text-[10px] text-slate-400">AI tự động thẩm định & lưu Solana</span>
              </div>
              <div className="flex flex-wrap gap-1">
                {QUICK_REASONS.map((qr, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setVarianceReason(qr.text)}
                    className="px-2 py-0.5 rounded text-[10px] font-medium bg-white hover:bg-amber-50 hover:text-amber-800 border border-slate-200 text-slate-600 cursor-pointer"
                  >
                    {qr.label}
                  </button>
                ))}
              </div>
              <input
                type="text"
                value={varianceReason}
                onChange={(e) => setVarianceReason(e.target.value)}
                placeholder="VD: Nhà cung cấp tăng giá do bão lũ, hoặc nhập dự trữ tiệc cuối tuần..."
                className="w-full px-3 py-1.5 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-amber-500 text-slate-800"
              />
            </div>
          </div>
        )}

        {errorMessage && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-lg text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {uploadSuccess && (
          <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-3 py-2 rounded-lg text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
            <span>Nạp thành công! Đã cập nhật tồn kho & thẩm định kiểm toán Solana.</span>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold cursor-pointer"
          >
            Đóng
          </button>
          <button
            type="button"
            disabled={!selectedFile || isUploading || uploadSuccess}
            onClick={handleConfirmUpload}
            className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold shadow-xs ${
              !selectedFile || isUploading || uploadSuccess
                ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                : 'bg-amber-600 hover:bg-amber-700 text-white cursor-pointer active:scale-95'
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{isUploading ? 'Đang Nạp & Ký Duyệt Solana...' : 'Xác Nhận Nhập Hàng & Lưu Solana'}</span>
          </button>
        </div>

      </div>
    </div>
  );
}
