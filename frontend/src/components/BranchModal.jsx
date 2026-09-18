import React, { useState } from 'react';
import { Store, Plus, Trash2, X, Building2, Check } from 'lucide-react';
import { createBranch, deleteBranch } from '../services/api';

export default function BranchModal({ isOpen, onClose, branches, onUpdated, currentBranchId, onSelectBranch }) {
  const [name, setName] = useState('');
  const [address, setAddress] = useState('');
  const [type, setType] = useState('Quán Ăn & Cafe');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      setIsSubmitting(true);
      const newId = 'BRANCH_' + Math.floor(100 + Math.random() * 900);
      await createBranch({
        id: newId,
        name: name.trim(),
        address: address.trim() || 'Việt Nam',
        type: type.trim(),
      });
      setName('');
      setAddress('');
      onSelectBranch(newId);
      onUpdated();
    } catch (err) {
      alert('Lỗi tạo chi nhánh: ' + err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id, branchName) => {
    if (branches.length <= 1) {
      alert('Hệ thống phải có ít nhất 1 chi nhánh!');
      return;
    }
    if (!confirm(`Bạn có chắc chắn muốn xóa chi nhánh "${branchName}"?`)) return;
    try {
      await deleteBranch(id);
      if (currentBranchId === id) {
        const remaining = branches.filter(b => b.id !== id);
        if (remaining.length > 0) onSelectBranch(remaining[0].id);
      }
      onUpdated();
    } catch (err) {
      alert('Lỗi xóa chi nhánh: ' + err.message);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
        
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <Store className="w-5 h-5 text-emerald-600" />
            <h3 className="text-base font-bold text-slate-900">Quản Lý Chi Nhánh / Quán Ăn</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 cursor-pointer">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Existing Branches List */}
        <div className="space-y-2">
          <label className="text-xs font-bold text-slate-500 uppercase">Danh Sách Chi Nhánh Hiện Có ({branches.length})</label>
          <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
            {branches.map((b) => (
              <div 
                key={b.id} 
                className={`flex items-center justify-between p-2.5 rounded-xl border transition-all text-xs ${
                  b.id === currentBranchId 
                    ? 'bg-emerald-50 border-emerald-300 font-semibold' 
                    : 'bg-slate-50 border-slate-200'
                }`}
              >
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold text-slate-800">{b.name}</span>
                    {b.id === currentBranchId && (
                      <span className="text-[10px] bg-emerald-600 text-white px-1.5 py-0.2 rounded-md">Đang chọn</span>
                    )}
                  </div>
                  <span className="text-[11px] text-slate-500 block">{b.address} • {b.type}</span>
                </div>

                <div className="flex items-center gap-1">
                  {b.id !== currentBranchId && (
                    <button
                      onClick={() => onSelectBranch(b.id)}
                      className="px-2 py-1 bg-white border border-slate-200 hover:bg-slate-100 rounded text-slate-700 cursor-pointer"
                    >
                      Chọn
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(b.id, b.name)}
                    className="p-1.5 text-slate-400 hover:text-red-600 rounded hover:bg-red-50 cursor-pointer"
                    title="Xóa chi nhánh"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Add New Branch Form */}
        <form onSubmit={handleCreate} className="space-y-3 pt-3 border-t border-slate-100 text-xs">
          <h4 className="font-bold text-slate-800 flex items-center gap-1">
            <Plus className="w-4 h-4 text-emerald-600" /> Thêm Chi Nhánh Mới
          </h4>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Tên Chi Nhánh / Tên Quán (*)</label>
            <input
              type="text"
              required
              placeholder="Ví dụ: FoodFlow Hoàn Kiếm, Cafe Phố Cổ..."
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Địa Chỉ</label>
              <input
                type="text"
                placeholder="Ví dụ: 15 Tràng Tiền, Hà Nội"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Mô Hình Quán</label>
              <input
                type="text"
                placeholder="Ví dụ: Quán Cơm, Tiệm Trà, Bistro..."
                value={type}
                onChange={(e) => setType(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-semibold cursor-pointer"
            >
              Đóng
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-semibold cursor-pointer shadow-xs"
            >
              {isSubmitting ? 'Đang tạo...' : 'Tạo Chi Nhánh'}
            </button>
          </div>
        </form>

      </div>
    </div>
  );
}
