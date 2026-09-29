import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import DashboardPage from './pages/DashboardPage';
import ForecastPage from './pages/ForecastPage';
import PurchasePage from './pages/PurchasePage';
import InventoryPage from './pages/InventoryPage';
import RecipesPage from './pages/RecipesPage';
import PreordersPage from './pages/PreordersPage';

import BranchModal from './components/BranchModal';
import UploadSalesModal from './components/UploadSalesModal';
import UploadPurchaseModal from './components/UploadPurchaseModal';
import IngredientModal from './components/IngredientModal';

import { 
  getBranches, 
  getDashboardSummary, 
  getForecast, 
  getPurchaseRecommendations, 
  getInventory, 
  getDishes, 
  getRecipes, 
  getPreorders,
  getIngredients,
  retrainModel,
  resetDemoData,
  clearCleanData
} from './services/api';

export default function App() {
  const [currentTab, setCurrentTab] = useState('dashboard');
  const [branches, setBranches] = useState([]);
  const [selectedBranch, setSelectedBranch] = useState('BRANCH_01');
  const [selectedCity, setSelectedCity] = useState('ho_chi_minh');
  
  // Data States
  const [summaryData, setSummaryData] = useState(null);
  const [forecastData, setForecastData] = useState(null);
  const [purchaseData, setPurchaseData] = useState(null);
  const [inventoryData, setInventoryData] = useState(null);
  const [dishesData, setDishesData] = useState([]);
  const [recipesData, setRecipesData] = useState([]);
  const [ingredientsData, setIngredientsData] = useState([]);
  const [preordersData, setPreordersData] = useState([]);

  // Modals States
  const [isBranchModalOpen, setIsBranchModalOpen] = useState(false);
  const [isSalesUploadModalOpen, setIsSalesUploadModalOpen] = useState(false);
  const [isPurchaseUploadModalOpen, setIsPurchaseUploadModalOpen] = useState(false);
  const [isIngredientModalOpen, setIsIngredientModalOpen] = useState(false);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isRetraining, setIsRetraining] = useState(false);
  const [lastRetrainInfo, setLastRetrainInfo] = useState(null);

  // Load Branches initially
  const fetchBranches = async () => {
    try {
      const res = await getBranches();
      setBranches(res.data || []);
      if (res.data?.length > 0 && !res.data.find(b => b.id === selectedBranch)) {
        setSelectedBranch(res.data[0].id);
      }
    } catch (e) {
      console.error('Error fetching branches:', e);
    }
  };

  useEffect(() => {
    fetchBranches();
  }, []);

  // P0-3: Trạng thái loading riêng cho nhóm nặng (skeleton thay vì block toàn bộ UI)
  const [heavyLoading, setHeavyLoading] = useState({ summary: true, forecast: true, purchase: true });

  // Load all branch data — P0-3: Tách nhóm NHẸ (chặn UI) và NẶNG (tự cập nhật khi xong)
  const fetchAllBranchData = (branchId, city = selectedCity) => {
    setError(null);
    setLoading(true);  // Chỉ chờ nhóm NHẸ

    // === NHÓM NHẸ: inventory, dishes, recipes, ingredients, preorders ===
    Promise.allSettled([
      getInventory(branchId),
      getDishes(null, branchId),
      getRecipes(),
      getIngredients(),
      getPreorders(branchId),
    ]).then(([inv, dishes, recipes, ings, po]) => {
      setInventoryData(inv.status === 'fulfilled' ? inv.value.data : null);
      setDishesData(dishes.status === 'fulfilled' ? dishes.value.data : []);
      setRecipesData(recipes.status === 'fulfilled' ? recipes.value.data : []);
      setIngredientsData(ings.status === 'fulfilled' ? ings.value.data : []);
      setPreordersData(po.status === 'fulfilled' ? po.value.data : []);
    }).catch(err => {
      console.error('Error fetching light data:', err);
      setError('Lỗi tải dữ liệu: ' + (err.message || 'Không xác định'));
    }).finally(() => setLoading(false));

    // === NHÓM NẶNG: mỗi cái tự cập nhật khi xong, KHÔNG chặn UI ===
    setHeavyLoading({ summary: true, forecast: true, purchase: true });

    getDashboardSummary(branchId)
      .then(r => setSummaryData(r.data))
      .catch(() => setSummaryData(null))
      .finally(() => setHeavyLoading(p => ({ ...p, summary: false })));

    getForecast(branchId, 7, city)
      .then(r => setForecastData(r.data))
      .catch(() => setForecastData(null))
      .finally(() => setHeavyLoading(p => ({ ...p, forecast: false })));

    getPurchaseRecommendations(branchId)
      .then(r => setPurchaseData(r.data))
      .catch(() => setPurchaseData(null))
      .finally(() => setHeavyLoading(p => ({ ...p, purchase: false })));
  };

  useEffect(() => {
    if (selectedBranch) {
      fetchAllBranchData(selectedBranch, selectedCity);
    }
  }, [selectedBranch, selectedCity]);

  // Handle Retrain AI
  const handleRetrain = async () => {
    try {
      setIsRetraining(true);
      const res = await retrainModel();
      setLastRetrainInfo(res.data);
      await fetchAllBranchData(selectedBranch);
    } catch (e) {
      alert('Lỗi huấn luyện mô hình: ' + e.message);
    } finally {
      setIsRetraining(false);
    }
  };

  // Handle Demo & Clean Toggle
  const handleResetDemo = async () => {
    try {
      setLoading(true);
      await resetDemoData();
      await fetchBranches();
      await fetchAllBranchData(selectedBranch);
    } catch (e) {
      alert('Lỗi nạp demo: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleClearClean = async () => {
    try {
      setLoading(true);
      await clearCleanData();
      await fetchBranches();
      await fetchAllBranchData(selectedBranch);
    } catch (e) {
      alert('Lỗi xóa dữ liệu: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  const activeBranchMeta = branches.find(b => b.id === selectedBranch) || branches[0];

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col font-sans">
      
      {/* Top Navbar */}
      <Navbar
        branches={branches}
        selectedBranch={selectedBranch}
        onSelectBranch={setSelectedBranch}
        onOpenBranchModal={() => setIsBranchModalOpen(true)}
        onOpenUploadModal={() => setIsSalesUploadModalOpen(true)}
        onResetDemo={handleResetDemo}
        onClearClean={handleClearClean}
        onRetrain={handleRetrain}
        isRetraining={isRetraining}
        lastRetrainInfo={lastRetrainInfo}
      />

      {/* Main Body */}
      <div className="flex-1 flex max-w-7xl w-full mx-auto">
        
        {/* Left Sidebar */}
        <Sidebar
          currentTab={currentTab}
          onSelectTab={setCurrentTab}
          branchMeta={activeBranchMeta}
        />

        {/* Content Area */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 min-w-0">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-96 space-y-3">
              <div className="animate-spin rounded-full h-10 w-10 border-4 border-emerald-600 border-t-transparent"></div>
              <p className="text-sm font-medium text-slate-500">Đang tải dữ liệu FoodFlow AI...</p>
            </div>
          ) : error ? (
            /* ERROR FALLBACK UI — FIX: Thay vì infinite spinner, hiển thị lỗi + nút retry */
            <div className="flex flex-col items-center justify-center h-96 space-y-4">
              <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center">
                <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-slate-700">Không thể tải dữ liệu</h3>
              <p className="text-sm text-slate-500 text-center max-w-md">{error}</p>
              <button
                onClick={() => fetchAllBranchData(selectedBranch, selectedCity)}
                className="px-5 py-2.5 bg-emerald-600 text-white font-medium rounded-lg hover:bg-emerald-700 transition-colors shadow-sm"
              >
                🔄 Thử lại
              </button>
            </div>
          ) : (
            <>
              {currentTab === 'dashboard' && (
                <DashboardPage
                  summary={summaryData}
                  onNavigateTab={setCurrentTab}
                  heavyLoading={heavyLoading.summary}
                />
              )}

              {currentTab === 'forecast' && (
                <ForecastPage
                  forecastData={forecastData}
                  branchId={selectedBranch}
                  selectedCity={selectedCity}
                  onCityChange={setSelectedCity}
                  heavyLoading={heavyLoading.forecast}
                />
              )}

              {currentTab === 'purchase' && (
                <PurchasePage
                  purchaseData={purchaseData}
                  branchId={selectedBranch}
                  onRefresh={() => fetchAllBranchData(selectedBranch)}
                  onOpenPurchaseUploadModal={() => setIsPurchaseUploadModalOpen(true)}
                  heavyLoading={heavyLoading.purchase}
                />
              )}

              {currentTab === 'inventory' && (
                <InventoryPage
                  inventoryData={inventoryData}
                  branchId={selectedBranch}
                  onRefresh={() => fetchAllBranchData(selectedBranch)}
                  onOpenIngredientModal={() => setIsIngredientModalOpen(true)}
                />
              )}

              {currentTab === 'recipes' && (
                <RecipesPage
                  dishes={dishesData}
                  recipes={recipesData}
                  ingredients={ingredientsData}
                  branchId={selectedBranch}
                  branchName={activeBranchMeta?.name}
                  onRefresh={() => fetchAllBranchData(selectedBranch)}
                />
              )}

              {currentTab === 'preorders' && (
                <PreordersPage
                  preorders={preordersData}
                  dishes={dishesData}
                  branchId={selectedBranch}
                  onRefresh={() => fetchAllBranchData(selectedBranch)}
                />
              )}
            </>
          )}
        </main>
      </div>

      {/* Modals */}
      <BranchModal
        isOpen={isBranchModalOpen}
        onClose={() => setIsBranchModalOpen(false)}
        branches={branches}
        currentBranchId={selectedBranch}
        onSelectBranch={setSelectedBranch}
        onUpdated={async () => {
          await fetchBranches();
          await fetchAllBranchData(selectedBranch);
        }}
      />

      <UploadSalesModal
        isOpen={isSalesUploadModalOpen}
        onClose={() => setIsSalesUploadModalOpen(false)}
        onUploaded={async () => {
          await fetchAllBranchData(selectedBranch);
        }}
      />

      <UploadPurchaseModal
        isOpen={isPurchaseUploadModalOpen}
        onClose={() => setIsPurchaseUploadModalOpen(false)}
        branchId={selectedBranch}
        onUploaded={async () => {
          await fetchAllBranchData(selectedBranch);
        }}
      />

      <IngredientModal
        isOpen={isIngredientModalOpen}
        onClose={() => setIsIngredientModalOpen(false)}
        branchId={selectedBranch}
        onAdded={async () => {
          await fetchAllBranchData(selectedBranch);
        }}
      />

    </div>
  );
}
