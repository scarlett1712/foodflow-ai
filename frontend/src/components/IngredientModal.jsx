import React, { useState, useEffect } from 'react';
import { Sparkles, Plus, Check, AlertCircle, Tag, Eye } from 'lucide-react';
import { smartTagIngredients, createIngredient } from '../services/api';

const TAG_OPTIONS = [
  "🥩 Thịt & Hải sản tươi",
  "🥛 Sữa & Đồ béo",
  "☕ Cà phê & Trà",
  "🍊 Trái cây & Củ quả",
  "🥬 Rau gia vị tươi",
  "🍚 Tinh bột & Bánh",
  "🧋 Topping & Siro",
  "🧂 Gia vị & Khác"
];

export default function IngredientModal({ isOpen, onClose, onAdded, branchId }) {
  const [name, setName] = useState('');
  const [unit, setUnit] = useState('kg');
  const [costPerUnit, setCostPerUnit] = useState('');
  const [shelfLifeDays, setShelfLifeDays] = useState('7');
  const [minStock, setMinStock] = useState('5.0');
  const [initialStock, setInitialStock] = useState('0.0');
  const [categoryTag, setCategoryTag] = useState(TAG_OPTIONS[0]);
  const [isAiTagging, setIsAiTagging] = useState(false);
  const [showReviewStep, setShowReviewStep] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Auto AI Tagging whenever ingredient name changes
  useEffect(() => {
    if (name.trim().length >= 2) {
      const timer = setTimeout(async () => {
        try {
          setIsAiTagging(true);
          const res = await smartTagIngredients([name.trim()]);
          if (res.data?.tags?.[0]?.suggested_tag) {
            setCategoryTag(res.data.tags[0].suggested_tag);
          }
        } catch (e) {
          // ignore
        } finally {
          setIsAiTagging(false);
        }
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [name]);

  if (!isOpen) return null;

  const handleProceedToReview = (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setShowReviewStep(true);
  };

  const handleConfirmSave = async () => {
    try {
      setIsSaving(true);
      const randomId = 'ING_' + Math.floor(1000 + Math.random() * 9000);
      await createIngredient({
        id: randomId,
        name: name.trim(),
        unit: unit.trim(),
        cost_per_unit: parseFloat(costPerUnit) || 0,
        shelf_life_days: parseInt(shelfLifeDays) || 7,
        min_stock: parseFloat(minStock) || 0,
        category_tag: categoryTag,
        initial_stock: parseFloat(initialStock) || 0,
      }, branchId);

      onAdded();
      onClose();
      // Reset form
      setName('');
      setShowReviewStep(false);
    } catch (err) {
      alert('Lỗi lưu nguyên liệu: ' + err.message);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
        
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-base font-bold text-slate-900">
              {showReviewStep ? 'Xác Nhận & Xem Lại Dữ Liệu Nguyên Liệu' : 'Thêm Nguyên Liệu Mới'}
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              {showReviewStep 
                ? 'Kiểm tra lại thông tin và phân nhóm tag AI trước khi lưu lên hệ thống'
                : 'Nhập thông tin nguyên liệu, AI sẽ tự động phân loại tag nhóm phù hợp'}
            </p>
          </div>
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5 text-emerald-600" /> AI Support
          </span>
        </div>

        {/* Step 1: Input Form */}
        {!showReviewStep ? (
          <form onSubmit={handleProceedToReview} className="space-y-3.5 text-xs">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Tên Nguyên Liệu (*)</label>
              <input
                type="text"
                required
                placeholder="Ví dụ: Thịt thăn bò Úc, Sữa tươi tiệt trùng, Cam sành..."
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              />
            </div>

            {/* AI Suggested Tag */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="font-semibold text-slate-700 flex items-center gap-1">
                  <Tag className="w-3.5 h-3.5 text-emerald-600" /> Phân Nhóm Tag Nguyên Liệu
                </label>
                {isAiTagging && (
                  <span className="text-[10px] text-emerald-600 animate-pulse flex items-center gap-1">
                    <Sparkles className="w-3 h-3" /> AI đang gợi ý tag...
                  </span>
                )}
              </div>
              <select
                value={categoryTag}
                onChange={(e) => setCategoryTag(e.target.value)}
                className="w-full px-3 py-2 bg-emerald-50/60 border border-emerald-300 rounded-lg text-xs font-semibold text-emerald-900 focus:ring-2 focus:ring-emerald-500 focus:outline-none cursor-pointer"
              >
                {TAG_OPTIONS.map((tag) => (
                  <option key={tag} value={tag}>{tag}</option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Đơn Vị Tính</label>
                <input
                  type="text"
                  required
                  placeholder="kg, lít, lon, hộp, quả, ổ..."
                  value={unit}
                  onChange={(e) => setUnit(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Giá Vốn Dự Kiến (VNĐ)</label>
                <input
                  type="number"
                  placeholder="Ví dụ: 120000"
                  value={costPerUnit}
                  onChange={(e) => setCostPerUnit(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Hạn Dùng (Ngày)</label>
                <input
                  type="number"
                  value={shelfLifeDays}
                  onChange={(e) => setShelfLifeDays(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Tồn Tối Thiểu (Min)</label>
                <input
                  type="number"
                  step="0.1"
                  value={minStock}
                  onChange={(e) => setMinStock(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Tồn Hiện Tại (Kho)</label>
                <input
                  type="number"
                  step="0.1"
                  value={initialStock}
                  onChange={(e) => setInitialStock(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-semibold cursor-pointer"
              >
                Hủy
              </button>
              <button
                type="submit"
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-semibold cursor-pointer shadow-xs"
              >
                <Eye className="w-3.5 h-3.5" />
                <span>Xem Lại Dữ Liệu (Review)</span>
              </button>
            </div>
          </form>
        ) : (
          /* Step 2: Data Review Preview Screen */
          <div className="space-y-4 text-xs">
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2.5">
              <div className="flex justify-between border-b border-slate-200/60 pb-2">
                <span className="text-slate-500">Tên nguyên liệu:</span>
                <span className="font-bold text-slate-900 text-sm">{name}</span>
              </div>
              <div className="flex justify-between border-b border-slate-200/60 pb-2">
                <span className="text-slate-500">Tag Nhóm Phân Loại:</span>
                <span className="font-semibold text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded">{categoryTag}</span>
              </div>
              <div className="flex justify-between border-b border-slate-200/60 pb-2">
                <span className="text-slate-500">Đơn vị & Giá vốn:</span>
                <span className="font-medium text-slate-800">{unit} • {parseFloat(costPerUnit || 0).toLocaleString('vi-VN')} VNĐ/{unit}</span>
              </div>
              <div className="flex justify-between border-b border-slate-200/60 pb-2">
                <span className="text-slate-500">Hạn sử dụng:</span>
                <span className="font-medium text-slate-800">{shelfLifeDays} ngày</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Mức tồn tối thiểu / Tồn kho ban đầu:</span>
                <span className="font-medium text-slate-800">{minStock} {unit} / {initialStock} {unit}</span>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setShowReviewStep(false)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-semibold cursor-pointer"
              >
                Quay Lại Sửa
              </button>
              <button
                type="button"
                onClick={handleConfirmSave}
                disabled={isSaving}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-semibold cursor-pointer shadow-xs"
              >
                <Check className="w-3.5 h-3.5" />
                <span>{isSaving ? 'Đang lưu...' : 'Xác Nhận Lưu Lên Web'}</span>
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
