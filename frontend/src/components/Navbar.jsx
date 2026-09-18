import React, { useState } from 'react';
import { 
  ChefHat, 
  Sparkles, 
  RefreshCw, 
  Store, 
  CheckCircle2, 
  UploadCloud, 
  Plus, 
  Database,
  RotateCcw
} from 'lucide-react';

export default function Navbar({ 
  branches, 
  selectedBranch, 
  onSelectBranch, 
  onOpenBranchModal,
  onOpenUploadModal,
  onResetDemo,
  onClearClean,
  onRetrain, 
  isRetraining, 
  lastRetrainInfo 
}) {
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');

  const handleRetrainClick = async () => {
    await onRetrain();
    setToastMessage('Đã huấn luyện lại mô hình AI thành công!');
    setShowToast(true);
    setTimeout(() => setShowToast(false), 4000);
  };

  const handleDemoClick = async () => {
    if (confirm('Nạp lại toàn bộ dữ liệu mẫu F&B (3 chi nhánh, 22 món, 35 nguyên liệu)?')) {
      await onResetDemo();
      setToastMessage('Đã nạp lại dữ liệu mẫu Demo thành công!');
      setShowToast(true);
      setTimeout(() => setShowToast(false), 4000);
    }
  };

  const handleClearClick = async () => {
    if (confirm('Xóa dữ liệu để trở về trạng thái Trắng (Clean Slate) để tự nhập từ đầu?')) {
      await onClearClean();
      setToastMessage('Đã chuyển về trạng thái Trắng! Bạn có thể tự thêm chi nhánh, món ăn, tải file lên.');
      setShowToast(true);
      setTimeout(() => setShowToast(false), 4000);
    }
  };

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-40 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Brand Logo */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center text-white shadow-md shadow-emerald-500/20">
              <ChefHat className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-xl tracking-tight text-slate-900">FoodFlow</span>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
                  <Sparkles className="w-3 h-3 text-emerald-600" /> AI Engine
                </span>
              </div>
              <p className="text-xs text-slate-500 hidden sm:block">Dự đoán nhu cầu & Gợi ý mua nguyên liệu F&B</p>
            </div>
          </div>

          {/* Right Controls */}
          <div className="flex items-center gap-2 sm:gap-3">
            
            {/* Branch Selector + Manage Button */}
            <div className="flex items-center bg-slate-100/80 rounded-lg border border-slate-200 p-0.5">
              <div className="flex items-center gap-1.5 px-2.5 py-1">
                <Store className="w-4 h-4 text-slate-500" />
                <select
                  value={selectedBranch}
                  onChange={(e) => onSelectBranch(e.target.value)}
                  className="bg-transparent text-xs font-semibold text-slate-800 focus:outline-none cursor-pointer max-w-[150px] sm:max-w-[180px] truncate"
                >
                  {branches.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name}
                    </option>
                  ))}
                </select>
              </div>

              <button
                onClick={onOpenBranchModal}
                className="p-1.5 hover:bg-slate-200 rounded-md text-slate-600 cursor-pointer"
                title="Quản lý / Thêm chi nhánh mới"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Solana Devnet Badge */}
            <a
              href="https://explorer.solana.com/address/29qNdUWXW5cqyojHkkhViHRdh7ro5AVoqBWwzSXgJCRA?cluster=devnet"
              target="_blank"
              rel="noopener noreferrer"
              className="hidden lg:inline-flex items-center gap-1.5 px-2.5 py-1.5 bg-gradient-to-r from-purple-50 to-indigo-50 hover:from-purple-100 hover:to-indigo-100 text-purple-900 rounded-lg text-xs font-semibold border border-purple-200/80 transition-all cursor-pointer shadow-2xs group"
              title="Solana Devnet: Online. Nhấn để xem Authority Wallet trên Solana Explorer."
            >
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-purple-700 group-hover:text-purple-900">Solana Devnet</span>
            </a>

            {/* Upload Data Hub Button */}
            <button
              onClick={onOpenUploadModal}
              className="hidden lg:inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 rounded-lg text-xs font-bold border border-emerald-300 transition-all cursor-pointer shadow-2xs"
              title="Tải lên file dữ liệu Doanh số & Công thức món ăn (Excel / CSV)"
            >
              <UploadCloud className="w-3.5 h-3.5 text-emerald-600" />
              <span>Nhập File Excel / CSV</span>
            </button>

            {/* Demo / Reset Toggle */}
            <div className="hidden xl:flex items-center gap-1 bg-slate-50 border border-slate-200 p-1 rounded-lg">
              <button
                onClick={handleDemoClick}
                className="px-2 py-1 text-[11px] font-semibold text-slate-600 hover:text-emerald-700 hover:bg-emerald-50 rounded cursor-pointer"
                title="Nạp bộ dữ liệu mẫu F&B để demo"
              >
                Nạp Dữ Liệu Mẫu
              </button>
              <button
                onClick={handleClearClick}
                className="px-2 py-1 text-[11px] font-semibold text-slate-400 hover:text-red-600 hover:bg-red-50 rounded cursor-pointer"
                title="Xóa dữ liệu để nhập mới hoàn toàn từ đầu"
              >
                Dữ Liệu Trắng
              </button>
            </div>

            {/* Retrain Model Action Button */}
            <button
              onClick={handleRetrainClick}
              disabled={isRetraining}
              className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all shadow-xs ${
                isRetraining
                  ? 'bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200'
                  : 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-600/20 active:scale-95 cursor-pointer'
              }`}
              title="Chạy huấn luyện lại mô hình AI với dữ liệu mới"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRetraining ? 'animate-spin' : ''}`} />
              <span className="hidden md:inline">{isRetraining ? 'Đang train AI...' : 'Huấn Luyện Lại Model'}</span>
            </button>
          </div>

        </div>
      </div>

      {/* Toast Notification */}
      {showToast && (
        <div className="bg-emerald-50 border-b border-emerald-200 px-4 py-2 text-xs text-emerald-800 flex items-center justify-center gap-2 animate-fadeIn">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          <span>{toastMessage}</span>
        </div>
      )}
    </header>
  );
}
