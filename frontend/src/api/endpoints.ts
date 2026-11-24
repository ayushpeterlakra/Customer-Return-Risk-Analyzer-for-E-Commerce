import { API_BASE_URL, apiClient } from './client'
import type {
  AnalyticsSummary,
  Assessment,
  CategoryReturns,
  CustomerDetail,
  CustomerListItem,
  DateRange,
  HealthResponse,
  HighRiskItem,
  HistoryPoint,
  LevelCount,
  MlMetrics,
  MlPrediction,
  OrderItem,
  Page,
  RatioBucket,
  ReasonCount,
  ReturnItem,
  ReviewRecord,
  ReviewStatus,
  RiskLevel,
  RulesResponse,
  ScoringConfig,
  TrendPoint,
} from '../types/api'

const get = async <T>(url: string, params?: object) => (await apiClient.get<T>(url, { params })).data

export interface CustomerQuery {
  page: number
  page_size: number
  search?: string
  risk_level?: RiskLevel
  min_score?: number
  min_return_ratio?: number
  category?: string
  sort: string
  order: 'asc' | 'desc'
}

export const api = {
  health: () => get<HealthResponse>('/api/health'),

  customers: (q: CustomerQuery) => get<Page<CustomerListItem>>('/api/customers', q),
  customer: (id: string) => get<CustomerDetail>(`/api/customers/${encodeURIComponent(id)}`),
  customerOrders: (id: string, page = 1) =>
    get<Page<OrderItem>>(`/api/customers/${encodeURIComponent(id)}/orders`, { page, page_size: 100 }),
  customerReturns: (id: string, page = 1) =>
    get<Page<ReturnItem>>(`/api/customers/${encodeURIComponent(id)}/returns`, { page, page_size: 100 }),

  assess: async (id: string) =>
    (await apiClient.post<Assessment>(`/api/risk/assess/${encodeURIComponent(id)}`)).data,
  assessAll: async () =>
    (await apiClient.post<{ assessed: number; LOW: number; MEDIUM: number; HIGH: number; duration_ms: number }>(
      '/api/risk/assess-all',
    )).data,
  riskHistory: (id: string) => get<HistoryPoint[]>(`/api/risk/${encodeURIComponent(id)}/history`),
  highRisk: (page: number, review_status?: ReviewStatus) =>
    get<Page<HighRiskItem>>('/api/risk/high-risk', { page, page_size: 20, review_status }),

  summary: (r: DateRange) => get<AnalyticsSummary>('/api/analytics/summary', r),
  returnsByCategory: (r: DateRange) => get<CategoryReturns[]>('/api/analytics/returns-by-category', r),
  riskDistribution: () => get<LevelCount[]>('/api/analytics/risk-distribution'),
  returnTrends: (granularity: 'day' | 'week', r: DateRange) =>
    get<TrendPoint[]>('/api/analytics/return-trends', { granularity, ...r }),
  ratioDistribution: () => get<RatioBucket[]>('/api/analytics/return-ratio-distribution'),
  returnReasons: (r: DateRange) => get<ReasonCount[]>('/api/analytics/return-reasons', r),

  reviewTrail: (id: string) => get<ReviewRecord[]>(`/api/reviews/${encodeURIComponent(id)}`),
  updateReview: async (id: string, body: { review_status: ReviewStatus; review_notes?: string; updated_by: string }) =>
    (await apiClient.patch<ReviewRecord>(`/api/reviews/${encodeURIComponent(id)}`, body)).data,

  mlMetrics: () => get<MlMetrics>('/api/ml/metrics'),
  mlPredict: async (customer_id: string, model = 'selected') =>
    (await apiClient.post<MlPrediction>('/api/ml/predict', { customer_id, model })).data,

  rules: () => get<RulesResponse>('/api/settings/scoring-rules'),
  saveRules: async (config: ScoringConfig, updated_by: string) =>
    (await apiClient.put<RulesResponse>('/api/settings/scoring-rules', { config, updated_by, rescore: true })).data,
  resetRules: async () => (await apiClient.post<RulesResponse>('/api/settings/scoring-rules/reset')).data,

  importCsv: async (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return (
      await apiClient.post<{ imported: Record<string, number>; rescored: Record<string, number> }>(
        '/api/data/import',
        form,
        { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 120_000 },
      )
    ).data
  },
  exportUrl: (risk_level?: RiskLevel, min_score?: number) => {
    const params = new URLSearchParams()
    params.set('risk_level', risk_level ?? 'ALL')
    if (min_score !== undefined) params.set('min_score', String(min_score))
    return `${API_BASE_URL}/api/data/export/flagged-customers?${params.toString()}`
  },
  templateUrl: () => `${API_BASE_URL}/api/data/import/template`,
}
