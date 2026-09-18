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

  // Load all branch data whenever selectedBranch changes
  const fetchAllBranchData = async (branchId) => {
    try {
      setLoading(true);
      const [sumRes, fcRes, purRes, invRes, dishRes, recRes, ingRes, preRes] = await Promise.all([
        getDashboardSummary(branchId),
        getForecast(branchId, 7),
        getPurchaseRecommendations(branchId),
        getInventory(branchId),
        getDishes(),
        getRecipes(),
        getIngredients(),
        getPreorders(branchId),
      ]);

      setSummaryData(sumRes.data);
      setForecastData(fcRes.data);
      setPurchaseData(purRes.data);
      setInventoryData(invRes.data);
      setDishesData(dishRes.data);
      setRecipesData(recRes.data);
      setIngredientsData(ingRes.data);
      setPreordersData(preRes.data);
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedBranch) {
      fetchAllBranchData(selectedBranch);
    }
  }, [selectedBranch]);

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
        <main className="flex-1 p-6 lg:p-8 overflow-y-auto">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-96 space-y-3">
              <div className="animate-spin rounded-full h-10 w-10 border-4 border-emerald-600 border-t-transparent"></div>
              <p className="text-sm font-medium text-slate-500">Đang tải dữ liệu FoodFlow AI...</p>
            </div>
          ) : (
            <>
              {currentTab === 'dashboard' && (
                <DashboardPage
                  summary={summaryData}
                  onNavigateTab={setCurrentTab}
                />
              )}

              {currentTab === 'forecast' && (
                <ForecastPage
                  forecastData={forecastData}
                  branchId={selectedBranch}
                />
              )}

              {currentTab === 'purchase' && (
                <PurchasePage
                  purchaseData={purchaseData}
                  branchId={selectedBranch}
                  onRefresh={() => fetchAllBranchData(selectedBranch)}
                  onOpenPurchaseUploadModal={() => setIsPurchaseUploadModalOpen(true)}
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
