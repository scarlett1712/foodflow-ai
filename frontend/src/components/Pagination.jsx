import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

export default function Pagination({ 
  totalItems, 
  pageSize, 
  currentPage, 
  onPageChange, 
  onPageSizeChange,
  compact = false
}) {
  const totalPages = Math.ceil(totalItems / pageSize) || 1;
  const startItem = totalItems === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(currentPage * pageSize, totalItems);

  if (compact) {
    return (
      <div className="flex items-center justify-between gap-2 px-3 py-2.5 border-t border-slate-200 bg-slate-50/70 text-xs text-slate-600 rounded-b-2xl select-none">
        <div className="flex items-center gap-1.5 whitespace-nowrap">
          <select
            value={pageSize}
            onChange={(e) => {
              onPageSizeChange(Number(e.target.value));
              onPageChange(1);
            }}
            className="bg-white border border-slate-300 rounded-md px-2 py-1 text-xs font-semibold text-slate-700 focus:outline-none focus:ring-1 focus:ring-emerald-500 cursor-pointer shadow-2xs"
          >
            <option value={5}>5 / trang</option>
            <option value={10}>10 / trang</option>
            <option value={20}>20 / trang</option>
          </select>
          <span className="text-[11px] text-slate-500 font-medium">
            ({startItem}-{endItem} / {totalItems})
          </span>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage <= 1}
            className={`p-1 rounded-md border border-slate-300 transition-all ${
              currentPage <= 1
                ? 'opacity-30 cursor-not-allowed bg-slate-100 text-slate-400'
                : 'bg-white hover:bg-slate-100 text-slate-700 cursor-pointer shadow-2xs'
            }`}
            title="Trang trước"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>

          <span className="px-2 py-0.5 text-xs font-semibold bg-white border border-slate-200 rounded-md text-slate-800 shadow-2xs whitespace-nowrap">
            {currentPage}/{totalPages}
          </span>

          <button
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage >= totalPages}
            className={`p-1 rounded-md border border-slate-300 transition-all ${
              currentPage >= totalPages
                ? 'opacity-30 cursor-not-allowed bg-slate-100 text-slate-400'
                : 'bg-white hover:bg-slate-100 text-slate-700 cursor-pointer shadow-2xs'
            }`}
            title="Trang sau"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-t border-slate-200 bg-slate-50/70 text-xs text-slate-600 rounded-b-2xl">
      {/* Page Size Selector */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="whitespace-nowrap">Hiển thị mỗi trang:</span>
        <select
          value={pageSize}
          onChange={(e) => {
            onPageSizeChange(Number(e.target.value));
            onPageChange(1);
          }}
          className="bg-white border border-slate-300 rounded-lg px-2.5 py-1 text-xs font-semibold text-slate-800 focus:outline-none focus:ring-1 focus:ring-emerald-500 cursor-pointer shadow-2xs"
        >
          <option value={5}>5 dòng</option>
          <option value={10}>10 dòng</option>
          <option value={20}>20 dòng</option>
        </select>
        <span className="text-slate-400">|</span>
        <span className="whitespace-nowrap">
          Đang xem <strong>{startItem}-{endItem}</strong> trong tổng số <strong>{totalItems}</strong> bản ghi
        </span>
      </div>

      {/* Navigation Buttons */}
      <div className="flex items-center gap-1.5 shrink-0">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1}
          className={`p-1.5 rounded-lg border border-slate-300 transition-all ${
            currentPage <= 1
              ? 'opacity-40 cursor-not-allowed bg-slate-100 text-slate-400'
              : 'bg-white hover:bg-slate-100 text-slate-700 cursor-pointer shadow-2xs'
          }`}
          title="Trang trước"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        <span className="px-3 py-1 font-semibold bg-white border border-slate-200 rounded-lg text-slate-800 shadow-2xs whitespace-nowrap">
          Trang {currentPage} / {totalPages}
        </span>

        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages}
          className={`p-1.5 rounded-lg border border-slate-300 transition-all ${
            currentPage >= totalPages
              ? 'opacity-40 cursor-not-allowed bg-slate-100 text-slate-400'
              : 'bg-white hover:bg-slate-100 text-slate-700 cursor-pointer shadow-2xs'
          }`}
          title="Trang sau"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

    </div>
  );
}
