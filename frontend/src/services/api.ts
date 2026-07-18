import axios from 'axios';
import { ref } from 'vue';

import { getDesktopBackendConfig } from './desktopConnection';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';
const DESKTOP_TOKEN_HEADER = 'X-FRP-Desktop-Token';
const ACCESS_TOKEN_KEY = 'access_token';
const USERNAME_KEY = 'username';
const ROLE_KEY = 'role';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

client.interceptors.request.use(async (config) => {
  if (!import.meta.env.VITE_API_BASE_URL && typeof window !== 'undefined') {
    const desktopConfig = await getDesktopBackendConfig(window);
    if (desktopConfig) {
      config.baseURL = desktopConfig.api_base_url;
      config.headers.set(DESKTOP_TOKEN_HEADER, desktopConfig.token);
    }
  }
  const token = sessionStorage.getItem(ACCESS_TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !String(error.config?.url).includes('/auth/login')) {
      clearSession();
      if (window.location.pathname !== '/login') window.location.assign('/login');
    }
    return Promise.reject(error);
  },
);

// 全局响应式会话状态，确保角色及 Token 变更时 UI 能自动感知并刷新
export const currentSession = ref({
  token: sessionStorage.getItem(ACCESS_TOKEN_KEY),
  username: sessionStorage.getItem(USERNAME_KEY),
  role: sessionStorage.getItem(ROLE_KEY),
});

export const saveSession = (session: LoginResponse) => {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, session.access_token);
  sessionStorage.setItem(USERNAME_KEY, session.username);
  sessionStorage.setItem(ROLE_KEY, session.role);
  
  // 更新响应式状态触发 UI 重算
  currentSession.value = {
    token: session.access_token,
    username: session.username,
    role: session.role,
  };
};

export const clearSession = () => {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  sessionStorage.removeItem(USERNAME_KEY);
  sessionStorage.removeItem(ROLE_KEY);
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(USERNAME_KEY);
  
  // 清空响应式状态触发 UI 重算
  currentSession.value = {
    token: null,
    username: null,
    role: null,
  };
};

export const getSession = () => currentSession.value;

export interface LoginResponse {
  access_token: string;
  token_type: string;
  username: string;
  role: 'admin' | 'finance' | 'viewer';
}

export interface DesktopSetupStatus {
  setup_required: boolean;
}

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
  source_code: string;
  alias_name: string;
  store_id: number | null;
  status: 'mapped' | 'pending';
  created_at: string;
  updated_at: string;
  confirmed_by?: string | null;
  confirmed_at?: string | null;
  store?: { name: string; is_active: boolean };
}

export interface FieldMapping {
  id: number;
  data_source: string;
  target_field: 'trade_date' | 'store_name' | 'amount' | 'marketing_fee' | 'payment_method';
  source_column: string;
  is_active: boolean;
  created_at: string;
}

export interface ImportFile {
  id: number;
  filename: string;
  data_source: string;
  upload_status: string;
  error_message: string | null;
  row_count: number;
  uploaded_at: string;
  store_id?: number | null;
  profile_code?: string | null;
  profile_version?: number | null;
  supersedes_file_id: number | null;
  is_current: boolean;
}

export interface ReconciliationBatch {
  id: number;
  business_date: string;
  status: 'draft' | 'attention_required' | 'ready_to_close' | 'closed';
  version: number;
  created_by: string;
  created_at: string;
  closed_by?: string | null;
  closed_at?: string | null;
  reopened_by?: string | null;
  reopened_at?: string | null;
  reopen_reason?: string | null;
}

export interface SourceCoverage {
  id: number;
  store_id: number;
  source_code: SourceCode;
  status: 'present_data' | 'present_zero' | 'missing' | 'attention_required';
  evidence_type: string | null;
  amount: number;
  file_count: number;
  valid_row_count: number;
  error_row_count: number;
  updated_at: string;
}

export interface DataQualityIssue {
  id: number;
  import_file_id: number | null;
  issue_type: string;
  source_code: SourceCode;
  raw_value: string | null;
  affected_row_count: number;
  affected_amount: number;
  status: 'open' | 'resolved' | 'superseded';
  created_at: string;
}

export interface ReconciliationResult {
  id: number;
  batch_id?: number | null;
  store_id?: number | null;
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
  status: 'consistent' | 'discrepancy' | 'incomplete' | 'missing_data';
  completeness_status?: string | null;
  remarks: string | null;
  is_resolved: boolean;
  resolved_by: string | null;
  resolved_at: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface BatchDetail {
  batch: ReconciliationBatch;
  import_files: ImportFile[];
  coverages: SourceCoverage[];
  quality_issues: DataQualityIssue[];
  results: ReconciliationResult[];
  can_restore_last_reset: boolean;
  last_reset_event_id: number | null;
}

export interface PreflightResult {
  profile_code: string;
  profile_version: number;
  sheet_name: string;
  business_date: string;
  store_id: number | null;
  output_sources: SourceCode[];
  total_data_rows: number;
  matching_row_count: number;
  date_range_start: string | null;
  date_range_end: string | null;
  detected_store_names: string[];
}

export interface ImportOutcome {
  status: 'imported' | 'duplicate' | 'attention_required';
  import_file_id: number;
  extraction_run_id: number | null;
}

export interface ImportVersionAction {
  status: 'invalidated' | 'reset';
  batch_id: number;
  file_id: number | null;
}

export type SourceCode = 'tonglian' | 'meituan' | 'douyin' | 'cash' | 'sales';
export type ProfileCode = 'store_finance_v1' | 'tonglian_v1' | 'meituan_v1' | 'douyin_v1';

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

const workbookForm = (file: File, fields: Record<string, string | number | null | undefined>) => {
  const form = new FormData();
  form.append('file', file);
  Object.entries(fields).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') form.append(key, String(value));
  });
  return form;
};

export const api = {
  getDesktopSetupStatus: () =>
    client.get<DesktopSetupStatus>('/auth/desktop-setup').then((res) => res.data),
  setupDesktopAdmin: (username: string, password: string) =>
    client.post<{ username: string; role: string }>('/auth/desktop-setup', {
      username,
      password,
    }).then((res) => res.data),
  login: (username: string, password: string) =>
    client.post<LoginResponse>('/auth/login', { username, password }).then((res) => res.data),
  logout: () => client.post('/auth/logout'),
  getMe: () => client.get<{ username: string; role: string }>('/auth/me').then((res) => res.data),

  getBatches: () => client.get<ReconciliationBatch[]>('/batches/').then((res) => res.data),
  createBatch: (businessDate: string) =>
    client.post<ReconciliationBatch>('/batches/', { business_date: businessDate }).then((res) => res.data),
  getBatchDetail: (batchId: number) =>
    client.get<BatchDetail>(`/batches/${batchId}/detail`).then((res) => res.data),
  confirmZero: (batchId: number, storeId: number, sourceCode: SourceCode) =>
    client.post(`/batches/${batchId}/confirm-zero`, { store_id: storeId, source_code: sourceCode }).then((res) => res.data),
  revokeZero: (batchId: number, storeId: number, sourceCode: SourceCode, reason: string) =>
    client.post(`/batches/${batchId}/revoke-zero`, {
      store_id: storeId,
      source_code: sourceCode,
      reason,
    }).then((res) => res.data),
  reconcileBatch: (batchId: number) =>
    client.post<ReconciliationResult[]>(`/batches/${batchId}/reconcile`).then((res) => res.data),
  closeBatch: (batchId: number) =>
    client.post<ReconciliationBatch>(`/batches/${batchId}/close`).then((res) => res.data),
  reopenBatch: (batchId: number, reason: string) =>
    client.post<ReconciliationBatch>(`/batches/${batchId}/reopen`, { reason }).then((res) => res.data),
  resetBatchCurrentData: (batchId: number, reason: string, confirmationDate: string, riskAcknowledged: boolean) =>
    client.post<ReconciliationBatch>(`/batches/${batchId}/reset-current-data`, {
      reason,
      confirmation_date: confirmationDate,
      risk_acknowledged: riskAcknowledged,
    }).then((res) => res.data),
  restoreLastReset: (batchId: number, reason: string, confirmationDate: string, riskAcknowledged: boolean) =>
    client.post<ReconciliationBatch>(`/batches/${batchId}/restore-last-reset`, {
      reason,
      confirmation_date: confirmationDate,
      risk_acknowledged: riskAcknowledged,
    }).then((res) => res.data),

  preflightWorkbook: (file: File, profileCode: ProfileCode, businessDate: string, storeId?: number | null, password?: string | null) =>
    client.post<PreflightResult>('/files/preflight', workbookForm(file, {
      profile_code: profileCode,
      business_date: businessDate,
      store_id: storeId,
      password: password,
    }), { headers: { 'Content-Type': 'multipart/form-data' } }).then((res) => res.data),
  importWorkbook: (file: File, batchId: number, profileCode: ProfileCode, storeId?: number | null, password?: string | null) =>
    client.post<ImportOutcome>('/files/import', workbookForm(file, {
      batch_id: batchId,
      profile_code: profileCode,
      store_id: storeId,
      password: password,
    }), { headers: { 'Content-Type': 'multipart/form-data' } }).then((res) => res.data),
  replaceImportFile: (fileId: number, file: File, reason: string, password?: string | null) =>
    client.post<ImportOutcome>(`/files/${fileId}/replace`, workbookForm(file, { reason, password }), {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((res) => res.data),
  invalidateImportFile: (fileId: number, reason: string) =>
    client.post<ImportVersionAction>(`/files/${fileId}/invalidate`, { reason }).then((res) => res.data),
  restoreImportFile: (fileId: number, reason: string) =>
    client.post<ImportOutcome>(`/files/${fileId}/restore`, { reason }).then((res) => res.data),

  getStores: () => client.get<Store[]>('/stores/').then((res) => res.data),
  createStore: (data: { name: string; code?: string; region?: string; manager?: string; phone?: string; is_active?: boolean }) =>
    client.post<Store>('/stores/', data).then((res) => res.data),
  updateStore: (id: number, data: Partial<Store> & { status_change_reason?: string }) => client.put<Store>(`/stores/${id}`, data).then((res) => res.data),
  deleteStore: (id: number) => client.delete(`/stores/${id}`).then((res) => res.data),

  getStoreAliases: (status?: string) =>
    client.get<StoreAlias[]>('/stores/aliases/list', { params: { status } }).then((res) => res.data),
  createStoreAlias: (aliasName: string, storeId: number | null, sourceCode = 'legacy') =>
    client.post<StoreAlias>('/stores/aliases/create', {
      alias_name: aliasName,
      store_id: storeId,
      source_code: sourceCode,
    }).then((res) => res.data),
  confirmStoreAlias: (id: number, storeId: number, reason?: string) =>
    client.post<StoreAlias>(`/stores/aliases/${id}/confirm`, { store_id: storeId, reason }).then((res) => res.data),
  updateStoreAlias: (id: number, data: { store_id: number; reason?: string }) =>
    client.put<StoreAlias>(`/stores/aliases/${id}`, data).then((res) => res.data),

  getFieldMappings: () => client.get<FieldMapping[]>('/mappings/').then((res) => res.data),
  getFieldMappingsBySource: (source: string) =>
    client.get<FieldMapping[]>(`/mappings/source/${source}`).then((res) => res.data),
  createFieldMapping: (data: { data_source: string; target_field: string; source_column: string }) =>
    client.post<FieldMapping>('/mappings/', data).then((res) => res.data),
  updateFieldMapping: (id: number, data: { is_active?: boolean; source_column?: string; status_change_reason?: string }) =>
    client.put<FieldMapping>(`/mappings/${id}`, data).then((res) => res.data),
  deleteFieldMapping: (id: number) => client.delete(`/mappings/${id}`).then((res) => res.data),

  getImportFiles: () => client.get<ImportFile[]>('/files/').then((res) => res.data),
  getDashboardSummary: (tradeDate?: string) =>
    client.get<DashboardSummary>('/dashboard/summary', { params: { trade_date: tradeDate } }).then((res) => res.data),
  getDashboardTrends: (params?: { days?: number; start_date?: string; end_date?: string }) =>
    client.get<TrendData[]>('/dashboard/trends', { params }).then((res) => res.data),
  getReconciliationResults: (params: { trade_date?: string; status?: string; is_resolved?: boolean }) =>
    client.get<ReconciliationResult[]>('/reconciliation/', { params }).then((res) => res.data),
  updateReconciliationResult: (id: number, data: { remarks?: string | null; is_resolved?: boolean }) =>
    client.put<ReconciliationResult>(`/reconciliation/${id}`, data).then((res) => res.data),
  recalculateDate: (tradeDate: string) =>
    client.post('/reconciliation/recalculate', null, { params: { trade_date: tradeDate } }).then((res) => res.data),
  downloadReconciliation: async (tradeDate: string) => {
    const response = await client.get<Blob>('/reconciliation/export', {
      params: { trade_date: tradeDate },
      responseType: 'blob',
    });
    return response.data;
  },
};
