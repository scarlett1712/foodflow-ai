import React from 'react';
import { 
  TrendingUp, 
  ShoppingCart, 
  AlertTriangle, 
  DollarSign, 
  ArrowUpRight, 
  Calendar, 
  CalendarCheck,
  CheckCircle,
  Flame,
  ArrowRight,
  Sparkles
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid 
} from 'recharts';

export default function DashboardPage({ summary, onNavigateTab }) {
  if (!summary) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  const { kpis, top_dishes_tomorrow, urgent_purchases, recent_revenue_trend, tomorrow_date, branch } = summary;

  // Format currency VNĐ
  const formatVND = (num) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(num || 0);
  };

  const chartData = recent_revenue_trend?.map((item) => ({
    date: item.date.slice(5),
    revenue: item.daily_revenue / 1000000, // Triệu VNĐ
  })) || [];

  const isDataEmpty = (!top_dishes_tomorrow || top_dishes_tomorrow.length === 0) && (!recent_revenue_trend || recent_revenue_trend.length === 0);

  return (
    <div className="space-y-6">
      
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900">Bảng Điều Hành Dự Báo & Nhập Hàng</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              {tomorrow_date ? `Ngày mai: ${tomorrow_date}` : 'Chưa có lịch sử'}
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Tổng quan chỉ số dự báo bán hàng và khuyến nghị nhập nguyên liệu cho <strong>{branch?.name}</strong>.
          </p>
        </div>

        <button
          onClick={() => onNavigateTab('purchase')}
          className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-semibold shadow-md shadow-emerald-600/20 transition-all cursor-pointer"
        >
          <ShoppingCart className="w-4 h-4" />
          <span>Xem Danh Sách Đi Chợ</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {isDataEmpty && (
        <div className="bg-gradient-to-r from-emerald-50 via-teal-50 to-blue-50 border border-emerald-200 p-6 rounded-2xl text-slate-800 space-y-3">
          <div className="flex items-center gap-2 text-emerald-800 font-bold text-base">
            <Sparkles className="w-5 h-5 text-emerald-600" />
            <span>Chào mừng bạn đến với FoodFlow AI! Hệ thống đang ở trạng thái mới hoàn toàn.</span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            Để bắt đầu dự báo và quản lý đi chợ cho quán ăn của bạn, hãy thực hiện các bước đơn giản sau:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
            <button
              onClick={() => onNavigateTab('recipes')}
              className="p-3.5 bg-white border border-slate-200 rounded-xl text-left hover:border-emerald-400 hover:shadow-xs transition-all cursor-pointer"
            >
              <span className="text-xs font-bold text-slate-900 block mb-1">1. Thêm Món Ăn & Công Thức</span>
              <span className="text-[11px] text-slate-500">Tạo thực đơn món ăn và định lượng nguyên liệu cấu thành.</span>
            </button>
            <button
              onClick={() => onNavigateTab('inventory')}
              className="p-3.5 bg-white border border-slate-200 rounded-xl text-left hover:border-emerald-400 hover:shadow-xs transition-all cursor-pointer"
            >
              <span className="text-xs font-bold text-slate-900 block mb-1">2. Khai Báo Kho & Đi Chợ</span>
              <span className="text-[11px] text-slate-500">Thêm nguyên liệu kèm AI Smart Tag hoặc tải file đi chợ lên.</span>
            </button>
            <div className="p-3.5 bg-white border border-slate-200 rounded-xl text-left">
              <span className="text-xs font-bold text-slate-900 block mb-1">3. Tải File Doanh Số CSV</span>
              <span className="text-[11px] text-slate-500">Nhấn nút "Nhập File CSV" trên Navbar để AI học dữ liệu bán hàng.</span>
            </div>
          </div>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Card 1: Doanh thu dự kiến */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Doanh Thu Dự Kiến</span>
            <div className="p-2.5 rounded-xl bg-emerald-50 text-emerald-600">
              <DollarSign className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <h3 className="text-2xl font-bold text-slate-900">{formatVND(kpis.expected_sales_revenue)}</h3>
            <p className="text-xs text-emerald-600 font-medium flex items-center gap-1 mt-1">
              <ArrowUpRight className="w-3.5 h-3.5" /> Dựa trên XGBoost + Đơn đặt trước
            </p>
          </div>
        </div>

        {/* Card 2: Nhu cầu món ăn */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Tổng Lượng Món Cần Bán</span>
            <div className="p-2.5 rounded-xl bg-blue-50 text-blue-600">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <h3 className="text-2xl font-bold text-slate-900">{kpis.total_dishes_demand} <span className="text-sm font-normal text-slate-500">phần / ly</span></h3>
            <p className="text-xs text-slate-500 font-medium flex items-center gap-1 mt-1">
              <CalendarCheck className="w-3.5 h-3.5 text-blue-500" /> Bao gồm <strong>+{kpis.confirmed_preorders_count}</strong> phần đặt trước
            </p>
          </div>
        </div>

        {/* Card 3: Ngân sách đi chợ */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Ngân Sách Nhập Hàng</span>
            <div className="p-2.5 rounded-xl bg-purple-50 text-purple-600">
              <ShoppingCart className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <h3 className="text-2xl font-bold text-purple-900">{formatVND(kpis.purchase_budget_needed)}</h3>
            <p className="text-xs text-purple-700 font-medium mt-1">
              Cần mua <strong>{kpis.items_to_buy_count}</strong> mặt hàng nguyên liệu
            </p>
          </div>
        </div>

        {/* Card 4: Cảnh báo thiếu hụt */}
        <div className="bg-white p-5 rounded-2xl border border-amber-200 bg-amber-50/40 shadow-xs relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-amber-800 uppercase tracking-wider">Thiếu Hụt Khẩn Cấp</span>
            <div className="p-2.5 rounded-xl bg-amber-100 text-amber-700">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <h3 className="text-2xl font-bold text-amber-900">{kpis.critical_shortage_count} <span className="text-sm font-normal text-amber-700">nguyên liệu</span></h3>
            <p className="text-xs text-amber-700 font-medium mt-1">
              Tồn kho hiện tại dưới 35% nhu cầu ngày mai
            </p>
          </div>
        </div>

      </div>

      {/* Main Content 2 Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Revenue Chart & Top Dishes (2/3 width) */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Revenue Trend Chart */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-base font-bold text-slate-900">Xu Hướng Doanh Số 7 Ngày Gần Nhất</h3>
                <p className="text-xs text-slate-500">Doanh thu thực tế theo ngày (Đơn vị: Triệu VNĐ)</p>
              </div>
              <span className="text-xs font-semibold text-slate-600 bg-slate-100 px-2.5 py-1 rounded-lg">
                7 Ngày qua
              </span>
            </div>

            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
                  <defs>
                    <linearGradient id="revenueGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0.0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#64748b' }} />
                  <YAxis tick={{ fontSize: 12, fill: '#64748b' }} unit=" tr" />
                  <Tooltip 
                    formatter={(value) => [`${value.toFixed(1)} Triệu VNĐ`, 'Doanh Thu']}
                    labelFormatter={(label) => `Ngày: ${label}`}
                    contentStyle={{ backgroundColor: '#1e293b', borderRadius: '12px', border: 'none', color: '#fff' }}
                  />
                  <Area type="monotone" dataKey="revenue" stroke="#10b981" strokeWidth={3} fillOpacity={1} fill="url(#revenueGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Top Selling Dishes Predicted */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Flame className="w-5 h-5 text-orange-500" />
                <h3 className="text-base font-bold text-slate-900">Top 5 Món Dự Báo Bán Chạy Nhất Ngày Mai</h3>
              </div>
              <button 
                onClick={() => onNavigateTab('forecast')} 
                className="text-xs font-semibold text-emerald-600 hover:text-emerald-700 flex items-center gap-1"
              >
                Xem chi tiết 22 món <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="overflow-hidden">
              <table className="w-full text-left text-xs table-fixed">
                <thead>
                  <tr className="border-b border-slate-100 text-xs font-semibold text-slate-400 uppercase">
                    <th className="pb-3 w-[36%]">Món Ăn / Đồ Uống</th>
                    <th className="pb-3 w-[22%]">Phân Loại</th>
                    <th className="pb-3 text-right w-[14%]">Dự Báo ML</th>
                    <th className="pb-3 text-right w-[14%]">Đặt Trước</th>
                    <th className="pb-3 text-right font-bold text-slate-900 w-[14%]">Tổng Cầu</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {top_dishes_tomorrow?.map((dish) => (
                    <tr key={dish.dish_id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3 pr-2 font-medium text-slate-800 break-words leading-tight">{dish.dish_name}</td>
                      <td className="py-3 pr-2">
                        <span className="text-[11px] px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 font-medium inline-block break-words">
                          {dish.category}
                        </span>
                      </td>
                      <td className="py-3 text-right text-slate-600 font-medium">{dish.xgb_forecast}</td>
                      <td className="py-3 text-right font-semibold text-blue-600">
                        {dish.confirmed_preorders > 0 ? `+${dish.confirmed_preorders}` : '-'}
                      </td>
                      <td className="py-3 text-right font-bold text-emerald-600 text-sm">
                        {dish.expected_demand}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        </div>

        {/* Right Column: Urgent Purchase Recommendations (1/3 width) */}
        <div className="space-y-6">
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col h-full justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-amber-500" />
                  <h3 className="text-base font-bold text-slate-900">Cần Nhập Gấp</h3>
                </div>
                <span className="text-xs font-bold text-red-600 bg-red-50 border border-red-200 px-2 py-0.5 rounded-full">
                  {kpis.critical_shortage_count} Cấp thiết
                </span>
              </div>
              <p className="text-xs text-slate-500 mb-4">
                Các mặt hàng tươi sống đang dưới mức tồn an toàn cho ngày mai:
              </p>

              <div className="space-y-3">
                {urgent_purchases?.map((ing) => (
                  <div key={ing.ingredient_id} className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 hover:border-emerald-300 transition-all">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-semibold text-slate-800">{ing.ingredient_name}</span>
                      <span className={`text-[11px] font-bold px-2 py-0.5 rounded-md ${
                        ing.status === 'CRITICAL' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
                      }`}>
                        {ing.status_text}
                      </span>
                    </div>

                    <div className="grid grid-cols-3 text-xs text-slate-500 mt-2 pt-2 border-t border-slate-200/60">
                      <div>
                        <span className="block text-[10px] text-slate-400">Cần dùng:</span>
                        <span className="font-semibold text-slate-700">{ing.required_quantity} {ing.unit}</span>
                      </div>
                      <div>
                        <span className="block text-[10px] text-slate-400">Tồn kho:</span>
                        <span className="font-semibold text-slate-700">{ing.current_stock} {ing.unit}</span>
                      </div>
                      <div className="text-right">
                        <span className="block text-[10px] text-red-500 font-bold">CẦN MUA:</span>
                        <span className="font-bold text-red-600 text-sm">{ing.recommended_purchase} {ing.unit}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={() => onNavigateTab('purchase')}
              className="w-full mt-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-sm font-semibold transition-all flex items-center justify-center gap-2 cursor-pointer"
            >
              <span>Xem Bảng Mua Hàng Đầy Đủ</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>

      </div>

    </div>
  );
}
