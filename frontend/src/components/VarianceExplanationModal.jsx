import React, { useState, useEffect } from 'react';
import { 
  AlertTriangle, 
  Sparkles, 
  ShieldCheck, 
  X, 
  TrendingUp, 
  CheckCircle2, 
  Info, 
  ArrowRight,
  RefreshCw,
  Zap,
  HelpCircle
} from 'lucide-react';
import { analyzePurchaseVariance } from '../services/api';

export default function VarianceExplanationModal({
  isOpen,
  onClose,
  items = [],
  branchId = 'BRANCH_01',
  targetDate = '',
  onConfirmWithReason,
  isSubmitting = false
}) {
  const [reason, setReason] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [assessment, setAssessment] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');

  const QUICK_REASONS = [
    { label: '🌩️ Bão giá thị trường / NCC tăng', text: 'Nhà cung cấp điều chỉnh tăng giá do biến động thị trường và chi phí vận chuyển nông sản leo thang.' },
    { label: '🎉 Phục vụ tiệc / Khách đông đột xuất', text: 'Nhà hàng nhận đặt thêm tiệc lớn đột xuất cuối tuần nên cần nhập dôi dư nguyên liệu dự trữ.' },
    { label: '📦 Bù hao hụt / Hỏng hóc kho', text: 'Nhập bổ sung khẩn cấp do lô nguyên liệu cũ bị hao hụt và hỏng trong quá trình bảo quản.' },
    { label: '🏷️ Mua sỉ nhận chiết khấu cao', text: 'Tận dụng chương trình chiết khấu mua sỉ số lượng lớn từ nhà cung cấp để tối ưu giá vốn.' }
  ];

  // Auto-run initial evaluation when modal opens
  useEffect(() => {
    if (isOpen && items.length > 0) {
      handleRunAnalysis('');
    } else {
      setAssessment(null);
      setReason('');
      setErrorMsg('');
    }
  }, [isOpen, items]);

  const handleRunAnalysis = async (customReason) => {
    try {
      setIsAnalyzing(true);
      setErrorMsg('');
      const payload = {
        branch_id: branchId,
        date: targetDate,
        items: items,
        reason: customReason !== undefined ? customReason : reason
      };
      const res = await analyzePurchaseVariance(payload);
      setAssessment(res.data);
    } catch (e) {
      console.error(e);
      setErrorMsg('Không thể phân tích chênh lệch lúc này: ' + (e.response?.data?.detail || e.message));
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleApplyQuickReason = (text) => {
    setReason(text);
    handleRunAnalysis(text);
  };

  const handleConfirm = () => {
    if (!reason.trim()) {
      setErrorMsg('Vui lòng nhập lý do giải trình trước khi ký duyệt nhập kho!');
      return;
    }
    onConfirmWithReason(reason.trim(), assessment);
  };

  if (!isOpen) return null;

  const flaggedItems = assessment?.item_evaluations?.filter(x => x.is_price_flagged || x.is_qty_flagged) || [];
  const costVariancePct = assessment?.cost_variance_pct || 0;
  const costDiff = assessment?.cost_variance_diff || 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="bg-white rounded-3xl max-w-2xl w-full shadow-2xl border border-slate-100 overflow-hidden flex flex-col my-8 animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="px-6 py-4.5 bg-gradient-to-r from-amber-500 via-orange-500 to-amber-600 text-white flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-white/20 rounded-xl backdrop-blur-xs">
              <AlertTriangle className="w-5 h-5 text-amber-100" />
            </div>
            <div>
              <h3 className="text-base font-bold">Cảnh Báo Chênh Lệch Đơn Đi Chợ</h3>
              <p className="text-xs text-amber-100">
                Phát hiện biến động so với Gợi ý AI & Giá Vốn Chuẩn
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 rounded-full hover:bg-white/20 text-white/80 hover:text-white transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-5 max-h-[75vh] overflow-y-auto">
          
          {/* Summary KPI Callout */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="bg-amber-50/80 border border-amber-200/80 p-3.5 rounded-2xl">
              <span className="text-[11px] font-semibold text-amber-700 block">Chênh Lệch Ngân Sách</span>
              <div className="flex items-baseline gap-1 mt-1">
                <span className="text-lg font-extrabold text-amber-900">
                  {costVariancePct > 0 ? `+${costVariancePct}%` : `${costVariancePct}%`}
                </span>
                <span className="text-xs text-amber-700">
                  ({costDiff > 0 ? `+${Number(costDiff).toLocaleString('vi-VN')} đ` : `${Number(costDiff).toLocaleString('vi-VN')} đ`})
                </span>
              </div>
            </div>

            <div className="bg-slate-50 border border-slate-200 p-3.5 rounded-2xl">
              <span className="text-[11px] font-semibold text-slate-500 block">Số Mặt Hàng Bị Lệch</span>
              <div className="flex items-baseline gap-1 mt-1">
                <span className="text-lg font-extrabold text-slate-800">{flaggedItems.length}</span>
                <span className="text-xs text-slate-500">/ {items.length} nguyên liệu</span>
              </div>
            </div>

            <div className="bg-emerald-50/80 border border-emerald-200/80 p-3.5 rounded-2xl">
              <span className="text-[11px] font-semibold text-emerald-700 block">Kiểm Toán Solana Devnet</span>
              <div className="flex items-center gap-1.5 mt-1">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span className="text-xs font-bold text-emerald-800">Dual-Proof Audit</span>
              </div>
            </div>
          </div>

          {/* Table of Flagged Items */}
          {flaggedItems.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                <Info className="w-3.5 h-3.5 text-slate-400" />
                Chi Tiết Các Mặt Hàng Tăng Giá Hoặc Vượt Khối Lượng:
              </h4>
              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <table className="w-full text-left text-xs table-fixed">
                  <thead>
                    <tr className="bg-slate-100/80 text-slate-600 font-bold border-b border-slate-200">
                      <th className="py-2 px-3 w-[35%]">Nguyên Liệu</th>
                      <th className="py-2 px-3 text-right w-[20%]">Số Lượng</th>
                      <th className="py-2 px-3 text-right w-[25%]">Đơn Giá Mua</th>
                      <th className="py-2 px-3 text-center w-[20%]">Độ Lệch Giá</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {flaggedItems.map((fi, idx) => (
                      <tr key={idx} className="hover:bg-slate-50">
                        <td className="py-2.5 px-3 font-semibold text-slate-800 break-words leading-tight">
                          {fi.ingredient_name}
                        </td>
                        <td className="py-2.5 px-3 text-right text-slate-700 font-medium">
                          {fi.actual_quantity} {fi.unit}
                          {fi.is_qty_flagged && (
                            <span className="block text-[10px] text-amber-600 font-bold">Vượt định mức</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-slate-800">
                          {Number(fi.actual_unit_price).toLocaleString('vi-VN')} đ
                          <span className="block text-[10px] text-slate-400">
                            Chuẩn: {Number(fi.standard_unit_price).toLocaleString('vi-VN')} đ
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          {fi.price_variance_pct > 0 ? (
                            <span className="inline-block px-2 py-0.5 rounded-md text-[11px] font-bold bg-red-100 text-red-700">
                              +{fi.price_variance_pct}%
                            </span>
                          ) : (
                            <span className="text-slate-400 font-mono text-[11px]">-</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Reason Input & Quick Pills */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                <span>Lý Do Giải Trình Chênh Lệch (Bắt buộc):</span>
              </label>
              <span className="text-[11px] text-slate-400">AI sẽ tự động thẩm định ngữ nghĩa</span>
            </div>

            {/* Quick Reason Suggestions */}
            <div className="flex flex-wrap gap-1.5">
              {QUICK_REASONS.map((qr, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleApplyQuickReason(qr.text)}
                  className="px-2.5 py-1 rounded-lg text-[11px] font-medium bg-slate-100 hover:bg-emerald-50 hover:text-emerald-700 hover:border-emerald-200 border border-slate-200 text-slate-700 transition-all cursor-pointer"
                >
                  {qr.label}
                </button>
              ))}
            </div>

            <textarea
              rows={3}
              value={reason}
              onChange={(e) => {
                setReason(e.target.value);
                setErrorMsg('');
              }}
              placeholder="Nhập lý do cụ thể (VD: Nhà cung cấp tăng giá do bão lũ miền Trung, hoặc Nhập thêm dự trữ phục vụ tiệc cưới 50 khách cuối tuần...)"
              className="w-full p-3 text-xs bg-slate-50 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-amber-500 focus:bg-white text-slate-800 placeholder-slate-400 leading-relaxed"
            />

            <div className="flex items-center justify-end">
              <button
                type="button"
                onClick={() => handleRunAnalysis(reason)}
                disabled={isAnalyzing || !reason.trim()}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  isAnalyzing || !reason.trim()
                    ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                    : 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs'
                }`}
              >
                <Sparkles className={`w-3.5 h-3.5 ${isAnalyzing ? 'animate-spin' : ''}`} />
                <span>{isAnalyzing ? 'AI Đang Thẩm Định...' : '✨ AI Thẩm Định Tính Hợp Lý'}</span>
              </button>
            </div>
          </div>

          {/* AI Assessment Result Card */}
          {assessment && (
            <div className={`p-4 rounded-2xl border transition-all ${
              assessment.verdict === 'PLAUSIBLE' || assessment.verdict === 'COMPLIANT'
                ? 'bg-emerald-50/60 border-emerald-200 text-emerald-950'
                : assessment.verdict === 'MONITOR'
                ? 'bg-amber-50/60 border-amber-200 text-amber-950'
                : 'bg-red-50/60 border-red-200 text-red-950'
            }`}>
              <div className="flex items-center justify-between pb-2 border-b border-black/5">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-emerald-600" />
                  <span className="text-xs font-bold uppercase tracking-wider">
                    Kết Quả Thẩm Định Của AI
                  </span>
                </div>
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-extrabold ${
                  assessment.plausibility_badge === 'success'
                    ? 'bg-emerald-600 text-white'
                    : assessment.plausibility_badge === 'warning'
                    ? 'bg-amber-500 text-white'
                    : 'bg-red-600 text-white'
                }`}>
                  Độ Hợp Lý: {assessment.plausibility_level}
                </span>
              </div>

              <div className="mt-3 space-y-2 text-xs">
                <div className="flex items-start gap-2">
                  <span className="font-bold text-slate-700 shrink-0">Phân loại:</span>
                  <span className="font-semibold text-slate-900">{assessment.category_text}</span>
                </div>

                <div className="flex items-start gap-2">
                  <span className="font-bold text-slate-700 shrink-0">Đánh giá AI:</span>
                  <span className="text-slate-800">{assessment.ai_notes}</span>
                </div>

                {/* Model Adaptation Strategy */}
                <div className="mt-2 p-2.5 rounded-xl bg-white/80 border border-black/5 flex items-start gap-2">
                  <Zap className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold text-slate-800 block text-[11px]">
                      Chiến Lược Tự Động Thích Ứng Mô Hình Dự Báo:
                    </span>
                    <p className="text-[11px] text-slate-600 mt-0.5 leading-relaxed">
                      {assessment.adjustment_strategy}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {errorMsg && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 font-medium">
              {errorMsg}
            </div>
          )}

        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-200 rounded-xl transition-all cursor-pointer"
          >
            Hủy / Điều Chỉnh Lại Số Lượng
          </button>

          <button
            type="button"
            onClick={handleConfirm}
            disabled={isSubmitting || isAnalyzing}
            className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold text-white shadow-md transition-all cursor-pointer ${
              isSubmitting || isAnalyzing
                ? 'bg-slate-400 cursor-not-allowed'
                : 'bg-emerald-600 hover:bg-emerald-700 hover:shadow-emerald-600/30'
            }`}
          >
            {isSubmitting ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Đang Ký Duyệt & Lưu On-Chain...</span>
              </>
            ) : (
              <>
                <ShieldCheck className="w-4 h-4" />
                <span>Xác Nhận Nhập Kho & Ký Duyệt Solana</span>
              </>
            )}
          </button>
        </div>

      </div>
    </div>
  );
}
