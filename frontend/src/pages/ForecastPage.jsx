import React, { useState } from 'react';
import { 
  TrendingUp, 
  Sparkles, 
  Search, 
  BarChart3, 
  Info,
  CalendarCheck,
  MapPin,
  CloudSun,
  CloudRain,
  Sun,
  CloudLightning,
  Snowflake,
  Thermometer,
  Droplets
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid, 
  Legend 
} from 'recharts';
import Pagination from '../components/Pagination';
import DataInsightCard from '../components/DataInsightCard';

const CITY_OPTIONS = [
  { id: 'ho_chi_minh', name: 'TP. Hồ Chí Minh', region: 'Miền Nam' },
  { id: 'ha_noi', name: 'Hà Nội', region: 'Miền Bắc' },
  { id: 'da_nang', name: 'Đà Nẵng', region: 'Miền Trung' },
  { id: 'can_tho', name: 'Cần Thơ', region: 'Miền Tây' },
  { id: 'hai_phong', name: 'Hải Phòng', region: 'Miền Bắc' },
  { id: 'da_lat', name: 'Đà Lạt (Lâm Đồng)', region: 'Tây Nguyên' },
];

export default function ForecastPage({ forecastData, branchId, selectedCity = 'ho_chi_minh', onCityChange }) {
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDishId, setSelectedDishId] = useState('D01');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  if (!forecastData || !forecastData.branches) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  const branchForecast = forecastData.branches?.[0];
  const allDishes = branchForecast?.dishes || [];

  if (allDishes.length === 0) {
    return (
      <div className="bg-white p-12 rounded-2xl border border-slate-200 shadow-xs text-center space-y-4">
        <div className="w-16 h-16 bg-purple-50 text-purple-600 rounded-2xl flex items-center justify-center mx-auto">
          <Sparkles className="w-8 h-8" />
        </div>
        <div>
          <h3 className="text-lg font-bold text-slate-900">Chưa Có Dữ Liệu Dự Báo Cho Quán Này</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
            Hiện tại bạn chưa thêm món ăn hoặc chưa tải lên file dữ liệu bán hàng lịch sử. Hãy thêm món tại mục "Thực Đơn" hoặc tải file CSV lên nhé!
          </p>
        </div>
      </div>
    );
  }

  const categories = ['ALL', 'Phở & Bún', 'Cơm & Bánh Mì', 'Ăn Vặt', 'Cà Phê', 'Trà & Trái Cây', 'Hải Sản', 'Món Nước', 'Món Khô'];

  const filteredDishes = allDishes.filter((d) => {
    const matchCat = selectedCategory === 'ALL' || d.category === selectedCategory;
    const matchSearch = d.dish_name.toLowerCase().includes(searchTerm.toLowerCase()) || d.dish_id.toLowerCase().includes(searchTerm.toLowerCase());
    return matchCat && matchSearch;
  });

  // Pagination slice
  const paginatedDishes = filteredDishes.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  // Selected dish for line chart
  const currentDish = allDishes.find((d) => d.dish_id === selectedDishId) || allDishes[0];

  const chartData = currentDish?.daily_forecasts?.map((day) => ({
    date: `${day.day_name} (${day.date.slice(5)})`,
    XGBoost: day.xgb_forecast || day.xgb_quantity,
    Baseline: day.baseline_forecast || day.baseline_quantity,
    Preorders: day.confirmed_preorders || day.preorder_quantity,
    Expected: day.expected_demand || day.final_forecast_quantity,
  })) || [];

  // Lấy danh sách 7 ngày thời tiết từ món đầu tiên
  const weatherDays = allDishes[0]?.daily_forecasts || [];

  const getWeatherIcon = (cond) => {
    switch (cond) {
      case 'nang_nong':
        return <Sun className="w-4 h-4 text-amber-500" />;
      case 'mua_rao':
        return <CloudRain className="w-4 h-4 text-blue-500" />;
      case 'mua_bao':
        return <CloudLightning className="w-4 h-4 text-purple-600" />;
      case 'lanh_ret':
        return <Snowflake className="w-4 h-4 text-cyan-500" />;
      default:
        return <CloudSun className="w-4 h-4 text-emerald-500" />;
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header with City / Location Selector */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-xl font-bold text-slate-900">Dự Báo Nhu Cầu Bán Hàng 7 Ngày Tới</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-100 text-purple-800 border border-purple-200 flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-purple-600" /> Universal XGBoost ML
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200 flex items-center gap-1">
              <CloudSun className="w-3 h-3 text-blue-600" /> Weather-Aware API
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Mô hình kết hợp chu kỳ thứ, ngày lễ, Tết Nguyên Đán và **dự báo thời tiết thực tế** theo từng địa phương.
          </p>
        </div>

        {/* City / Location Dropdown */}
        <div className="flex items-center gap-3 self-start lg:self-auto bg-slate-50 border border-slate-200 p-2 rounded-xl">
          <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
            <MapPin className="w-4 h-4 text-red-500 shrink-0" />
            <span>Địa điểm thời tiết:</span>
          </div>
          <select
            value={selectedCity}
            onChange={(e) => onCityChange && onCityChange(e.target.value)}
            className="bg-white border border-slate-300 text-xs font-semibold rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-emerald-500 text-slate-900 cursor-pointer shadow-xs"
          >
            {CITY_OPTIONS.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.region})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* 7-Day Weather Forecast Strip */}
      {weatherDays.length > 0 && (
        <div className="bg-linear-to-r from-sky-50 via-blue-50 to-indigo-50 border border-sky-200 p-4 rounded-2xl shadow-xs">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-bold text-sky-950 uppercase tracking-wider flex items-center gap-2">
              <CloudSun className="w-4 h-4 text-sky-600" />
              Dự Báo Thời Tiết 7 Ngày Tiếp Theo Tại {CITY_OPTIONS.find(c => c.id === selectedCity)?.name || 'Địa phương'}
            </h3>
            <span className="text-[11px] text-sky-700 bg-sky-100/80 border border-sky-300 px-2 py-0.5 rounded-full font-medium">
              Open-Meteo API Real-time
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5">
            {weatherDays.map((day, idx) => {
              const cond = day.weather_condition || 'nang_dep';
              return (
                <div 
                  key={idx} 
                  className={`bg-white/90 backdrop-blur-xs p-3 rounded-xl border transition-all hover:shadow-md ${
                    idx === 0 ? 'border-emerald-400 ring-2 ring-emerald-400/20' : 'border-sky-100'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="font-bold text-slate-800">{day.day_name}</span>
                    <span className="text-[10px] text-slate-500">{day.date.slice(5)}</span>
                  </div>

                  <div className="flex items-center gap-1.5 my-1.5">
                    {getWeatherIcon(cond)}
                    <span className="text-xs font-bold text-slate-900">{day.temperature || 32}°C</span>
                  </div>

                  <div className="text-[11px] text-slate-600 font-medium truncate mb-1" title={day.weather_desc}>
                    {day.weather_desc || 'Nắng đẹp'}
                  </div>

                  {day.precipitation_mm > 0 ? (
                    <div className="flex items-center gap-1 text-[10px] text-blue-600 font-semibold">
                      <Droplets className="w-3 h-3" /> {day.precipitation_mm} mm
                    </div>
                  ) : (
                    <div className="text-[10px] text-emerald-600 font-semibold">
                      Tạnh ráo
                    </div>
                  )}

                  {idx === 0 && (
                    <span className="mt-2 block text-center text-[9px] font-bold bg-emerald-100 text-emerald-800 py-0.5 rounded-md">
                      Ngày mai
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* AI Store Data Insights Card */}
      <DataInsightCard branchId={branchId} selectedCity={selectedCity} />

      {/* Selected Dish Trend Chart */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-emerald-600" />
              Biểu Đồ So Sánh Dự Báo 7 Ngày: <span className="text-emerald-600">{currentDish?.dish_name}</span>
            </h3>
            <p className="text-xs text-slate-500">
              Đối chiếu giữa mô hình <strong>XGBoost Regressor</strong>, <strong>Baseline (Trung bình tuần)</strong> và <strong>Đơn đặt trước</strong>
            </p>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold text-slate-500">Chọn món xem đồ thị:</label>
            <select
              value={selectedDishId}
              onChange={(e) => setSelectedDishId(e.target.value)}
              className="bg-slate-100 border border-slate-200 text-xs font-semibold rounded-lg px-3 py-1.5 focus:outline-none text-slate-800 cursor-pointer"
            >
              {allDishes.map((d) => (
                <option key={d.dish_id} value={d.dish_id}>
                  {d.dish_name} ({d.category})
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#64748b' }} />
              <YAxis tick={{ fontSize: 12, fill: '#64748b' }} unit=" phần" />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1e293b', borderRadius: '12px', border: 'none', color: '#fff', fontSize: '12px' }}
              />
              <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
              <Line type="monotone" dataKey="Expected" name="Tổng Nhu Cầu Kỳ Vọng" stroke="#10b981" strokeWidth={3.5} dot={{ r: 5 }} />
              <Line type="monotone" dataKey="XGBoost" name="Dự Báo XGBoost" stroke="#8b5cf6" strokeWidth={2.5} strokeDasharray="4 4" />
              <Line type="monotone" dataKey="Baseline" name="Baseline (Tuần trước)" stroke="#94a3b8" strokeWidth={2} />
              <Line type="monotone" dataKey="Preorders" name="Đơn Đặt Trước" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Full Dishes Forecast Table with Pagination */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        
        {/* Filters Toolbar */}
        <div className="p-5 pb-3 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex flex-wrap items-center gap-1.5">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => {
                  setSelectedCategory(cat);
                  setCurrentPage(1);
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  selectedCategory === cat
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {cat === 'ALL' ? `Tất cả món (${allDishes.length})` : cat}
              </button>
            ))}
          </div>

          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Tìm kiếm món ăn, đồ uống..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              className="pl-9 pr-4 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 w-64"
            />
          </div>
        </div>

        {/* Table */}
        <div className="w-full overflow-x-auto">
          <table className="w-full text-left text-xs table-fixed min-w-[800px]">
            <thead>
              <tr className="border-b border-slate-200 font-bold text-slate-500 uppercase bg-slate-50/80">
                <th className="py-2.5 px-2.5 w-[22%]">Tên Món</th>
                <th className="py-2.5 px-2 w-[12%]">Phân Loại</th>
                <th className="py-2.5 px-2 w-[11%] text-right">Giá Bán</th>
                <th className="py-2.5 px-2 w-[13%] text-center bg-emerald-50/70 text-emerald-900">
                  Ngày Mai
                </th>
                <th className="py-2.5 px-1 text-center text-slate-600 w-[7%]">+2d</th>
                <th className="py-2.5 px-1 text-center text-slate-600 w-[7%]">+3d</th>
                <th className="py-2.5 px-1 text-center text-slate-600 w-[7%]">+4d</th>
                <th className="py-2.5 px-1 text-center text-slate-600 w-[7%]">+5d</th>
                <th className="py-2.5 px-1 text-center text-slate-600 w-[7%]">+6d</th>
                <th className="py-2.5 px-1 text-center text-slate-600 w-[7%]">+7d</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {paginatedDishes.map((dish) => {
                const day1 = dish.daily_forecasts[0] || {};
                return (
                  <tr 
                    key={dish.dish_id}
                    onClick={() => setSelectedDishId(dish.dish_id)}
                    className={`hover:bg-emerald-50/40 transition-colors cursor-pointer ${
                      selectedDishId === dish.dish_id ? 'bg-emerald-50/80 font-semibold' : ''
                    }`}
                  >
                    <td className="py-2.5 px-2.5 font-semibold text-slate-900 break-words leading-tight align-middle">
                      {dish.dish_name}
                    </td>
                    <td className="py-2.5 px-2 align-middle">
                      <span className="px-1.5 py-0.5 rounded-md bg-slate-100 text-slate-600 text-[10px] break-words inline-block leading-tight">
                        {dish.category}
                      </span>
                    </td>
                    <td className="py-2.5 px-2 text-right text-slate-600 align-middle">
                      {dish.price ? dish.price.toLocaleString('vi-VN') : '0'} đ
                    </td>
                    <td className="py-2.5 px-2 text-center bg-emerald-50/50 align-middle">
                      <span className="text-xs font-bold text-emerald-700">
                        {day1.expected_demand || day1.final_forecast_quantity || 0}
                      </span>
                      {(day1.confirmed_preorders > 0 || day1.preorder_quantity > 0) && (
                        <span className="block text-[9px] text-blue-600 font-semibold">
                          (Đặt: +{day1.confirmed_preorders || day1.preorder_quantity})
                        </span>
                      )}
                    </td>
                    {dish.daily_forecasts.slice(1).map((d, idx) => (
                      <td key={idx} className="py-2.5 px-1 text-center text-slate-700 align-middle">
                        {d.expected_demand || d.final_forecast_quantity || 0}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination Component */}
        <Pagination
          totalItems={filteredDishes.length}
          pageSize={pageSize}
          currentPage={currentPage}
          onPageChange={setCurrentPage}
          onPageSizeChange={setPageSize}
        />

      </div>

    </div>
  );
}
