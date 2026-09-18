import React, { useState, useEffect } from 'react';
import { 
  ShoppingCart, 
  AlertTriangle, 
  CheckCircle2, 
  Download, 
  Printer, 
  Search, 
  DollarSign, 
  History, 
  UploadCloud, 
  Check, 
  PackageCheck,
  Calendar,
  ShieldCheck
} from 'lucide-react';
import { getPurchaseHistory, recordManualPurchase } from '../services/api';
import Pagination from '../components/Pagination';
import SolanaBadge from '../components/SolanaBadge';
import SolanaVerificationModal from '../components/SolanaVerificationModal';
import VarianceExplanationModal from '../components/VarianceExplanationModal';

export default function PurchasePage({ purchaseData, branchId, onRefresh, onOpenPurchaseUploadModal }) {
  const [subTab, setSubTab] = useState('recommendations'); // 'recommendations' | 'history'
  
  // Recommendations state
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');
  const [checkedItems, setCheckedItems] = useState({});
  const [isCopied, setIsCopied] = useState(false);
  const [isRecordingManual, setIsRecordingManual] = useState(false);
  const [recPage, setRecPage] = useState(1);
  const [recPageSize, setRecPageSize] = useState(10);

  // Variance Modal State
  const [isVarianceModalOpen, setIsVarianceModalOpen] = useState(false);
  const [pendingItemsToSubmit, setPendingItemsToSubmit] = useState([]);

  // History state
  const [purchaseHistoryList, setPurchaseHistoryList] = useState([]);
  const [historySearch, setHistorySearch] = useState('');
  const [histPage, setHistPage] = useState(1);
  const [histPageSize, setHistPageSize] = useState(10);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Solana Proof Modal State
  const [selectedProof, setSelectedProof] = useState(null);
  const [isProofModalOpen, setIsProofModalOpen] = useState(false);

  const handleOpenPoProof = (item) => {
    setSelectedProof({
      title: 'Chứng Thực Đơn Nhập Hàng (Purchase Audit Proof)',
      recordType: `Nhập Hàng: ${item.ingredient_name}`,
      code: item.batch_code || `PO-${item.date}-${item.ingredient_id}`,
      sha256Hash: item.record_hash || 'SHA256:SOLANA_DEVNET_AUDITED_PO',
      txSignature: item.solana_tx || 'SOLANA_DEVNET_CONFIRMED_TX',
      timestamp: item.date || '2026-09-18',
      variancePct: item.variance_pct || 0,
      varianceReason: item.variance_reason || '',
      aiVerdict: item.ai_verdict || 'COMPLIANT',
      aiNotes: item.ai_notes || '',
      aiAdjustment: item.ai_adjustment || ''
    });
    setIsProofModalOpen(true);
  };

  // Fetch purchase history when switching to history tab
  const fetchHistory = async () => {
    try {
      setLoadingHistory(true);
      const res = await getPurchaseHistory(branchId);
      setPurchaseHistoryList(res.data || []);
    } catch (e) {
      console.error('Error fetching purchase history:', e);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    if (subTab === 'history') {
      fetchHistory();
    }
  }, [subTab, branchId]);

  if (!purchaseData || !purchaseData.recommendations) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  const { target_date, branch, summary, recommendations } = purchaseData;

  const formatVND = (num) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(num || 0);
  };

  // Recommendations filtering
  const filteredRecs = recommendations.filter((item) => {
    let matchStatus = true;
    if (filterStatus === 'TO_BUY') {
      matchStatus = item.status === 'CRITICAL' || item.status === 'WARNING';
    } else if (filterStatus === 'CRITICAL') {
      matchStatus = item.status === 'CRITICAL';
    } else if (filterStatus === 'SUFFICIENT') {
      matchStatus = item.status === 'SUFFICIENT' || item.status === 'EXCESS';
    }

    const matchSearch = item.ingredient_name.toLowerCase().includes(searchTerm.toLowerCase()) || item.ingredient_id.toLowerCase().includes(searchTerm.toLowerCase());
    return matchStatus && matchSearch;
  });

  const paginatedRecs = filteredRecs.slice((recPage - 1) * recPageSize, recPage * recPageSize);

  // History filtering
  const filteredHistory = purchaseHistoryList.filter((item) => {
    return item.ingredient_name.toLowerCase().includes(historySearch.toLowerCase()) || 
           item.date.includes(historySearch) || 
           (item.batch_code && item.batch_code.toLowerCase().includes(historySearch.toLowerCase()));
  });

  const paginatedHistory = filteredHistory.slice((histPage - 1) * histPageSize, histPage * histPageSize);

  const handleToggleCheck = (id) => {
    setCheckedItems(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const handlePrint = () => {
    window.print();
  };

  const handleExportText = () => {
    const toBuyList = recommendations.filter(i => i.recommended_purchase > 0);
    const text = `PHIẾU ĐI CHỢ & NHẬP HÀNG - ${branch.name}\nNgày: ${target_date}\n` +
      `Tổng ngân sách dự kiến: ${formatVND(summary.total_estimated_purchase_cost)}\n` +
      `-----------------------------------------\n` +
      toBuyList.map((i, idx) => `${idx + 1}. ${i.ingredient_name}: ${i.recommended_purchase} ${i.unit} (Ước tính: ${formatVND(i.estimated_cost)})`).join('\n');
    
    navigator.clipboard.writeText(text);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 3000);
  };

  // Xác nhận nhập kho các mặt hàng đã tick hoặc toàn bộ các mặt hàng cần mua
  const handleConfirmStockIn = () => {
    const selectedRecs = recommendations.filter(i => {
      if (Object.keys(checkedItems).some(k => checkedItems[k])) {
        return checkedItems[i.ingredient_id] && i.recommended_purchase > 0;
      }
      return i.recommended_purchase > 0;
    });

    if (selectedRecs.length === 0) {
      alert('Không có mặt hàng nào cần nhập kho!');
      return;
    }

    const itemsPayload = selectedRecs.map(i => ({
      ingredient_id: i.ingredient_id,
      ingredient_name: i.ingredient_name,
      quantity: i.recommended_purchase,
      unit: i.unit,
      cost_per_unit: i.cost_per_unit,
    }));

    setPendingItemsToSubmit(itemsPayload);
    setIsVarianceModalOpen(true);
  };

  const handleConfirmWithVarianceReason = async (reason, assessment) => {
    try {
      setIsRecordingManual(true);
      const res = await recordManualPurchase({
        branch_id: branchId,
        date: target_date,
        items: pendingItemsToSubmit,
        variance_reason: reason,
        ai_assessment: assessment
      });

      setIsVarianceModalOpen(false);
      setCheckedItems({});
      if (onRefresh) onRefresh();

      if (res.data?.solana_proof) {
        setSelectedProof({
          title: 'Chứng Thực Đơn Nhập Hàng Bất Biến (Solana Devnet)',
          recordType: 'Xác Nhận Đơn Mua Hàng AI (PO Confirmation)',
          code: `PO-${target_date.replace(/-/g, '')}`,
          sha256Hash: res.data.solana_proof.record_hash,
          txSignature: res.data.solana_proof.tx_signature,
          timestamp: res.data.solana_proof.notarized_at,
          variancePct: res.data.solana_proof.variance_pct,
          varianceReason: res.data.solana_proof.variance_reason,
          aiVerdict: res.data.solana_proof.ai_verdict,
          aiNotes: res.data.ai_assessment?.ai_notes,
          aiAdjustment: res.data.ai_assessment?.adjustment_strategy
        });
        setIsProofModalOpen(true);
      } else {
        alert(res.data.message);
      }
    } catch (e) {
      alert('Lỗi nhập kho: ' + e.message);
    } finally {
      setIsRecordingManual(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header Banner */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900">Quản Lý Đi Chợ & Nhập Kho Nguyên Liệu</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
              {subTab === 'recommendations' ? `Ngày áp dụng: ${target_date}` : 'Lịch Sử Nhập Hàng'}
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Gợi ý mua hàng thông minh và theo dõi toàn bộ lịch sử chi phí đi chợ của nhà hàng.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Sub-tab switcher */}
          <div className="bg-slate-100 p-1 rounded-xl flex items-center gap-1 border border-slate-200">
            <button
              onClick={() => setSubTab('recommendations')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                subTab === 'recommendations'
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Gợi Ý Mua Hàng
            </button>
            <button
              onClick={() => setSubTab('history')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
                subTab === 'history'
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <History className="w-3.5 h-3.5" />
              <span>Lịch Sử Đi Chợ</span>
            </button>
          </div>

          {/* Upload Purchase CSV Button */}
          <button
            onClick={onOpenPurchaseUploadModal}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-xs font-semibold shadow-xs transition-all cursor-pointer"
            title="Tải lên file CSV lịch sử đi chợ để cập nhật tồn kho tự động"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Nhập File Đi Chợ</span>
          </button>
        </div>
      </div>

      {subTab === 'recommendations' ? (
        <>
          {/* Summary KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase">Mặt Hàng Cần Nhập</p>
                <h3 className="text-2xl font-bold text-slate-900 mt-1">
                  {summary.total_items_to_buy} <span className="text-xs font-normal text-slate-500">/ {recommendations.length} nguyên liệu</span>
                </h3>
                <p className="text-xs text-red-600 font-medium mt-0.5">
                  Trong đó có <strong>{summary.critical_shortage_items}</strong> mặt hàng thiếu khẩn cấp
                </p>
              </div>
              <div className="p-3 rounded-xl bg-amber-50 text-amber-600">
                <ShoppingCart className="w-6 h-6" />
              </div>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase">Ngân Sách Đi Chợ Dự Kiến</p>
                <h3 className="text-2xl font-bold text-purple-900 mt-1">
                  {formatVND(summary.total_estimated_purchase_cost)}
                </h3>
                <p className="text-xs text-slate-500 font-medium mt-0.5">
                  Giá vốn nguyên vật liệu (COGS)
                </p>
              </div>
              <div className="p-3 rounded-xl bg-purple-50 text-purple-600">
                <DollarSign className="w-6 h-6" />
              </div>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase">Biên Lợi Nhuận Gộp Dự Kiến</p>
                <h3 className="text-2xl font-bold text-emerald-600 mt-1">
                  {summary.profit_margin_estimated}%
                </h3>
                <p className="text-xs text-slate-500 font-medium mt-0.5">
                  Doanh thu: {formatVND(summary.total_estimated_sales_revenue)}
                </p>
              </div>
              <div className="p-3 rounded-xl bg-emerald-50 text-emerald-600">
                <CheckCircle2 className="w-6 h-6" />
              </div>
            </div>
          </div>

          {/* Main Recommendations Table */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
            
            {/* Filter & Action Toolbar */}
            <div className="p-5 pb-3 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div className="flex flex-wrap items-center gap-1.5">
                <button
                  onClick={() => { setFilterStatus('ALL'); setRecPage(1); }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    filterStatus === 'ALL' ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  Tất cả ({recommendations.length})
                </button>
                <button
                  onClick={() => { setFilterStatus('TO_BUY'); setRecPage(1); }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    filterStatus === 'TO_BUY' ? 'bg-amber-600 text-white' : 'bg-amber-50 text-amber-700 hover:bg-amber-100'
                  }`}
                >
                  Cần Nhập Hàng ({summary.total_items_to_buy})
                </button>
                <button
                  onClick={() => { setFilterStatus('CRITICAL'); setRecPage(1); }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    filterStatus === 'CRITICAL' ? 'bg-red-600 text-white' : 'bg-red-50 text-red-700 hover:bg-red-100'
                  }`}
                >
                  Thiếu Khẩn Cấp ({summary.critical_shortage_items})
                </button>
                <button
                  onClick={() => { setFilterStatus('SUFFICIENT'); setRecPage(1); }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    filterStatus === 'SUFFICIENT' ? 'bg-emerald-600 text-white' : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
                  }`}
                >
                  Đủ / Tồn Dư ({recommendations.length - summary.total_items_to_buy})
                </button>
              </div>

              <div className="flex items-center gap-2">
                <div className="relative">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    placeholder="Tìm nguyên liệu..."
                    value={searchTerm}
                    onChange={(e) => { setSearchTerm(e.target.value); setRecPage(1); }}
                    className="pl-9 pr-4 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 w-48"
                  />
                </div>

                <button
                  onClick={handleExportText}
                  className="p-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition-all cursor-pointer"
                  title="Sao chép danh sách đi chợ"
                >
                  <Download className="w-4 h-4" />
                </button>

                <button
                  onClick={handlePrint}
                  className="p-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition-all cursor-pointer"
                  title="In phiếu đi chợ"
                >
                  <Printer className="w-4 h-4" />
                </button>

                <button
                  onClick={handleConfirmStockIn}
                  disabled={isRecordingManual}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold shadow-xs transition-all cursor-pointer"
                  title="Xác nhận đã mua và tự động cộng dồn số lượng vào kho"
                >
                  <PackageCheck className="w-4 h-4" />
                  <span>{isRecordingManual ? 'Đang cập nhật kho...' : 'Xác Nhận Nhập Kho'}</span>
                </button>
              </div>
            </div>

            {/* Recommendations Table */}
            <div className="w-full">
              <table className="w-full text-left text-xs table-fixed">
                <thead>
                  <tr className="border-b border-slate-200 font-bold text-slate-500 uppercase bg-slate-50/80">
                    <th className="py-2.5 px-2 w-[4%] text-center">Mua</th>
                    <th className="py-2.5 px-2 w-[22%]">Nguyên Liệu</th>
                    <th className="py-2.5 px-2 w-[9%] text-right">Cần Dùng</th>
                    <th className="py-2.5 px-2 w-[9%] text-right">Tồn Kho</th>
                    <th className="py-2.5 px-2 w-[9%] text-right">Thiếu Hụt</th>
                    <th className="py-2.5 px-2 w-[14%] text-right bg-emerald-50/70 text-emerald-900 font-bold">CẦN MUA</th>
                    <th className="py-2.5 px-2 w-[10%] text-right">Đơn Giá</th>
                    <th className="py-2.5 px-2 w-[11%] text-right">Thành Tiền</th>
                    <th className="py-2.5 px-2 w-[12%] text-center">Trạng Thái</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {paginatedRecs.map((item) => {
                    const isChecked = !!checkedItems[item.ingredient_id];
                    return (
                      <tr 
                        key={item.ingredient_id} 
                        className={`hover:bg-slate-50/80 transition-colors ${
                          isChecked ? 'bg-slate-50 opacity-60 line-through' : ''
                        }`}
                      >
                        <td className="py-2.5 px-2 text-center align-middle">
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => handleToggleCheck(item.ingredient_id)}
                            className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 cursor-pointer w-4 h-4"
                          />
                        </td>
                        <td className="py-2.5 px-2 font-semibold text-slate-900 break-words leading-tight align-middle">
                          {item.ingredient_name}
                          <span className="block text-[10px] font-normal text-slate-400">Mã: {item.ingredient_id} • {item.unit}</span>
                        </td>
                        <td className="py-2.5 px-2 text-right font-medium text-slate-700 align-middle">
                          {item.required_quantity} {item.unit}
                        </td>
                        <td className="py-2.5 px-2 text-right font-medium text-slate-700 align-middle">
                          {item.current_stock} {item.unit}
                        </td>
                        <td className="py-2.5 px-2 text-right font-medium text-red-600 align-middle">
                          {item.shortage > 0 ? `${item.shortage} ${item.unit}` : '-'}
                        </td>
                        <td className="py-2.5 px-2 text-right bg-emerald-50/60 align-middle">
                          <span className={`text-xs font-bold ${
                            item.recommended_purchase > 0 ? 'text-emerald-700' : 'text-slate-400 font-normal'
                          }`}>
                            {item.recommended_purchase > 0 ? `${item.recommended_purchase} ${item.unit}` : '0'}
                          </span>
                        </td>
                        <td className="py-2.5 px-2 text-right text-slate-500 align-middle">
                          {formatVND(item.cost_per_unit)}
                        </td>
                        <td className="py-2.5 px-2 text-right font-semibold text-slate-900 align-middle">
                          {item.estimated_cost > 0 ? formatVND(item.estimated_cost) : '-'}
                        </td>
                        <td className="py-2.5 px-2 text-center align-middle">
                          <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[10px] font-bold leading-tight ${
                            item.status === 'CRITICAL' ? 'bg-red-100 text-red-700 border border-red-200' :
                            item.status === 'WARNING' ? 'bg-amber-100 text-amber-700 border border-amber-200' :
                            item.status === 'EXCESS' ? 'bg-blue-100 text-blue-700 border border-blue-200' :
                            'bg-emerald-100 text-emerald-700 border border-emerald-200'
                          }`}>
                            {item.status === 'CRITICAL' && <AlertTriangle className="w-3 h-3 shrink-0" />}
                            {item.status === 'SUFFICIENT' && <CheckCircle2 className="w-3 h-3 shrink-0" />}
                            <span className="truncate">{item.status_text}</span>
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <Pagination
              totalItems={filteredRecs.length}
              pageSize={recPageSize}
              currentPage={recPage}
              onPageChange={setRecPage}
              onPageSizeChange={setRecPageSize}
            />
          </div>
        </>
      ) : (
        /* Sub-tab 2: Purchase History Screen */
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="p-5 pb-3 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <h3 className="text-base font-bold text-slate-900">Lịch Sử Mua Hàng & Nhập Kho Thực Tế ({purchaseHistoryList.length})</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Các đợt đi chợ đã ghi nhận hoặc được nạp từ file CSV. Tồn kho đã được tự động đồng bộ.
              </p>
            </div>

            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Tìm ngày, nguyên liệu, mã lô..."
                value={historySearch}
                onChange={(e) => { setHistorySearch(e.target.value); setHistPage(1); }}
                className="pl-9 pr-4 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 w-64"
              />
            </div>
          </div>

          <div className="w-full">
            <table className="w-full text-left text-xs table-fixed">
              <thead>
                <tr className="border-b border-slate-200 font-bold text-slate-500 uppercase bg-slate-50/80">
                  <th className="py-2.5 px-2 w-[9%]">Ngày Mua</th>
                  <th className="py-2.5 px-2 w-[17%]">Tên Nguyên Liệu</th>
                  <th className="py-2.5 px-2 w-[8%] text-right">Số Lượng</th>
                  <th className="py-2.5 px-2 w-[9%] text-right">Đơn Giá</th>
                  <th className="py-2.5 px-2 w-[10%] text-right font-bold">Tổng Tiền</th>
                  <th className="py-2.5 px-2 w-[23%]">Kiểm Toán Chênh Lệch & AI</th>
                  <th className="py-2.5 px-2 w-[12%]">Mã Lô</th>
                  <th className="py-2.5 px-2 w-[12%] text-center">Xác Thực Solana</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loadingHistory ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-slate-400">Đang tải lịch sử mua hàng...</td>
                  </tr>
                ) : paginatedHistory.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-slate-400 italic">Chưa có bản ghi mua hàng nào. Nhấn "Nhập File Đi Chợ" để nạp dữ liệu!</td>
                  </tr>
                ) : (
                  paginatedHistory.map((item) => {
                    const varPct = Number(item.variance_pct || 0);
                    const hasReason = !!item.variance_reason;
                    const verdict = item.ai_verdict || (hasReason ? 'PLAUSIBLE' : varPct === 0 ? 'COMPLIANT' : 'ANOMALY');

                    return (
                      <tr key={item.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="py-2.5 px-2 font-semibold text-slate-900 break-words align-middle">{item.date}</td>
                        <td className="py-2.5 px-2 font-semibold text-slate-800 break-words leading-tight align-middle">{item.ingredient_name}</td>
                        <td className="py-2.5 px-2 text-right font-bold text-amber-600 align-middle">
                          {item.quantity_purchased} {item.unit}
                        </td>
                        <td className="py-2.5 px-2 text-right text-slate-600 align-middle">{formatVND(item.unit_price)}</td>
                        <td className="py-2.5 px-2 text-right font-bold text-slate-900 align-middle">{formatVND(item.total_cost)}</td>
                        
                        {/* AI & Variance Audit Column */}
                        <td className="py-2.5 px-2 align-middle">
                          <div className="space-y-1">
                            <div className="flex items-center gap-1.5 flex-wrap">
                              {varPct === 0 && !hasReason ? (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                                  <Check className="w-3 h-3 text-emerald-600" /> Khớp AI (100%)
                                </span>
                              ) : (
                                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold border ${
                                  verdict === 'PLAUSIBLE' || verdict === 'COMPLIANT'
                                    ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                                    : verdict === 'MONITOR'
                                    ? 'bg-amber-50 text-amber-800 border-amber-200'
                                    : 'bg-red-50 text-red-800 border-red-200'
                                }`}>
                                  {varPct > 0 ? `+${varPct}%` : `${varPct}%`} • {verdict === 'PLAUSIBLE' ? 'Hợp Lý' : verdict === 'MONITOR' ? 'Theo Dõi' : 'Cảnh Báo'}
                                </span>
                              )}
                            </div>
                            {item.variance_reason && (
                              <p className="text-[11px] text-slate-500 italic break-words line-clamp-1" title={item.variance_reason}>
                                "{item.variance_reason}"
                              </p>
                            )}
                          </div>
                        </td>

                        <td className="py-2.5 px-2 font-mono text-slate-600 text-[11px] break-words align-middle">{item.batch_code || '-'}</td>
                        <td className="py-2.5 px-2 text-center align-middle">
                          <SolanaBadge
                            hash={item.record_hash}
                            tx={item.solana_tx}
                            size="compact"
                            onClick={() => handleOpenPoProof(item)}
                          />
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          <Pagination
            totalItems={filteredHistory.length}
            pageSize={histPageSize}
            currentPage={histPage}
            onPageChange={setHistPage}
            onPageSizeChange={setHistPageSize}
          />
        </div>
      )}

      {/* Variance Explanation & AI Plausibility Modal */}
      <VarianceExplanationModal
        isOpen={isVarianceModalOpen}
        onClose={() => setIsVarianceModalOpen(false)}
        items={pendingItemsToSubmit}
        branchId={branchId}
        targetDate={target_date}
        onConfirmWithReason={handleConfirmWithVarianceReason}
        isSubmitting={isRecordingManual}
      />

      {/* Solana Verification Modal */}
      <SolanaVerificationModal
        isOpen={isProofModalOpen}
        onClose={() => setIsProofModalOpen(false)}
        proofData={selectedProof}
      />

    </div>
  );
}
