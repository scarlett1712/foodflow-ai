import React from 'react';
import { ShieldCheck, Cpu, ExternalLink } from 'lucide-react';

export default function SolanaBadge({ 
  hash, 
  tx, 
  status = 'CONFIRMED', 
  onClick, 
  size = 'normal' 
}) {
  const shortHash = hash 
    ? `${hash.slice(0, 6)}...${hash.slice(-4)}` 
    : 'Chờ ký...';

  if (size === 'compact') {
    return (
      <button
        onClick={onClick}
        className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200 text-[11px] font-medium transition-colors cursor-pointer group"
        title="Nhấn để xem chứng thực mật mã học trên Solana Devnet"
      >
        <ShieldCheck className="w-3.5 h-3.5 text-purple-600 group-hover:scale-110 transition-transform" />
        <span className="font-mono">{shortHash}</span>
      </button>
    );
  }

  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-2 px-2.5 py-1 rounded-lg bg-gradient-to-r from-purple-50 to-indigo-50 hover:from-purple-100 hover:to-indigo-100 text-purple-900 border border-purple-200 text-xs font-medium transition-all shadow-xs cursor-pointer group"
      title="Bản ghi bất biến trên Solana Devnet. Nhấn để kiểm tra đối chiếu chữ ký."
    >
      <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
      <span className="font-semibold text-purple-800">Solana Devnet:</span>
      <span className="font-mono text-purple-700 group-hover:text-purple-900">{shortHash}</span>
      <ShieldCheck className="w-3.5 h-3.5 text-purple-600 group-hover:text-purple-800" />
    </button>
  );
}
