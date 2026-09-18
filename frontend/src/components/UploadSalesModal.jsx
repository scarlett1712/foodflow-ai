import React, { useState } from 'react';
import { 
  UploadCloud, 
  FileSpreadsheet, 
  Download, 
  CheckCircle2, 
  AlertTriangle, 
  X, 
  FileText, 
  Layers, 
  TrendingUp, 
  Sparkles,
  FileCheck,
  ArrowRight
} from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export default function UploadSalesModal({ isOpen, onClose, onUploaded }) {
  const [salesFile, setSalesFile] = useState(null);
  const [recipesFile, setRecipesFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [successResult, setSuccessResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  if (!isOpen) return null;

  const handleDownloadTemplate = (type, format) => {
    window.open(`${API_BASE_URL}/${type}/template?format=${format}`, '_blank');
  };

  const handleConfirmUpload = async () => {
    if (!salesFile && !recipesFile) {
      setErrorMessage('Vui lòng chọn ít nhất 1 file (Lịch sử bán hàng hoặc Công thức món ăn) để tải lên!');
      return;
    }

    try {
      setIsUploading(true);
      setErrorMessage('');

      const formData = new FormData();
      if (salesFile) formData.append('sales_file', salesFile);
      if (recipesFile) formData.append('recipes_file', recipesFile);

      const res = await axios.post(`${API_BASE_URL}/data/upload-package`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      setSuccessResult(res.data);
      setUploadSuccess(true);

      setTimeout(() => {
        if (onUploaded) onUploaded();
        onClose();
      }, 2000);
    } catch (err) {
      setErrorMessage(err.response?.data?.detail || 'Lỗi tải lên dữ liệu: ' + err.message);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-3xl w-full p-6 shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-emerald-100 text-emerald-700 rounded-xl">
              <FileSpreadsheet className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Trung Tâm Nạp Dữ Liệu Excel / CSV</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Nạp Lịch sử bán hàng để AI học chu kỳ và Công thức định lượng để hệ thống bóc tách nguyên liệu đi chợ.
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 cursor-pointer">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Template Download Section */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          
          {/* Sales Template Card */}
          <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
            <div className="flex items-center gap-2 text-slate-800 font-bold text-xs">
              <TrendingUp className="w-4 h-4 text-emerald-600" />
              <span>1. File Mẫu Doanh Số Bán Hàng</span>
            </div>
            <p className="text-[11px] text-slate-500">
              Cột: <code>date</code>, <code>branch_id</code>, <code>dish_id</code>, <code>dish_name</code>, <code>quantity</code>, <code>revenue</code>
            </p>
            <div className="flex items-center gap-2 pt-1">
              <button
                type="button"
                onClick={() => handleDownloadTemplate('sales', 'excel')}
                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold cursor-pointer shadow-2xs"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Tải Mẫu Excel (.xlsx)</span>
              </button>
              <button
                type="button"
                onClick={() => handleDownloadTemplate('sales', 'csv')}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 rounded-lg text-xs font-semibold cursor-pointer"
              >
                <span>Mẫu CSV</span>
              </button>
            </div>
          </div>

          {/* Recipes Template Card */}
          <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
            <div className="flex items-center gap-2 text-slate-800 font-bold text-xs">
              <Layers className="w-4 h-4 text-purple-600" />
              <span>2. File Mẫu Công Thức (BOM)</span>
            </div>
            <p className="text-[11px] text-slate-500">
              Cột: <code>dish_name</code>, <code>dish_price</code>, <code>ingredient_name</code>, <code>quantity</code>, <code>unit</code>, <code>cost_per_unit</code>
            </p>
            <div className="flex items-center gap-2 pt-1">
              <button
                type="button"
                onClick={() => handleDownloadTemplate('recipes', 'excel')}
                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-semibold cursor-pointer shadow-2xs"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Tải Mẫu Excel (.xlsx)</span>
              </button>
              <button
                type="button"
                onClick={() => handleDownloadTemplate('recipes', 'csv')}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 rounded-lg text-xs font-semibold cursor-pointer"
              >
                <span>Mẫu CSV</span>
              </button>
            </div>
          </div>

        </div>

        {/* Dual Upload Area */}
        <div className="space-y-4">
          <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
            Chọn Hoặc Kéo Thả File Lên Hệ Thống (.xlsx, .xls, .csv):
          </h4>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            {/* Slot 1: Sales File */}
            <div className={`border-2 border-dashed rounded-2xl p-5 flex flex-col justify-between transition-all ${
              salesFile ? 'border-emerald-500 bg-emerald-50/30' : 'border-slate-300 hover:border-emerald-400 bg-slate-50/50'
            }`}>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                    <TrendingUp className="w-4 h-4 text-emerald-600" />
                    File 1: Doanh Số Bán Hàng
                  </span>
                  {salesFile && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                      Đã chọn
                    </span>
                  )}
                </div>

                {!salesFile ? (
                  <label className="flex flex-col items-center justify-center py-6 cursor-pointer text-center space-y-1">
                    <UploadCloud className="w-8 h-8 text-slate-400" />
                    <span className="text-xs font-semibold text-slate-700">Chọn file Doanh số (.xlsx, .csv)</span>
                    <span className="text-[10px] text-slate-400">Kéo thả file vào khung này</span>
                    <input 
                      type="file" 
                      accept=".xlsx,.xls,.csv" 
                      onChange={(e) => { setSalesFile(e.target.files[0]); setErrorMessage(''); }} 
                      className="hidden" 
                    />
                  </label>
                ) : (
                  <div className="p-3 bg-white border border-emerald-200 rounded-xl space-y-1">
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-bold text-slate-800 truncate">{salesFile.name}</p>
                      <button 
                        onClick={() => setSalesFile(null)} 
                        className="text-red-500 hover:text-red-700 text-[11px] font-semibold cursor-pointer"
                      >
                        Gỡ bỏ
                      </button>
                    </div>
                    <p className="text-[10px] text-slate-500">Kích thước: {(salesFile.size / 1024).toFixed(1)} KB</p>
                  </div>
                )}
              </div>
              <p className="text-[10px] text-slate-400 italic mt-2">Dùng để huấn luyện mô hình XGBoost và nhận diện chu kỳ.</p>
            </div>

            {/* Slot 2: Recipes File */}
            <div className={`border-2 border-dashed rounded-2xl p-5 flex flex-col justify-between transition-all ${
              recipesFile ? 'border-purple-500 bg-purple-50/30' : 'border-slate-300 hover:border-purple-400 bg-slate-50/50'
            }`}>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                    <Layers className="w-4 h-4 text-purple-600" />
                    File 2: Công Thức & Định Lượng (BOM)
                  </span>
                  {recipesFile && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-100 text-purple-800">
                      Đã chọn
                    </span>
                  )}
                </div>

                {!recipesFile ? (
                  <label className="flex flex-col items-center justify-center py-6 cursor-pointer text-center space-y-1">
                    <UploadCloud className="w-8 h-8 text-slate-400" />
                    <span className="text-xs font-semibold text-slate-700">Chọn file Công thức (.xlsx, .csv)</span>
                    <span className="text-[10px] text-slate-400">Kéo thả file vào khung này</span>
                    <input 
                      type="file" 
                      accept=".xlsx,.xls,.csv" 
                      onChange={(e) => { setRecipesFile(e.target.files[0]); setErrorMessage(''); }} 
                      className="hidden" 
                    />
                  </label>
                ) : (
                  <div className="p-3 bg-white border border-purple-200 rounded-xl space-y-1">
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-bold text-slate-800 truncate">{recipesFile.name}</p>
                      <button 
                        onClick={() => setRecipesFile(null)} 
                        className="text-red-500 hover:text-red-700 text-[11px] font-semibold cursor-pointer"
                      >
                        Gỡ bỏ
                      </button>
                    </div>
                    <p className="text-[10px] text-slate-500">Kích thước: {(recipesFile.size / 1024).toFixed(1)} KB</p>
                  </div>
                )}
              </div>
              <p className="text-[10px] text-slate-400 italic mt-2">Hệ thống sẽ <strong>tự động tạo nguyên liệu vào Kho & gắn AI Smart Tag</strong>.</p>
            </div>

          </div>
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-3.5 py-2.5 rounded-xl text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Success Alert */}
        {uploadSuccess && (
          <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-3.5 py-3 rounded-xl text-xs space-y-1">
            <div className="flex items-center gap-2 font-bold">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>{successResult?.message || 'Nạp dữ liệu thành công!'}</span>
            </div>
            <p className="text-[11px] text-emerald-700">Hệ thống đang đồng bộ dữ liệu kho và kích hoạt dự báo nhu cầu...</p>
          </div>
        )}

        {/* Footer Actions */}
        <div className="flex items-center justify-between pt-3 border-t border-slate-100">
          <p className="text-[11px] text-slate-400">
            Hỗ trợ file Excel <code>.xlsx</code>, <code>.xls</code> và CSV tiếng Việt có dấu.
          </p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold cursor-pointer"
            >
              Đóng
            </button>
            <button
              type="button"
              disabled={(!salesFile && !recipesFile) || isUploading || uploadSuccess}
              onClick={handleConfirmUpload}
              className={`inline-flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-semibold shadow-md ${
                (!salesFile && !recipesFile) || isUploading || uploadSuccess
                  ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                  : 'bg-emerald-600 hover:bg-emerald-700 text-white cursor-pointer active:scale-95 shadow-emerald-600/20'
              }`}
            >
              <Sparkles className="w-4 h-4" />
              <span>{isUploading ? 'Đang Xử Lý & Nạp Dữ Liệu...' : 'Xác Nhận Nạp File & Chạy AI'}</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}

