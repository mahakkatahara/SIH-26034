/**
 * Axios API client with JWT auth, request/response interceptors, and token refresh.
 */
import axios, { type AxiosInstance, type AxiosError } from 'axios';
import type {
  AuthTokens,
  User,
  Product,
  ProductListResponse,
  Inspection,
  InspectionDetail,
  InspectionListResponse,
  InspectionImage,
  AnalysisResult,
  Rule,
  RuleListResponse,
  Report,
  DashboardStats,
  TrendDataPoint,
  TopViolation,
} from '@/types';

const BASE_URL = import.meta.env.VITE_API_URL || '';

// ─── Axios instance ────────────────────────────────────────────────────────────
const api: AxiosInstance = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});

// ─── Request interceptor: attach Bearer token ──────────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ─── Response interceptor: handle 401 / token refresh ─────────────────────────
let isRefreshing = false;
let refreshQueue: Array<(token: string) => void> = [];

api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as any;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) {
        clearAuth();
        window.location.href = '/login';
        return Promise.reject(error);
      }
      if (isRefreshing) {
        return new Promise((resolve) => {
          refreshQueue.push((token) => {
            original.headers.Authorization = `Bearer ${token}`;
            resolve(api(original));
          });
        });
      }
      isRefreshing = true;
      try {
        const { data } = await axios.post<AuthTokens>(
          `${BASE_URL}/api/v1/auth/refresh`,
          { refresh_token: refreshToken }
        );
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        refreshQueue.forEach((cb) => cb(data.access_token));
        refreshQueue = [];
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return api(original);
      } catch {
        clearAuth();
        window.location.href = '/login';
        return Promise.reject(error);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);

function clearAuth() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');
}

// ─── Auth API ──────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) =>
    api.post<AuthTokens>('/auth/login', { email, password }).then((r) => r.data),

  refresh: (refresh_token: string) =>
    api.post<AuthTokens>('/auth/refresh', { refresh_token }).then((r) => r.data),

  me: () => api.get<User>('/auth/me').then((r) => r.data),
};

// ─── Dashboard API ─────────────────────────────────────────────────────────────
export const dashboardApi = {
  stats: () => api.get<DashboardStats>('/dashboard/stats').then((r) => r.data),
  recent: (limit = 10) =>
    api.get<Inspection[]>('/dashboard/recent', { params: { limit } }).then((r) => r.data),
  trend: (days = 30) =>
    api.get<TrendDataPoint[]>('/dashboard/trend', { params: { days } }).then((r) => r.data),
  topViolations: (limit = 10) =>
    api.get<TopViolation[]>('/dashboard/violations/top', { params: { limit } }).then((r) => r.data),
};

// ─── Inspections API ───────────────────────────────────────────────────────────
export const inspectionsApi = {
  list: (params?: {
    page?: number;
    size?: number;
    status?: string;
    compliance_status?: string;
    search?: string;
  }) => api.get<InspectionListResponse>('/inspections', { params }).then((r) => r.data),

  create: (data: { product_id?: string; remarks?: string; location?: string }) =>
    api.post<Inspection>('/inspections', data).then((r) => r.data),

  get: (id: string) =>
    api.get<InspectionDetail>(`/inspections/${id}`).then((r) => r.data),

  update: (id: string, data: Partial<Inspection>) =>
    api.put<Inspection>(`/inspections/${id}`, data).then((r) => r.data),

  uploadImages: (id: string, files: File[], label: string) => {
    const formData = new FormData();
    files.forEach((file) => formData.append('images', file));
    formData.append('label', label);
    return api
      .post<InspectionImage[]>(`/inspections/${id}/images`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data);
  },

  analyze: (id: string) =>
    api.post<AnalysisResult>(`/inspections/${id}/analyze`).then((r) => r.data),
};

// ─── Products API ──────────────────────────────────────────────────────────────
export const productsApi = {
  list: (params?: { page?: number; size?: number; search?: string; category?: string }) =>
    api.get<ProductListResponse>('/products', { params }).then((r) => r.data),

  create: (data: Partial<Product>) =>
    api.post<Product>('/products', data).then((r) => r.data),

  get: (id: string) => api.get<Product>(`/products/${id}`).then((r) => r.data),

  update: (id: string, data: Partial<Product>) =>
    api.put<Product>(`/products/${id}`, data).then((r) => r.data),

  delete: (id: string) => api.delete(`/products/${id}`),
};

// ─── Rules API ─────────────────────────────────────────────────────────────────
export const rulesApi = {
  list: (params?: { field?: string; severity?: string; is_active?: boolean }) =>
    api.get<RuleListResponse>('/rules', { params }).then((r) => r.data),

  get: (id: string) => api.get<Rule>(`/rules/${id}`).then((r) => r.data),
};

// ─── Reports API ───────────────────────────────────────────────────────────────
export const reportsApi = {
  list: () => api.get<Report[]>('/reports').then((r) => r.data),

  generate: (inspection_id: string, report_type: 'PDF' | 'DOCX') =>
    api.post<Report>('/reports/generate', { inspection_id, report_type }).then((r) => r.data),
};

export default api;
