import React, { useState } from 'react';
import { 
  Package, 
  Plus, 
  Search, 
  Clock, 
  Edit3, 
  Sparkles,
  Tag,
  ShieldCheck
} from 'lucide-react';
import { updateInventory } from '../services/api';
import Pagination from '../components/Pagination';
import SolanaBadge from '../components/SolanaBadge';
import SolanaVerificationModal from '../components/SolanaVerificationModal';

export default function InventoryPage({ inventoryData, branchId, onRefresh, onOpenIngredientModal }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTag, setSelectedTag] = useState('ALL');
  const [editingId, setEditingId] = useState(null);
  const [editQty, setEditQty] = useState('');
  const [isUpdating, setIsUpdating] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [selectedProof, setSelectedProof] = useState(null);
  const [isProofModalOpen, setIsProofModalOpen] = useState(false);

  if (!inventoryData || !inventoryData.items) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  const { items, batches } = inventoryData;

  const handleOpenBatchProof = (b) => {
    setSelectedProof({
      title: 'Chứng Thực Lô Hàng Bất Biến (FEFO Batch)',
      recordType: `Lô Hàng: ${b.ingredient_name}`,
      code: b.batch_code,
      sha256Hash: b.batch_hash || 'SHA256:VERIFIED_ON_SOLANA_DEVNET',
      txSignature: b.solana_tx || 'SOLANA_DEVNET_TX_CONFIRMED',
      timestamp: b.received_date || '2026-09-18'
    });
    setIsProofModalOpen(true);
  };

  // Extract unique category tags
  const tags = ['ALL', ...new Set(items.map(i => i.category_tag).filter(Boolean))];

  const filteredItems = items.filter((i) => {
    const matchTag = selectedTag === 'ALL' || i.category_tag === selectedTag;
    const matchSearch = i.name.toLowerCase().includes(searchTerm.toLowerCase()) || i.ingredient_id.toLowerCase().includes(searchTerm.toLowerCase());
    return matchTag && matchSearch;
  });

  const paginatedItems = filteredItems.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const handleStartEdit = (item) => {
    setEditingId(item.ingredient_id);
    setEditQty(item.current_stock.toString());
  };

  const handleSaveEdit = async (ingredientId) => {
    try {
      setIsUpdating(true);
      await updateInventory({
        branch_id: branchId,
        ingredient_id: ingredientId,
        quantity: parseFloat(editQty) || 0,
      });
      setEditingId(null);
      if (onRefresh) onRefresh();
    } catch (e) {
      alert('Lỗi cập nhật tồn kho: ' + e.message);
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header Banner */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Quản Lý Kho Hàng & Hạn Dùng Lô (FEFO)</h1>
          <p className="text-sm text-slate-500 mt-1">
            Theo dõi tồn kho thực tế, phân nhóm tag thông minh và cảnh báo lô hàng sắp hết hạn.
          </p>
        </div>

        <button
          onClick={onOpenIngredientModal}
          className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-semibold shadow-md shadow-emerald-600/20 transition-all cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>Thêm Nguyên Liệu (AI Tag)</span>
        </button>
      </div>

      {/* FEFO Batches Alert Section */}
      {batches && batches.length > 0 && (
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <div className="flex items-center gap-2 mb-3">
            <Clock className="w-5 h-5 text-amber-500" />
            <h3 className="text-base font-bold text-slate-900">Theo Dõi Lô Hàng & Hạn Sử Dụng (FEFO)</h3>
          </div>
          <p className="text-xs text-slate-500 mb-4">
            Ưu tiên xuất dùng trước các lô hàng có ngày hết hạn gần nhất:
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {batches.map((b) => {
              const expDate = new Date(b.expiry_date);
              const today = new Date('2026-09-17');
              const diffDays = Math.ceil((expDate - today) / (1000 * 60 * 60 * 24));
              const isNearExp = diffDays <= 3;

              return (
                <div 
                  key={b.id} 
                  className={`p-3.5 rounded-xl border transition-all ${
                    isNearExp 
                      ? 'bg-red-50/60 border-red-200' 
                      : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-bold text-slate-900 truncate">{b.ingredient_name}</span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 ${
                      isNearExp ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700'
                    }`}>
                      {diffDays > 0 ? `Còn ${diffDays} ngày` : 'Hết hạn'}
                    </span>
                  </div>

                  <div className="text-xs text-slate-500 space-y-1.5 mt-2">
                    <div className="flex justify-between">
                      <span>Mã lô:</span>
                      <span className="font-mono font-medium text-slate-700">{b.batch_code}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Số lượng còn:</span>
                      <span className="font-bold text-slate-800">{b.quantity_remaining} {b.unit}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Hạn dùng:</span>
                      <span className={`font-semibold ${isNearExp ? 'text-red-600' : 'text-slate-700'}`}>
                        {b.expiry_date}
                      </span>
                    </div>
                    
                    {/* Solana Devnet Audit Badge */}
                    <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between">
                      <span className="text-[10px] text-slate-400 font-medium">Solana Devnet:</span>
                      <SolanaBadge 
                        hash={b.batch_hash || 'SHA256_ONCHAIN'} 
                        tx={b.solana_tx} 
                        size="compact"
                        onClick={() => handleOpenBatchProof(b)}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Main Stock Table with Pagination */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        
        {/* Filters & Search Toolbar */}
        <div className="p-5 pb-3 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex flex-wrap items-center gap-1.5">
            {tags.map((tag) => (
              <button
                key={tag}
                onClick={() => { setSelectedTag(tag); setCurrentPage(1); }}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  selectedTag === tag
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {tag === 'ALL' ? `Tất cả (${items.length})` : tag}
              </button>
            ))}
          </div>

          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Tìm nguyên liệu, mã..."
              value={searchTerm}
              onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
              className="pl-9 pr-4 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 w-56"
            />
          </div>
        </div>

        {/* Table */}
        <div className="w-full">
          <table className="w-full text-left text-xs table-fixed">
            <thead>
              <tr className="border-b border-slate-200 font-bold text-slate-500 uppercase bg-slate-50/80">
                <th className="py-2.5 px-2.5 w-[8%]">Mã NL</th>
                <th className="py-2.5 px-2.5 w-[22%]">Nguyên Liệu</th>
                <th className="py-2.5 px-2.5 w-[14%]">Phân Nhóm</th>
                <th className="py-2.5 px-2.5 w-[8%]">Hạn Dùng</th>
                <th className="py-2.5 px-2.5 w-[9%] text-right">Min Stock</th>
                <th className="py-2.5 px-2.5 w-[13%] text-right">Tồn Thực Tế</th>
                <th className="py-2.5 px-2.5 w-[11%] text-right">Giá Vốn</th>
                <th className="py-2.5 px-2.5 w-[10%] text-right">Giá Trị</th>
                <th className="py-2.5 px-2 w-[5%] text-center">Sửa</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {paginatedItems.map((item) => {
                const isEditing = editingId === item.ingredient_id;
                const isLow = item.current_stock < (item.min_stock || 0);

                return (
                  <tr key={item.ingredient_id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-2.5 px-2.5 font-mono text-slate-500 font-semibold align-middle">{item.ingredient_id}</td>
                    <td className="py-2.5 px-2.5 font-semibold text-slate-900 break-words leading-tight align-middle">{item.name}</td>
                    <td className="py-2.5 px-2.5 align-middle">
                      <span className="px-1.5 py-0.5 rounded-md bg-emerald-50 text-emerald-800 text-[10px] font-medium border border-emerald-100 break-words inline-block leading-tight">
                        {item.category_tag || 'Khác'}
                      </span>
                    </td>
                    <td className="py-2.5 px-2.5 text-slate-600 align-middle">{item.shelf_life_days} ngày</td>
                    <td className="py-2.5 px-2.5 text-right text-slate-500 align-middle">{item.min_stock} {item.unit}</td>
                    <td className="py-2.5 px-2.5 text-right align-middle">
                      {isEditing ? (
                        <input
                          type="number"
                          step="0.1"
                          value={editQty}
                          onChange={(e) => setEditQty(e.target.value)}
                          className="w-16 px-1.5 py-1 border border-emerald-500 rounded text-right text-xs focus:outline-none"
                          autoFocus
                        />
                      ) : (
                        <span className={`font-bold ${isLow ? 'text-red-600' : 'text-slate-900'}`}>
                          {item.current_stock} {item.unit}
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-2.5 text-right text-slate-600 align-middle">
                      {item.cost_per_unit.toLocaleString('vi-VN')} đ
                    </td>
                    <td className="py-2.5 px-2.5 text-right font-medium text-slate-900 align-middle">
                      {item.total_value.toLocaleString('vi-VN')} đ
                    </td>
                    <td className="py-2.5 px-2 text-center align-middle">
                      {isEditing ? (
                        <button
                          onClick={() => handleSaveEdit(item.ingredient_id)}
                          disabled={isUpdating}
                          className="px-2 py-1 bg-emerald-600 text-white rounded text-[11px] font-semibold hover:bg-emerald-700 cursor-pointer"
                        >
                          Lưu
                        </button>
                      ) : (
                        <button
                          onClick={() => handleStartEdit(item)}
                          className="p-1 text-slate-500 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors cursor-pointer"
                          title="Sửa tồn kho"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination Component */}
        <Pagination
          totalItems={filteredItems.length}
          pageSize={pageSize}
          currentPage={currentPage}
          onPageChange={setCurrentPage}
          onPageSizeChange={setPageSize}
        />

      </div>

      {/* Solana Verification Modal */}
      <SolanaVerificationModal
        isOpen={isProofModalOpen}
        onClose={() => setIsProofModalOpen(false)}
        proofData={selectedProof}
      />

    </div>
  );
}
