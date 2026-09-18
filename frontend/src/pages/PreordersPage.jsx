import React, { useState } from 'react';
import { 
  CalendarCheck, 
  Plus, 
  CheckCircle2, 
  Trash2, 
  User, 
  Calendar,
  X,
  Package
} from 'lucide-react';
import { createPreorderMulti, deletePreorder } from '../services/api';
import Pagination from '../components/Pagination';

export default function PreordersPage({ preorders, dishes, branchId, onRefresh }) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [customerName, setCustomerName] = useState('');
  const [date, setDate] = useState('2026-09-18');
  const [note, setNote] = useState('');
  const [orderItems, setOrderItems] = useState([
    { dish_id: dishes?.[0]?.id || 'D01', quantity: 10 }
  ]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const paginatedPreorders = (preorders || []).slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const handleAddItemRow = () => {
    setOrderItems(prev => [...prev, { dish_id: dishes?.[0]?.id || 'D01', quantity: 5 }]);
  };

  const handleRemoveItemRow = (index) => {
    if (orderItems.length <= 1) return;
    setOrderItems(prev => prev.filter((_, i) => i !== index));
  };

  const handleItemChange = (index, field, value) => {
    setOrderItems(prev => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!customerName.trim() || orderItems.length === 0) return;
    try {
      setIsSubmitting(true);
      const itemsPayload = orderItems.map(it => {
        const dishObj = dishes.find(d => d.id === it.dish_id);
        return {
          dish_id: it.dish_id,
          dish_name: dishObj ? dishObj.name : it.dish_id,
          quantity: parseInt(it.quantity) || 1,
        };
      });

      await createPreorderMulti({
        branch_id: branchId,
        date: date,
        customer_name: customerName.trim(),
        note: note.trim(),
        items: itemsPayload,
      });

      setShowAddModal(false);
      setCustomerName('');
      setNote('');
      setOrderItems([{ dish_id: dishes?.[0]?.id || 'D01', quantity: 10 }]);
      if (onRefresh) onRefresh();
    } catch (err) {
      alert('Lỗi tạo đơn đặt trước: ' + err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteOrder = async (id) => {
    if (!confirm('Xóa đơn đặt trước này?')) return;
    try {
      await deletePreorder(id);
      if (onRefresh) onRefresh();
    } catch (err) {
      alert('Lỗi xóa: ' + err.message);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header Banner */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900">Đơn Đặt Trước & Tiệc Đa Món (Pre-orders)</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200">
              Đa Món Trong 1 Đơn
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Cho phép khách hàng đặt nhiều món cùng lúc, hệ thống tự động cộng dồn từng món vào nhu cầu nguyên liệu.
          </p>
        </div>

        <button
          onClick={() => setShowAddModal(true)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-semibold shadow-md shadow-emerald-600/20 transition-all cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>Thêm Đơn Đặt Trước Mới</span>
        </button>
      </div>

      {/* List of Pre-orders with Pagination */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-5 pb-3 border-b border-slate-100">
          <h3 className="text-base font-bold text-slate-900">Danh Sách Đơn Đặt Trước Đã Xác Nhận ({preorders?.length || 0})</h3>
        </div>

        <div className="w-full">
          <table className="w-full text-left text-xs table-fixed">
            <thead>
              <tr className="border-b border-slate-200 font-bold text-slate-500 uppercase bg-slate-50/80">
                <th className="py-2.5 px-2.5 w-[8%]">Mã</th>
                <th className="py-2.5 px-2.5 w-[11%]">Ngày Giao</th>
                <th className="py-2.5 px-2.5 w-[18%]">Khách Hàng</th>
                <th className="py-2.5 px-2.5 w-[36%]">Chi Tiết Các Món Đặt</th>
                <th className="py-2.5 px-2.5 w-[9%] text-right">Tổng Phần</th>
                <th className="py-2.5 px-2.5 w-[13%]">Ghi Chú</th>
                <th className="py-2.5 px-2 w-[5%] text-center">Xóa</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {paginatedPreorders.map((po) => (
                <tr key={po.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-2.5 px-2.5 font-mono text-slate-500 font-semibold align-top">#{po.id}</td>
                  <td className="py-2.5 px-2.5 font-semibold text-slate-900 break-words align-top">{po.date}</td>
                  <td className="py-2.5 px-2.5 font-medium text-slate-800 break-words align-top">
                    <div className="flex items-start gap-1.5">
                      <User className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
                      <span className="break-words leading-tight">{po.customer_name}</span>
                    </div>
                  </td>
                  <td className="py-2.5 px-2.5 align-top">
                    <div className="flex flex-wrap gap-1">
                      {po.items ? (
                        po.items.map((it, idx) => (
                          <span key={idx} className="bg-blue-50 text-blue-800 border border-blue-200 px-1.5 py-0.5 rounded text-[11px] font-semibold break-words leading-tight inline-block">
                            {it.dish_name}: <strong className="text-blue-900">+{it.quantity}</strong>
                          </span>
                        ))
                      ) : (
                        <span className="bg-blue-50 text-blue-800 px-1.5 py-0.5 rounded text-[11px] font-semibold break-words">
                          {po.dish_name}: +{po.quantity}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-2.5 px-2.5 text-right font-bold text-blue-600 text-sm align-top">
                    {po.quantity || (po.items ? po.items.reduce((s, i) => s + i.quantity, 0) : 0)}
                  </td>
                  <td className="py-2.5 px-2.5 text-slate-500 italic break-words text-[11px] align-top">{po.note || '-'}</td>
                  <td className="py-2.5 px-2 text-center align-top">
                    <button
                      onClick={() => handleDeleteOrder(po.id)}
                      className="p-1 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded cursor-pointer"
                      title="Xóa đơn"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <Pagination
          totalItems={preorders?.length || 0}
          pageSize={pageSize}
          currentPage={currentPage}
          onPageChange={setCurrentPage}
          onPageSizeChange={setPageSize}
        />
      </div>

      {/* Modal Add Multi-Dish Preorder */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900">Tạo Đơn Đặt Trước Đa Món</h3>
              <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-slate-600 cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Tên Khách Hàng / Đơn Vị (*)</label>
                  <input
                    type="text"
                    required
                    placeholder="Ví dụ: Anh Hoàng (Họp công ty)"
                    value={customerName}
                    onChange={(e) => setCustomerName(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Ngày Giao / Ăn (*)</label>
                  <input
                    type="date"
                    required
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>
              </div>

              {/* Dynamic Items List */}
              <div className="space-y-2 pt-2 border-t border-slate-100">
                <div className="flex items-center justify-between">
                  <label className="font-bold text-slate-800">Danh Sách Món & Số Lượng Trong Đơn</label>
                  <button
                    type="button"
                    onClick={handleAddItemRow}
                    className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600 hover:text-emerald-700 cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" /> Thêm Món
                  </button>
                </div>

                <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                  {orderItems.map((row, idx) => (
                    <div key={idx} className="flex items-center gap-2 p-2 bg-slate-50 rounded-xl border border-slate-200">
                      <select
                        value={row.dish_id}
                        onChange={(e) => handleItemChange(idx, 'dish_id', e.target.value)}
                        className="flex-1 px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-medium focus:outline-none cursor-pointer"
                      >
                        {dishes?.map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.name} ({d.category})
                          </option>
                        ))}
                      </select>

                      <input
                        type="number"
                        min="1"
                        required
                        value={row.quantity}
                        onChange={(e) => handleItemChange(idx, 'quantity', e.target.value)}
                        className="w-20 px-2 py-1.5 bg-white border border-slate-200 rounded-lg text-xs text-center font-bold"
                        placeholder="Số lượng"
                      />

                      {orderItems.length > 1 && (
                        <button
                          type="button"
                          onClick={() => handleRemoveItemRow(idx)}
                          className="p-1 text-slate-400 hover:text-red-600 rounded cursor-pointer"
                          title="Xóa món"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Ghi Chú Giao Hàng</label>
                <input
                  type="text"
                  placeholder="Ví dụ: Giao trước 11h30 trưa"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-semibold cursor-pointer"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-semibold cursor-pointer shadow-xs"
                >
                  {isSubmitting ? 'Đang lưu...' : 'Xác Nhận Đơn Hàng'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
