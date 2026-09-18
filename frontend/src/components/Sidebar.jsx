import React from 'react';
import { 
  LayoutDashboard, 
  TrendingUp, 
  ShoppingCart, 
  Package, 
  UtensilsCrossed, 
  CalendarCheck,
  Building2
} from 'lucide-react';

export default function Sidebar({ currentTab, onSelectTab, branchMeta }) {
  const navItems = [
    { id: 'dashboard', label: 'Tổng Quan', icon: LayoutDashboard, badge: null },
    { id: 'forecast', label: 'Dự Báo Nhu Cầu', icon: TrendingUp, badge: 'XGBoost' },
    { id: 'purchase', label: 'Gợi Ý Mua Hàng', icon: ShoppingCart, badge: 'Quan trọng' },
    { id: 'inventory', label: 'Kho & Hạn Dùng', icon: Package, badge: null },
    { id: 'recipes', label: 'Thực Đơn & Định Lượng', icon: UtensilsCrossed, badge: null },
    { id: 'preorders', label: 'Đơn Đặt Trước', icon: CalendarCheck, badge: null },
  ];

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col justify-between shrink-0 min-h-[calc(100vh-4rem)] border-r border-slate-800">
      <div className="p-4">
        
        {/* Active Branch Info Card */}
        {branchMeta && (
          <div className="bg-slate-800/80 rounded-xl p-3 mb-6 border border-slate-700/60">
            <div className="flex items-start gap-2.5">
              <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 mt-0.5">
                <Building2 className="w-4 h-4" />
              </div>
              <div className="overflow-hidden">
                <p className="text-xs text-slate-400 font-medium">Chi nhánh hiện tại</p>
                <h4 className="text-sm font-semibold text-white truncate">{branchMeta.name}</h4>
                <p className="text-[11px] text-emerald-400 font-medium truncate mt-0.5">{branchMeta.type}</p>
              </div>
            </div>
          </div>
        )}

        {/* Navigation Menu */}
        <div className="text-[11px] uppercase tracking-wider font-bold text-slate-400 px-3 mb-2">
          Menu Điều Hành
        </div>
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded-md font-semibold ${
                      isActive
                        ? 'bg-emerald-700 text-emerald-100'
                        : item.badge === 'XGBoost'
                        ? 'bg-purple-900/60 text-purple-300 border border-purple-700/50'
                        : 'bg-amber-900/60 text-amber-300 border border-amber-700/50'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Model status footer */}
      <div className="p-4 border-t border-slate-800/80">
        <div className="bg-slate-950/60 rounded-xl p-3 border border-slate-800 text-xs">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="font-semibold text-slate-200">XGBoost Production</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Dữ liệu huấn luyện: <strong>730 ngày</strong> (2 năm) trên <strong>22 món</strong> tại 3 chi nhánh.
          </p>
        </div>
      </div>
    </aside>
  );
}
