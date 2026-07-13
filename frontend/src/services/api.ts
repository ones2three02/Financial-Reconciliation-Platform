import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Auth interceptor
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export interface Store {
  id: number;
  name: string;
  code?: string | null;
  region?: string | null;
  manager?: string | null;
  phone?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface StoreAlias {
  id: number;
  alias_name: string;
  store_id: number | null;
  status: 'mapped' | 'pending';
  created_at: string;
  updated_at: string;
  store?: {
    name: string;
    is_active: boolean;
  };
}

export interface FieldMapping {
  id: number;
  data_source: string;
  target_field: 'trade_date' | 'store_name' | 'amount';
  source_column: string;
  is_active: boolean;
  created_at: string;
}

export interface ImportFile {
  id: number;
  filename: string;
  data_source: string;
  upload_status: 'pending' | 'parsed' | 'failed';
  error_message: string | null;
  row_count: number;
  uploaded_at: string;
}

export interface ReconciliationResult {
  id: number;
  trade_date: string;
  standard_store_name: string;
  tonglian_amount: number;
  meituan_amount: number;
  douyin_amount: number;
  cash_amount: number;
  sales_amount: number;
  expected_amount: number;
  actual_amount: number;
  difference: number;
  status: 'consistent' | 'discrepancy' | 'missing_data';
  remarks: string | null;
  is_resolved: boolean;
  resolved_by: string | null;
  resolved_at: string | null;
}

export interface DashboardSummary {
  total_stores: number;
  consistent_count: number;
  discrepancy_count: number;
  missing_data_count: number;
  total_sales: number;
  total_tonglian: number;
  total_difference: number;
}

export interface TrendData {
  date: string;
  sales_amount: number;
  tonglian_amount: number;
  difference: number;
  total_stores: number;
  discrepancies: number;
}

export const api = {
  // Dashboard
  getDashboardSummary: (tradeDate?: string) =>
    client.get<DashboardSummary>('/dashboard/summary', { params: { trade_date: tradeDate } }).then(res => res.data),
  
  getDashboardTrends: (days = 7) =>
    client.get<TrendData[]>('/dashboard/trends', { params: { days } }).then(res => res.data),

  // Stores
  getStores: () =>
    client.get<Store[]>('/stores/').then(res => res.data),
  
  createStore: (data: { name: string; code?: string; region?: string; manager?: string; phone?: string; is_active?: boolean }) =>
    client.post<Store>('/stores/', data).then(res => res.data),
  
  updateStore: (id: number, data: { name?: string; code?: string; region?: string; manager?: string; phone?: string; is_active?: boolean }) =>
    client.put<Store>(`/stores/${id}`, data).then(res => res.data),
  
  deleteStore: (id: number) =>
    client.delete(`/stores/${id}`).then(res => res.data),

  // Aliases
  getStoreAliases: (status?: string) =>
    client.get<StoreAlias[]>('/stores/aliases/list', { params: { status } }).then(res => res.data),
  
  createStoreAlias: (aliasName: string, storeId: number | null) =>
    client.post<StoreAlias>('/stores/aliases/create', { alias_name: aliasName, store_id: storeId }).then(res => res.data),
  
  updateStoreAlias: (id: number, data: { store_id: number | null }) =>
    client.put<StoreAlias>(`/stores/aliases/${id}`, data).then(res => res.data),

  // Mappings
  getFieldMappings: () =>
    client.get<FieldMapping[]>('/mappings/').then(res => res.data),
  
  getFieldMappingsBySource: (source: string) =>
    client.get<FieldMapping[]>(`/mappings/source/${source}`).then(res => res.data),
  
  createFieldMapping: (data: { data_source: string; target_field: string; source_column: string }) =>
    client.post<FieldMapping>('/mappings/', data).then(res => res.data),
  
  updateFieldMapping: (id: number, data: { is_active?: boolean; source_column?: string }) =>
    client.put<FieldMapping>(`/mappings/${id}`, data).then(res => res.data),
  
  deleteFieldMapping: (id: number) =>
    client.delete(`/mappings/${id}`).then(res => res.data),

  // Files
  getImportFiles: () =>
    client.get<ImportFile[]>('/files/').then(res => res.data),
  
  uploadFile: (file: File, dataSource: string) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('data_source', dataSource);
    return client.post('/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }).then(res => res.data);
  },
  
  reprocessFile: (fileId: number) =>
    client.post(`/files/${fileId}/reprocess`).then(res => res.data),

  confirmMapping: (importFileId: number, mappings: Record<string, string>) =>
    client.post('/files/confirm-mapping', { import_file_id: importFileId, mappings }).then(res => res.data),

  // Reconciliation
  getReconciliationResults: (params: { trade_date?: string; status?: string; is_resolved?: boolean }) =>
    client.get<ReconciliationResult[]>('/reconciliation/', { params }).then(res => res.data),
  
  updateReconciliationResult: (id: number, data: { remarks?: string | null; is_resolved?: boolean; resolved_by?: string }) =>
    client.put<ReconciliationResult>(`/reconciliation/${id}`, data).then(res => res.data),
  
  recalculateDate: (tradeDate: string) =>
    client.post('/reconciliation/recalculate', null, { params: { trade_date: tradeDate } }).then(res => res.data),
  
  getExportUrl: (tradeDate: string) =>
    `${API_BASE_URL}/reconciliation/export?trade_date=${tradeDate}`,

  // Auth login
  login: (username: string, password: string) =>
    client.post<{ access_token: string; token_type: string; username: string }>('/auth/login', { username, password }).then(res => res.data),
};
