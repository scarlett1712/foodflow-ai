import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 90000,
});

export const getBranches = () => api.get('/branches');
export const createBranch = (payload) => api.post('/branches', payload);
export const deleteBranch = (id) => api.delete(`/branches/${id}`);

export const getDashboardSummary = (branchId = 'BRANCH_01') => api.get(`/dashboard/summary?branch_id=${branchId}`);
export const getWeatherLocations = () => api.get('/weather/locations');
export const getForecast = (branchId = 'BRANCH_01', nDays = 7, city = 'ho_chi_minh') => 
  api.get(`/forecast?branch_id=${branchId}&n_days=${nDays}&city=${city}`);
export const getStoreInsights = (branchId = 'BRANCH_01', city = 'ho_chi_minh') =>
  api.get(`/insights?branch_id=${branchId}&city=${city}`);

export const getPurchaseRecommendations = (branchId = 'BRANCH_01', targetDate = null) => {
  const url = targetDate 
    ? `/purchase-recommendations?branch_id=${branchId}&target_date=${targetDate}`
    : `/purchase-recommendations?branch_id=${branchId}`;
  return api.get(url);
};

export const getPurchaseHistory = (branchId = 'BRANCH_01', limit = 100) => api.get(`/purchases/history?branch_id=${branchId}&limit=${limit}`);
export const recordManualPurchase = (payload) => api.post('/purchases/record-manual', payload);
export const analyzePurchaseVariance = (payload) => api.post('/purchases/analyze-variance', payload);

export const getInventory = (branchId = 'BRANCH_01') => api.get(`/inventory?branch_id=${branchId}`);
export const updateInventory = (payload) => api.post('/inventory/update', payload);

export const getIngredients = () => api.get('/ingredients');
export const smartTagIngredients = (names) => api.post('/ingredients/smart-tag', { names });
export const createIngredient = (payload, branchId = 'BRANCH_01') => api.post(`/ingredients?branch_id=${branchId}`, payload);
export const deleteIngredient = (id) => api.delete(`/ingredients/${id}`);

export const getDishes = (category = null) => api.get(category ? `/dishes?category=${category}` : '/dishes');
export const createDish = (payload) => api.post('/dishes', payload);
export const createDishWithRecipe = (payload) => api.post('/dishes/with-recipe', payload);
export const deleteDish = (dishId) => api.delete(`/dishes/${dishId}`);

export const getRecipes = (dishId = null) => api.get(dishId ? `/recipes?dish_id=${dishId}` : '/recipes');
export const saveRecipeItem = (payload) => api.post('/recipes', payload);
export const smartAddRecipeItem = (payload) => api.post('/recipes/smart-add', payload);
export const deleteRecipeItem = (dishId, ingredientId) => api.delete(`/recipes/${dishId}/${ingredientId}`);

export const getPreorders = (branchId = 'BRANCH_01') => api.get(`/preorders?branch_id=${branchId}`);
export const createPreorderMulti = (payload) => api.post('/preorders', payload);
export const deletePreorder = (id) => api.delete(`/preorders/${id}`);

// Solana Devnet Audit & Notarization
export const getSolanaStatus = () => api.get('/solana/status');
export const verifySolanaProof = (payload) => api.post('/solana/verify', payload);
export const notarizeBatchOnchain = (batchId) => api.post(`/solana/notarize-batch/${batchId}`);
export const notarizePurchaseOrder = (payload) => api.post('/solana/notarize-po', payload);

export const retrainModel = () => api.post('/model/retrain');
export const resetDemoData = () => api.post('/data/reset-demo');
export const clearCleanData = () => api.post('/data/clear-clean');

export default api;
