import React, { useState } from 'react';
import { 
  UtensilsCrossed, 
  Layers, 
  Search, 
  ChevronRight, 
  Plus, 
  Sparkles, 
  X, 
  Trash2, 
  Check,
  AlertCircle,
  ShoppingBag
} from 'lucide-react';
import { createDishWithRecipe, deleteDish, smartAddRecipeItem, deleteRecipeItem } from '../services/api';
import Pagination from '../components/Pagination';

export default function RecipesPage({ dishes = [], recipes = [], ingredients = [], onRefresh }) {
  const [selectedDishId, setSelectedDishId] = useState(dishes?.[0]?.id || '');
  const [searchTerm, setSearchTerm] = useState('');
  
  // Modal states
  const [showAddDishModal, setShowAddDishModal] = useState(false);
  const [showAddIngredientModal, setShowAddIngredientModal] = useState(false);
  
  // Combined Add Dish + Recipe Form State
  const [newDishName, setNewDishName] = useState('');
  const [newDishCategory, setNewDishCategory] = useState('Phở & Bún');
  const [newDishPrice, setNewDishPrice] = useState('50000');
  const [dishIngredientsList, setDishIngredientsList] = useState([
    { ingredient_name: '', quantity: '0.15', unit: 'kg', cost_per_unit: '50000' }
  ]);
  const [isSubmittingDish, setIsSubmittingDish] = useState(false);

  // Add Recipe Item to Existing Dish form
  const [selectedIngMode, setSelectedIngMode] = useState('new'); // 'existing' | 'new'
  const [existingIngId, setExistingIngId] = useState('');
  const [customIngName, setCustomIngName] = useState('');
  const [customIngUnit, setCustomIngUnit] = useState('kg');
  const [customIngPrice, setCustomIngPrice] = useState('50000');
  const [recipeQuantity, setRecipeQuantity] = useState('0.15');
  const [isSubmittingIng, setIsSubmittingIng] = useState(false);

  // Pagination for dishes list
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Open Add Dish Modal with clean default rows
  const handleOpenAddDishModal = () => {
    setNewDishName('');
    setNewDishCategory('Phở & Bún');
    setNewDishPrice('50000');
    setDishIngredientsList([
      { ingredient_name: '', quantity: '0.15', unit: 'kg', cost_per_unit: '50000' }
    ]);
    setShowAddDishModal(true);
  };

  // Add Row in Combined Modal
  const handleAddIngredientRow = () => {
    setDishIngredientsList([
      ...dishIngredientsList,
      { ingredient_name: '', quantity: '0.1', unit: 'kg', cost_per_unit: '40000' }
    ]);
  };

  // Remove Row in Combined Modal
  const handleRemoveIngredientRow = (index) => {
    if (dishIngredientsList.length === 1) {
      setDishIngredientsList([{ ingredient_name: '', quantity: '0.1', unit: 'kg', cost_per_unit: '40000' }]);
      return;
    }
    const updated = [...dishIngredientsList];
    updated.splice(index, 1);
    setDishIngredientsList(updated);
  };

  // Update Row in Combined Modal
  const handleUpdateIngredientRow = (index, field, value) => {
    const updated = [...dishIngredientsList];
    updated[index][field] = value;

    // If typing an existing ingredient name, auto-fill unit & cost if matched
    if (field === 'ingredient_name' && value) {
      const match = ingredients.find(i => i.name.toLowerCase() === value.trim().toLowerCase());
      if (match) {
        updated[index].unit = match.unit || 'kg';
        updated[index].cost_per_unit = match.cost_per_unit || '50000';
      }
    }

    setDishIngredientsList(updated);
  };

  // Handle Create Dish with Recipes combined
  const handleCreateDishWithRecipe = async (e) => {
    e.preventDefault();
    if (!newDishName.trim()) {
      alert('Vui lòng nhập tên món ăn!');
      return;
    }

    // Filter valid ingredients
    const validIngredients = dishIngredientsList
      .filter(it => it.ingredient_name && it.ingredient_name.trim() !== '')
      .map(it => ({
        ingredient_name: it.ingredient_name.trim(),
        quantity: parseFloat(it.quantity) || 0.1,
        unit: it.unit || 'kg',
        cost_per_unit: parseFloat(it.cost_per_unit) || 50000,
      }));

    try {
      setIsSubmittingDish(true);
      const res = await createDishWithRecipe({
        name: newDishName.trim(),
        category: newDishCategory,
        price: parseFloat(newDishPrice) || 0,
        ingredients: validIngredients,
      });

      setShowAddDishModal(false);
      setNewDishName('');
      if (res.data?.dish_id) {
        setSelectedDishId(res.data.dish_id);
      }
      if (onRefresh) await onRefresh();
    } catch (err) {
      alert('Lỗi tạo món & nguyên liệu: ' + (err.response?.data?.detail || err.message));
    } finally {
      setIsSubmittingDish(false);
    }
  };

  // Handle Delete Dish
  const handleDeleteDish = async (dishId, dishName) => {
    if (!window.confirm(`Bạn có chắc muốn xóa món "${dishName}" (${dishId}) và toàn bộ công thức của món này không?`)) return;
    try {
      await deleteDish(dishId);
      if (onRefresh) await onRefresh();
    } catch (err) {
      alert('Lỗi xóa món: ' + err.message);
    }
  };

  // Handle Add Ingredient to Existing Dish
  const handleAddRecipeIngredient = async (e) => {
    e.preventDefault();
    if (!activeDish) {
      alert('Vui lòng chọn món ăn trước!');
      return;
    }
    const qty = parseFloat(recipeQuantity);
    if (!qty || qty <= 0) {
      alert('Vui lòng nhập định lượng hợp lệ (> 0)');
      return;
    }

    try {
      setIsSubmittingIng(true);
      if (selectedIngMode === 'existing') {
        if (!existingIngId) {
          alert('Vui lòng chọn một nguyên liệu từ danh sách');
          return;
        }
        await smartAddRecipeItem({
          dish_id: activeDish.id,
          ingredient_id: existingIngId,
          quantity: qty,
        });
      } else {
        if (!customIngName.trim()) {
          alert('Vui lòng nhập tên nguyên liệu mới');
          return;
        }
        await smartAddRecipeItem({
          dish_id: activeDish.id,
          ingredient_name: customIngName.trim(),
          quantity: qty,
          unit: customIngUnit,
          cost_per_unit: parseFloat(customIngPrice) || 50000,
        });
      }

      setShowAddIngredientModal(false);
      setCustomIngName('');
      setRecipeQuantity('0.15');
      if (onRefresh) await onRefresh();
    } catch (err) {
      alert('Lỗi thêm nguyên liệu: ' + err.message);
    } finally {
      setIsSubmittingIng(false);
    }
  };

  // Handle Delete Ingredient from Recipe
  const handleDeleteRecipeItem = async (dishId, ingId, ingName) => {
    if (!window.confirm(`Xóa nguyên liệu "${ingName}" khỏi công thức món này?`)) return;
    try {
      await deleteRecipeItem(dishId, ingId);
      if (onRefresh) await onRefresh();
    } catch (err) {
      alert('Lỗi xóa nguyên liệu: ' + err.message);
    }
  };

  const filteredDishes = (dishes || []).filter(d => 
    d.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    d.category?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    d.id?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const paginatedDishes = filteredDishes.slice((currentPage - 1) * pageSize, currentPage * pageSize);
  const activeDish = dishes.find(d => d.id === selectedDishId) || dishes[0];
  const dishIngredients = recipes?.filter(r => r.dish_id === activeDish?.id) || [];

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Thực Đơn & Định Lượng Món Ăn (Recipes / BOM)</h1>
          <p className="text-sm text-slate-500 mt-1">
            Khai báo món ăn và định lượng nguyên liệu cấu thành. Khi nhập nguyên liệu mới, hệ thống sẽ <strong>tự động tạo nguyên liệu vào kho</strong>.
          </p>
        </div>

        <button
          onClick={handleOpenAddDishModal}
          className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-semibold shadow-md shadow-emerald-600/20 transition-all cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>Thêm Món Ăn & Định Lượng Mới</span>
        </button>
      </div>

      {(!dishes || dishes.length === 0) ? (
        /* Empty dishes state */
        <div className="bg-white p-12 rounded-2xl border border-slate-200 shadow-xs text-center space-y-4">
          <div className="w-16 h-16 bg-emerald-50 text-emerald-600 rounded-2xl flex items-center justify-center mx-auto">
            <UtensilsCrossed className="w-8 h-8" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-900">Thực Đơn Đang Trống</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
              Bạn chưa tạo món ăn nào cho quán. Hãy thêm món ăn kèm định lượng nguyên liệu đầu tiên để bắt đầu dự báo và quản lý đi chợ!
            </p>
          </div>
          <button
            onClick={handleOpenAddDishModal}
            className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold shadow-xs cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Thêm Món Ăn Đầu Tiên</span>
          </button>
        </div>
      ) : (
        /* Main Layout with Dishes List + Recipe Details */
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Left Column: List of Dishes */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between overflow-hidden">
            <div className="p-4 space-y-3">
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Tìm món ăn, đồ uống..."
                  value={searchTerm}
                  onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
                  className="pl-9 pr-4 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 w-full"
                />
              </div>

              <div className="space-y-1.5">
                {paginatedDishes.map((dish) => {
                  const isSelected = (activeDish?.id === dish.id);
                  return (
                    <div
                      key={dish.id}
                      onClick={() => setSelectedDishId(dish.id)}
                      className={`w-full flex items-center justify-between p-2.5 rounded-xl text-left transition-all cursor-pointer h-13 group ${
                        isSelected
                          ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/20 font-semibold'
                          : 'bg-slate-50 hover:bg-slate-100 text-slate-800 border border-slate-200/60'
                      }`}
                    >
                      <div className="truncate pr-2 flex-1">
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                            isSelected ? 'bg-emerald-700 text-white' : 'bg-slate-200 text-slate-600'
                          }`}>
                            {dish.id}
                          </span>
                          <h4 className="text-xs font-semibold truncate">{dish.name}</h4>
                        </div>
                        <span className={`text-[11px] block mt-0.5 ${isSelected ? 'text-emerald-100' : 'text-slate-400'}`}>
                          {dish.category} • {dish.price?.toLocaleString('vi-VN')} đ
                        </span>
                      </div>

                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          title="Xóa món ăn"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteDish(dish.id, dish.name);
                          }}
                          className={`p-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer ${
                            isSelected ? 'hover:bg-emerald-700 text-emerald-100 hover:text-white' : 'hover:bg-red-50 text-slate-400 hover:text-red-600'
                          }`}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                        <ChevronRight className={`w-4 h-4 shrink-0 ${isSelected ? 'text-white' : 'text-slate-400'}`} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <Pagination
              totalItems={filteredDishes.length}
              pageSize={pageSize}
              currentPage={currentPage}
              onPageChange={setCurrentPage}
              onPageSizeChange={setPageSize}
              compact={true}
            />
          </div>

          {/* Right Column: Recipe Details */}
          <div className="lg:col-span-2 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
            <div>
              {/* Active Dish Header */}
              <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-4">
                <div>
                  <span className="text-xs font-semibold text-emerald-600 uppercase tracking-wider">Định Lượng Chuẩn 1 Phần</span>
                  <h2 className="text-2xl font-bold text-slate-900 mt-0.5">{activeDish?.name}</h2>
                  <p className="text-xs text-slate-500 mt-1">
                    Mã món: <strong className="font-mono">{activeDish?.id}</strong> • Phân loại: <strong>{activeDish?.category}</strong> • Giá bán: <strong>{activeDish?.price?.toLocaleString('vi-VN')} VNĐ</strong>
                  </p>
                </div>

                <button
                  onClick={() => {
                    setSelectedIngMode('new');
                    setShowAddIngredientModal(true);
                  }}
                  className="inline-flex items-center gap-2 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold shadow-xs transition-all cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Thêm Nguyên Liệu Cho Món</span>
                </button>
              </div>

              {/* Recipe Breakdown Table */}
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                  <Layers className="w-4 h-4 text-slate-500" />
                  Bảng Bóc Tách Nguyên Liệu Cấu Thành ({dishIngredients.length} thành phần)
                </h3>
              </div>

              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <table className="w-full text-left text-xs table-fixed">
                  <thead>
                    <tr className="border-b border-slate-200 text-xs font-bold text-slate-500 uppercase bg-slate-50/80 h-10">
                      <th className="py-2.5 px-3 w-[15%]">Mã NL</th>
                      <th className="py-2.5 px-3 w-[40%]">Tên Nguyên Liệu</th>
                      <th className="py-2.5 px-3 text-right w-[20%]">Định Lượng / Phần</th>
                      <th className="py-2.5 px-3 w-[13%]">Đơn Vị</th>
                      <th className="py-2.5 px-3 text-center w-[12%]">Thao Tác</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-xs">
                    {dishIngredients.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-slate-400 italic">
                          <p>Món này chưa có công thức định lượng chi tiết.</p>
                          <button
                            onClick={() => {
                              setSelectedIngMode('new');
                              setShowAddIngredientModal(true);
                            }}
                            className="mt-2 text-emerald-600 hover:text-emerald-700 font-semibold cursor-pointer underline inline-flex items-center gap-1"
                          >
                            <Plus className="w-3.5 h-3.5" /> Thêm nguyên liệu đầu tiên cho món này
                          </button>
                        </td>
                      </tr>
                    ) : (
                      dishIngredients.map((r) => (
                        <tr key={r.ingredient_id} className="hover:bg-slate-50/80">
                          <td className="py-2.5 px-3 font-mono text-slate-500 break-words">{r.ingredient_id}</td>
                          <td className="py-2.5 px-3 font-semibold text-slate-800 break-words leading-tight">{r.ingredient_name}</td>
                          <td className="py-2.5 px-3 text-right font-bold text-emerald-700 text-xs break-words">
                            {r.quantity}
                          </td>
                          <td className="py-2.5 px-3 text-slate-500 break-words">{r.unit}</td>
                          <td className="py-2.5 px-3 text-center">
                            <button
                              onClick={() => handleDeleteRecipeItem(activeDish.id, r.ingredient_id, r.ingredient_name)}
                              className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors cursor-pointer"
                              title="Xóa nguyên liệu khỏi món"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="mt-6 p-4 rounded-xl bg-slate-50 border border-slate-200/80 text-xs text-slate-600 leading-relaxed space-y-1">
              <p className="font-semibold text-slate-700 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                Cơ Chế Bóc Tách Tự Động & Tự Tạo Kho:
              </p>
              <p className="text-slate-500">
                Khi bạn nhập nguyên liệu vào món ăn, hệ thống sẽ tự động đồng bộ sang <strong>Kho nguyên liệu</strong> và gắn AI Tag phân loại. Khi có đơn đặt trước hoặc dự báo tăng trưởng, hệ thống sẽ tự bóc tách chính xác khối lượng cần đi chợ.
              </p>
            </div>
          </div>

        </div>
      )}

      {/* Datalist for existing ingredients autocomplete */}
      <datalist id="existing-ingredients-list">
        {ingredients.map(ing => (
          <option key={ing.id} value={ing.name} />
        ))}
      </datalist>

      {/* Modal 1: GỘP THÊM MÓN ĂN & THÊM TOÀN BỘ NGUYÊN LIỆU (COMBINED MODAL) */}
      {showAddDishModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-emerald-100 text-emerald-700 rounded-xl">
                  <UtensilsCrossed className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">Thêm Món Ăn & Định Lượng Nguyên Liệu</h3>
                  <p className="text-xs text-slate-500">Khai báo thông tin món và các nguyên liệu cấu thành trong cùng 1 bước</p>
                </div>
              </div>
              <button onClick={() => setShowAddDishModal(false)} className="text-slate-400 hover:text-slate-600 cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Form Body */}
            <form onSubmit={handleCreateDishWithRecipe} className="flex-1 overflow-y-auto p-6 space-y-5 text-xs">
              
              {/* Section 1: Thông tin món */}
              <div className="space-y-3 bg-slate-50 p-4 rounded-xl border border-slate-200">
                <h4 className="font-bold text-slate-800 text-xs flex items-center gap-1.5 uppercase tracking-wider">
                  <span>1. Thông Tin Món Ăn / Đồ Uống</span>
                </h4>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="sm:col-span-1">
                    <label className="block font-semibold text-slate-700 mb-1">Tên Món (*)</label>
                    <input
                      type="text"
                      required
                      placeholder="Ví dụ: Phở Bò Tái Nạm..."
                      value={newDishName}
                      onChange={(e) => setNewDishName(e.target.value)}
                      className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Phân Loại Món</label>
                    <select
                      value={newDishCategory}
                      onChange={(e) => setNewDishCategory(e.target.value)}
                      className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-xs font-medium focus:outline-none cursor-pointer"
                    >
                      <option value="Phở & Bún">Phở & Bún</option>
                      <option value="Cơm & Bánh Mì">Cơm & Bánh Mì</option>
                      <option value="Ăn Vặt">Ăn Vặt / Khai Vị</option>
                      <option value="Cà Phê">Cà Phê</option>
                      <option value="Trà & Trái Cây">Trà & Trái Cây</option>
                      <option value="Khác">Khác</option>
                    </select>
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Giá Bán Niêm Yết (VNĐ)</label>
                    <input
                      type="number"
                      required
                      placeholder="Ví dụ: 55000"
                      value={newDishPrice}
                      onChange={(e) => setNewDishPrice(e.target.value)}
                      className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* Section 2: Danh sách nguyên liệu cấu thành */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-bold text-slate-800 text-xs flex items-center gap-1.5 uppercase tracking-wider">
                      <span>2. Bảng Định Lượng Nguyên Liệu Cấu Thành ({dishIngredientsList.length} thành phần)</span>
                    </h4>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      Gõ tên nguyên liệu; hệ thống sẽ <strong>tự động tạo vào Kho</strong> và gắn AI Tag nếu là nguyên liệu mới.
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={handleAddIngredientRow}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 rounded-lg text-xs font-semibold cursor-pointer transition-colors"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Thêm Nguyên Liệu</span>
                  </button>
                </div>

                {/* Ingredients Rows */}
                <div className="space-y-2.5 max-h-60 overflow-y-auto pr-1">
                  {dishIngredientsList.map((row, idx) => (
                    <div key={idx} className="flex items-center gap-2 p-2.5 bg-slate-50/90 border border-slate-200 rounded-xl">
                      <span className="w-5 h-5 rounded-full bg-slate-200 text-slate-600 flex items-center justify-center font-bold text-[10px] shrink-0">
                        {idx + 1}
                      </span>

                      {/* Ingredient Name */}
                      <div className="flex-1">
                        <input
                          type="text"
                          required
                          list="existing-ingredients-list"
                          placeholder="Tên nguyên liệu (vd: Thịt bò, Hành tây, Sữa tươi...)"
                          value={row.ingredient_name}
                          onChange={(e) => handleUpdateIngredientRow(idx, 'ingredient_name', e.target.value)}
                          className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                        />
                      </div>

                      {/* Quantity */}
                      <div className="w-24">
                        <input
                          type="number"
                          step="any"
                          required
                          placeholder="Định lượng"
                          value={row.quantity}
                          onChange={(e) => handleUpdateIngredientRow(idx, 'quantity', e.target.value)}
                          className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-bold text-emerald-800 text-right focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                        />
                      </div>

                      {/* Unit */}
                      <div className="w-22">
                        <select
                          value={row.unit}
                          onChange={(e) => handleUpdateIngredientRow(idx, 'unit', e.target.value)}
                          className="w-full px-2 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-medium focus:outline-none cursor-pointer"
                        >
                          <option value="kg">kg</option>
                          <option value="gram">gram</option>
                          <option value="lít">lít</option>
                          <option value="ml">ml</option>
                          <option value="quả">quả</option>
                          <option value="hộp">hộp</option>
                          <option value="lon">lon</option>
                          <option value="gói">gói</option>
                          <option value="bó">bó</option>
                        </select>
                      </div>

                      {/* Cost per unit */}
                      <div className="w-28 hidden sm:block">
                        <input
                          type="number"
                          placeholder="Giá mua/đv"
                          value={row.cost_per_unit}
                          onChange={(e) => handleUpdateIngredientRow(idx, 'cost_per_unit', e.target.value)}
                          className="w-full px-2 py-1.5 bg-white border border-slate-200 rounded-lg text-xs text-right focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                          title="Giá mua ước tính (VNĐ/đơn vị)"
                        />
                      </div>

                      {/* Remove row button */}
                      <button
                        type="button"
                        onClick={() => handleRemoveIngredientRow(idx)}
                        className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors cursor-pointer shrink-0"
                        title="Xóa dòng nguyên liệu này"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>

                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-[11px] text-emerald-800 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Mẹo: Định lượng cho 1 phần là khối lượng nguyên liệu tiêu hao khi bán được 1 món (vd: 1 tô phở cần <strong>0.15</strong> kg thịt bò).</span>
                </div>
              </div>

              {/* Modal Actions */}
              <div className="flex items-center justify-end gap-2.5 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowAddDishModal(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-semibold cursor-pointer"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingDish}
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-semibold cursor-pointer shadow-md shadow-emerald-600/20 inline-flex items-center gap-2"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>{isSubmittingDish ? 'Đang lưu món & tạo kho...' : 'Lưu Món Ăn & Toàn Bộ Định Lượng'}</span>
                </button>
              </div>

            </form>

          </div>
        </div>
      )}

      {/* Modal 2: Add Single Ingredient to Existing Dish */}
      {showAddIngredientModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <h3 className="text-base font-bold text-slate-900">Thêm Nguyên Liệu Cho: {activeDish?.name}</h3>
                <p className="text-xs text-slate-500 mt-0.5">Tự động tạo nguyên liệu mới vào danh mục kho nếu chưa có</p>
              </div>
              <button onClick={() => setShowAddIngredientModal(false)} className="text-slate-400 hover:text-slate-600 cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Mode Selector Tabs */}
            <div className="flex bg-slate-100 p-1 rounded-xl gap-1 text-xs font-semibold">
              <button
                type="button"
                onClick={() => setSelectedIngMode('new')}
                className={`flex-1 py-1.5 rounded-lg transition-all cursor-pointer ${
                  selectedIngMode === 'new' ? 'bg-white text-emerald-700 shadow-xs' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                ✨ Nhập Nguyên Liệu Mới (Auto Tạo Vào Kho)
              </button>
              <button
                type="button"
                onClick={() => setSelectedIngMode('existing')}
                className={`flex-1 py-1.5 rounded-lg transition-all cursor-pointer ${
                  selectedIngMode === 'existing' ? 'bg-white text-emerald-700 shadow-xs' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                📦 Chọn Từ Kho Đã Có ({ingredients?.length || 0})
              </button>
            </div>

            <form onSubmit={handleAddRecipeIngredient} className="space-y-3.5 text-xs">
              
              {selectedIngMode === 'existing' ? (
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Chọn Nguyên Liệu Trong Kho (*)</label>
                  {(!ingredients || ingredients.length === 0) ? (
                    <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-xs">
                      Kho chưa có nguyên liệu nào. Vui lòng chuyển sang tab <strong>"Nhập Nguyên Liệu Mới"</strong> ở trên!
                    </div>
                  ) : (
                    <select
                      value={existingIngId}
                      onChange={(e) => setExistingIngId(e.target.value)}
                      required
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium focus:outline-none cursor-pointer"
                    >
                      <option value="">-- Chọn nguyên liệu có sẵn --</option>
                      {ingredients.map((ing) => (
                        <option key={ing.id} value={ing.id}>
                          {ing.name} ({ing.unit}) - {ing.category_tag || 'Khác'}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              ) : (
                <>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Tên Nguyên Liệu Mới (*)</label>
                    <input
                      type="text"
                      required
                      placeholder="Ví dụ: Thịt bò nạm, Bánh phở tươi, Hành hoa, Sữa tươi tiệt trùng..."
                      value={customIngName}
                      onChange={(e) => setCustomIngName(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">Đơn Vị Tính</label>
                      <select
                        value={customIngUnit}
                        onChange={(e) => setCustomIngUnit(e.target.value)}
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium focus:outline-none cursor-pointer"
                      >
                        <option value="kg">kg (Kilogram)</option>
                        <option value="gram">gram</option>
                        <option value="lít">lít</option>
                        <option value="ml">ml</option>
                        <option value="quả">quả / trái</option>
                        <option value="hộp">hộp</option>
                        <option value="lon">lon</option>
                        <option value="gói">gói</option>
                        <option value="bó">bó</option>
                      </select>
                    </div>

                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">Giá Mua Ước Tính (VNĐ)</label>
                      <input
                        type="number"
                        placeholder="Ví dụ: 80000"
                        value={customIngPrice}
                        onChange={(e) => setCustomIngPrice(e.target.value)}
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                      />
                    </div>
                  </div>
                </>
              )}

              {/* Định Lượng / 1 Phần */}
              <div className="bg-emerald-50/70 border border-emerald-200 p-3 rounded-xl space-y-1">
                <label className="block font-bold text-emerald-900 mb-1">
                  Định Lượng Cho 1 Suất Ăn / 1 Ly (* {selectedIngMode === 'new' ? customIngUnit : (ingredients.find(i=>i.id===existingIngId)?.unit || 'đơn vị')})
                </label>
                <input
                  type="number"
                  step="any"
                  required
                  placeholder="Ví dụ: 0.15 (kg), 250 (ml)..."
                  value={recipeQuantity}
                  onChange={(e) => setRecipeQuantity(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-emerald-300 rounded-lg text-xs font-bold text-emerald-800 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                />
                <p className="text-[11px] text-emerald-700">
                  Ví dụ: 1 tô Phở cần <strong>0.15</strong> kg thịt bò, hoặc 1 ly Cà phê cần <strong>0.025</strong> kg hạt cà phê.
                </p>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowAddIngredientModal(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-semibold cursor-pointer"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingIng}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-semibold cursor-pointer shadow-xs inline-flex items-center gap-1.5"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>{isSubmittingIng ? 'Đang lưu...' : 'Lưu Vào Món & Tạo Kho'}</span>
                </button>
              </div>

            </form>

          </div>
        </div>
      )}

    </div>
  );
}

