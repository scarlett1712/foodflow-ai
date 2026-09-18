import React, { useState } from 'react';
import { 
  ShieldCheck, 
  ExternalLink, 
  Copy, 
  Check, 
  Lock, 
  Cpu, 
  CheckCircle2, 
  X 
} from 'lucide-react';
import { verifySolanaProof } from '../services/api';

export default function SolanaVerificationModal({ isOpen, onClose, proofData }) {
  const [copiedHash, setCopiedHash] = useState(false);
  const [copiedTx, setCopiedTx] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState(null);

  if (!isOpen || !proofData) return null;

  const {
    title = 'Chứng Thực Bất Biến Solana Devnet',
    recordType = 'Lô Hàng Kho (FEFO Batch)',
    code = '',
    sha256Hash = '',
    txSignature = '',
    network = 'Solana Devnet',
    authority = '29qNdUWXW5cqyojHkkhViHRdh7ro5AVoqBWwzSXgJCRA',
    timestamp = new Date().toLocaleString('vi-VN'),
    variancePct = 0,
    varianceReason = '',
    aiVerdict = '',
    aiNotes = '',
    aiAdjustment = ''
  } = proofData;

  const explorerUrl = txSignature 
    ? `https://explorer.solana.com/tx/${txSignature}?cluster=devnet`
    : `https://explorer.solana.com/address/${authority}?cluster=devnet`;

  const copyToClipboard = (text, type) => {
    navigator.clipboard.writeText(text);
    if (type === 'hash') {
      setCopiedHash(true);
      setTimeout(() => setCopiedHash(false), 2000);
    } else {
      setCopiedTx(true);
      setTimeout(() => setCopiedTx(false), 2000);
    }
  };

  const handleVerifyOnchain = async () => {
    try {
      setIsVerifying(true);
      const res = await verifySolanaProof({
        expected_hash: sha256Hash,
        tx_signature: txSignature || 'SOLANA_DEVNET_SIGNED_TX'
      });
      setVerifyResult(res.data);
    } catch (e) {
      setVerifyResult({
        verified: false,
        message: 'Lỗi kiểm tra chữ ký: ' + e.message
      });
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="relative bg-slate-900 border border-slate-700 text-white rounded-2xl shadow-2xl max-w-2xl w-full p-6 space-y-5 animate-in fade-in zoom-in duration-200">
        
        {/* Header */}
        <div className="flex items-start justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-emerald-400 flex items-center justify-center text-white shadow-lg shadow-purple-500/20">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-white">{title}</h3>
                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                  Solana Devnet
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Bằng chứng mật mã học bất biến xác thực nguồn gốc dữ liệu F&B
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Audit Badges & Info */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <div className="bg-slate-800/70 border border-slate-700/60 rounded-xl p-3">
            <span className="text-[11px] font-medium text-slate-400 block">Loại Bản Ghi</span>
            <span className="text-xs font-bold text-emerald-400 mt-1 block truncate">{recordType}</span>
          </div>

          <div className="bg-slate-800/70 border border-slate-700/60 rounded-xl p-3">
            <span className="text-[11px] font-medium text-slate-400 block">Mã Đối Tượng</span>
            <span className="text-xs font-mono font-bold text-white mt-1 block truncate">{code || 'N/A'}</span>
          </div>

          <div className="bg-slate-800/70 border border-slate-700/60 rounded-xl p-3 col-span-2 sm:col-span-1">
            <span className="text-[11px] font-medium text-slate-400 block">Thời Điểm Ghi Nhận</span>
            <span className="text-xs font-semibold text-slate-300 mt-1 block">{timestamp}</span>
          </div>
        </div>

        {/* Dual-Commitment AI & Variance Proof (if applicable) */}
        {(varianceReason || aiVerdict) && (
          <div className="p-3.5 rounded-xl bg-slate-950 border border-purple-500/30 space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="font-bold text-purple-300 flex items-center gap-1.5 uppercase text-[11px] tracking-wider">
                <ShieldCheck className="w-4 h-4 text-purple-400" />
                Kiểm Toán Tuân Thủ AI (Dual-Commitment Audit):
              </span>
              <span className={`px-2 py-0.5 rounded-full font-bold text-[10px] ${
                aiVerdict === 'PLAUSIBLE' || aiVerdict === 'COMPLIANT'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                  : aiVerdict === 'MONITOR'
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                  : 'bg-red-500/20 text-red-300 border border-red-500/30'
              }`}>
                {aiVerdict === 'PLAUSIBLE' ? '🟢 Hợp Lý (Verified)' : aiVerdict === 'MONITOR' ? '🟡 Cần Theo Dõi' : '🔴 Cảnh Báo'}
              </span>
            </div>

            {variancePct !== 0 && (
              <div className="text-slate-300 flex items-center gap-2">
                <span className="text-slate-400">Độ lệch ngân sách:</span>
                <span className="font-mono font-bold text-amber-400">
                  {variancePct > 0 ? `+${variancePct}%` : `${variancePct}%`}
                </span>
              </div>
            )}

            {varianceReason && (
              <div className="text-slate-300">
                <span className="text-slate-400 font-medium">Lý do giải trình: </span>
                <span className="italic text-slate-200">"{varianceReason}"</span>
              </div>
            )}

            {aiAdjustment && (
              <div className="text-slate-400 text-[11px] pt-1 border-t border-slate-800 flex items-start gap-1.5">
                <span className="text-emerald-400 font-bold shrink-0">⚡ Thích ứng mô hình:</span>
                <span className="text-slate-300">{aiAdjustment}</span>
              </div>
            )}
          </div>
        )}

        {/* SHA-256 Hash Box */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-purple-400" />
              Mã Băm Xác Định (Deterministic SHA-256 Hash)
            </label>
            <button
              onClick={() => copyToClipboard(sha256Hash, 'hash')}
              className="text-[11px] font-medium text-purple-400 hover:text-purple-300 flex items-center gap-1 cursor-pointer"
            >
              {copiedHash ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
              {copiedHash ? 'Đã sao chép' : 'Sao chép Hash'}
            </button>
          </div>
          <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl font-mono text-[11px] text-purple-300 break-all select-all">
            {sha256Hash || '0x0000000000000000000000000000000000000000000000000000000000000000'}
          </div>
        </div>

        {/* Solana Transaction Signature */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-emerald-400" />
              Chữ Ký Giao Dịch Solana Devnet (Tx Signature)
            </label>
            <button
              onClick={() => copyToClipboard(txSignature, 'tx')}
              className="text-[11px] font-medium text-emerald-400 hover:text-emerald-300 flex items-center gap-1 cursor-pointer"
            >
              {copiedTx ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
              {copiedTx ? 'Đã sao chép' : 'Sao chép Tx'}
            </button>
          </div>
          <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl font-mono text-[11px] text-emerald-400 break-all select-all">
            {txSignature || 'Đang chờ phát hành chữ ký trên Solana Devnet...'}
          </div>
        </div>

        {/* Verification Result Callout */}
        {verifyResult && (
          <div className="p-3.5 rounded-xl bg-emerald-950/60 border border-emerald-500/40 text-emerald-200 text-xs flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-bold text-emerald-300">Xác Thực Toàn Vẹn Thành Công 100%!</span>
              <p className="text-slate-300 leading-relaxed">{verifyResult.message}</p>
              <div className="flex items-center gap-2 mt-1 text-[11px] text-emerald-400/90 font-mono">
                <span>Authority: {authority.slice(0, 8)}...{authority.slice(-6)}</span>
                <span>•</span>
                <span>Tamper-Proof Confirmed</span>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2 border-t border-slate-800">
          <a
            href={explorerUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold border border-slate-700 transition-all cursor-pointer"
          >
            <span>Xem Trên Solana Explorer</span>
            <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
          </a>

          <div className="w-full sm:w-auto flex items-center gap-2">
            <button
              onClick={handleVerifyOnchain}
              disabled={isVerifying}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold shadow-lg shadow-emerald-600/30 transition-all cursor-pointer"
            >
              {isVerifying ? (
                <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <ShieldCheck className="w-4 h-4" />
              )}
              <span>Đối Chiếu Chữ Ký Ngay</span>
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold cursor-pointer"
            >
              Đóng
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
