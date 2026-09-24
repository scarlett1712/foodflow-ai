import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  TrendingUp, 
  Award, 
  AlertTriangle, 
  Sun, 
  CloudRain, 
  Calendar, 
  Lightbulb, 
  ArrowUpRight, 
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  HelpCircle
} from 'lucide-react';
import { getStoreInsights } from '../services/api';

export default function DataInsightCard({ branchId = 'BRANCH_01', selectedCity = 'ho_chi_minh' }) {
  const [insightData, setInsightData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isExpanded, setIsExpanded] = useState(true);

  const fetchInsights = async () => {
    try {
      setLoading(true);
      const res = await getStoreInsights(branchId, selectedCity);
      if (res.data && res.data.status === 'success') {
        setInsightData(res.data);
      } else {
        setInsightData(null);
      }
    } catch (err) {
      console.error('Error fetching store insights:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInsights();
  }, [branchId, selectedCity]);

  if (loading) {
    return (
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex items-center justify-center gap-3 text-slate-500 text-xs">
        <RefreshCw className="w-4 h-4 animate-spin text-purple-600" />
        <span>Đang phân tích thấu cảm dữ liệu & sinh AI Insights...</span>
      </div>
    );
  }

  if (!insightData) {
    return null;
  }

  const { summary, menu_engineering, day_of_week_pattern, weather_sensitivity, actionable_recommendations, branch } = insightData;

  const getPriorityBadge = (p) => {
    switch (p) {
      case 'HIGH':
        return <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-200">Ưu tiên cao</span>;
      case 'MEDIUM':
        return <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">Quan trọng</span>;
      default:
        return <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">Khuyến nghị</span>;
    }
  };

  return (
    <div className="bg-linear-to-br from-purple-50/70 via-indigo-50/40 to-white rounded-2xl border border-purple-200/80 shadow-xs overflow-hidden transition-all">
      
      {/* Header */}
      <div className="p-5 pb-4 flex items-center justify-between border-b border-purple-100/80">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-purple-600 text-white flex items-center justify-center shadow-md shadow-purple-200">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-slate-900">AI Data Insights — Thấu Cảm Dữ Liệu Quán</h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-200 text-purple-900">
                {branch?.name || 'Chi Nhánh'}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Tự động phân tích quy luật bán hàng qua {insightData.analyzed_days} ngày lịch sử, độ nhạy thời tiết và chu kỳ vận hành.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchInsights}
            title="Làm mới phân tích"
            className="p-1.5 rounded-lg bg-white border border-slate-200 text-slate-600 hover:text-purple-600 hover:bg-purple-50 transition-colors cursor-pointer text-xs flex items-center gap-1"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1.5 rounded-lg bg-white border border-slate-200 text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer text-xs flex items-center gap-1"
          >
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="p-5 space-y-5">
          
          {/* 4 Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5">
            
            {/* Card 1: Top Star Dish */}
            <div className="bg-white p-4 rounded-xl border border-slate-200/90 shadow-2xs space-y-2.5">
              <div className="flex items-center justify-between text-xs font-bold text-slate-800">
                <span className="flex items-center gap-1.5 text-amber-600">
                  <Award className="w-4 h-4" /> Món Ngôi Sao (Top 1)
                </span>
                <span className="text-[10px] text-slate-400">Gánh doanh thu</span>
              </div>
              {menu_engineering?.top_stars?.[0] ? (
                <div>
                  <div className="text-sm font-bold text-slate-900 truncate">
                    {menu_engineering.top_stars[0].dish_name}
                  </div>
                  <div className="text-xs text-slate-500 mt-1 flex items-center justify-between">
                    <span>Đóng góp: <strong className="text-emerald-600">{menu_engineering.top_stars[0].revenue_pct}%</strong> DT</span>
                    <span>~{menu_engineering.top_stars[0].avg_daily_qty} phần/ngày</span>
                  </div>
                </div>
              ) : (
                <div className="text-xs text-slate-400">Chưa đủ dữ liệu</div>
              )}
            </div>

            {/* Card 2: Weather Sensitivity */}
            <div className="bg-white p-4 rounded-xl border border-slate-200/90 shadow-2xs space-y-2.5">
              <div className="flex items-center justify-between text-xs font-bold text-slate-800">
                <span className="flex items-center gap-1.5 text-sky-600">
                  <Sun className="w-4 h-4" /> Độ Nhạy Thời Tiết
                </span>
                <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded-sm ${
                  weather_sensitivity?.score >= 60 ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'
                }`}>
                  {weather_sensitivity?.level} ({weather_sensitivity?.score}/100)
                </span>
              </div>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between text-slate-600">
                  <span>Nắng nóng (&gt;33°C):</span>
                  <strong className="text-amber-700">{weather_sensitivity?.hot_day_avg_rev?.toLocaleString('vi-VN')} đ/ngày</strong>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Ngày mưa dông:</span>
                  <strong className="text-blue-700">{weather_sensitivity?.rainy_day_avg_rev?.toLocaleString('vi-VN')} đ/ngày</strong>
                </div>
              </div>
            </div>

            {/* Card 3: Weekend Lift */}
            <div className="bg-white p-4 rounded-xl border border-slate-200/90 shadow-2xs space-y-2.5">
              <div className="flex items-center justify-between text-xs font-bold text-slate-800">
                <span className="flex items-center gap-1.5 text-purple-600">
                  <Calendar className="w-4 h-4" /> Hiệu Ứng Cuối Tuần
                </span>
                <span className="text-[10px] text-slate-400">Tăng trưởng</span>
              </div>
              <div>
                <div className="text-base font-extrabold text-purple-700 flex items-center gap-1">
                  +{day_of_week_pattern?.weekend_lift_pct}%
                  <ArrowUpRight className="w-4 h-4 text-purple-600" />
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  Cao điểm: <strong>{day_of_week_pattern?.peak_day}</strong> | Thấp nhất: <strong>{day_of_week_pattern?.lull_day}</strong>
                </div>
              </div>
            </div>

            {/* Card 4: Underperforming Dish */}
            <div className="bg-white p-4 rounded-xl border border-slate-200/90 shadow-2xs space-y-2.5">
              <div className="flex items-center justify-between text-xs font-bold text-slate-800">
                <span className="flex items-center gap-1.5 text-rose-600">
                  <AlertTriangle className="w-4 h-4" /> Cần Tối Ưu Menu
                </span>
                <span className="text-[10px] text-slate-400">Bán chậm</span>
              </div>
              {menu_engineering?.slow_movers?.[0] ? (
                <div>
                  <div className="text-sm font-bold text-slate-900 truncate">
                    {menu_engineering.slow_movers[0].dish_name}
                  </div>
                  <div className="text-xs text-slate-500 mt-1 flex items-center justify-between">
                    <span>Chỉ chiếm: <strong>{menu_engineering.slow_movers[0].revenue_pct}%</strong> DT</span>
                    <span>~{menu_engineering.slow_movers[0].avg_daily_qty} phần/ngày</span>
                  </div>
                </div>
              ) : (
                <div className="text-xs text-slate-400">Đang đồng đều</div>
              )}
            </div>

          </div>

          {/* Weather Narrative Banner */}
          {weather_sensitivity?.narrative && (
            <div className="bg-white/80 backdrop-blur-xs p-3.5 rounded-xl border border-purple-100 text-xs text-slate-700 leading-relaxed flex items-start gap-2.5 shadow-2xs">
              <Lightbulb className="w-4 h-4 text-purple-600 shrink-0 mt-0.5" />
              <div>
                <strong className="text-purple-950 font-bold">Quy luật tác động thời tiết lên doanh thu: </strong>
                {weather_sensitivity.narrative}
              </div>
            </div>
          )}

          {/* Actionable Recommendations */}
          {actionable_recommendations?.length > 0 && (
            <div className="bg-white p-4.5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  Đề Xuất Hành Động Thực Tế Dành Cho Chủ Quán ({actionable_recommendations.length} Khuyến nghị AI)
                </h3>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {actionable_recommendations.map((rec, i) => (
                  <div key={i} className="p-3.5 rounded-xl bg-slate-50/80 border border-slate-200 hover:border-purple-300 hover:bg-purple-50/30 transition-all space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[11px] font-bold text-slate-800 truncate">{rec.title}</span>
                      {getPriorityBadge(rec.priority)}
                    </div>
                    <p className="text-[11px] text-slate-600 leading-relaxed">
                      {rec.description}
                    </p>
                    {rec.impact && (
                      <div className="text-[10px] text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded-md inline-block">
                        🎯 Hiệu quả kỳ vọng: {rec.impact}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>
      )}

    </div>
  );
}
