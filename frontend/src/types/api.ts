// TypeScript mirrors of the backend Pydantic schemas (backend/app/schemas).
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH'
export type ReviewStatus = 'PENDING_REVIEW' | 'UNDER_INVESTIGATION' | 'REVIEWED' | 'ESCALATED'
export type OrderStatus = 'PLACED' | 'SHIPPED' | 'DELIVERED' | 'CANCELLED'
export type ReturnStatus = 'REQUESTED' | 'APPROVED' | 'REJECTED' | 'REFUNDED'

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface HealthResponse {
  status: 'ok' | 'degraded'
  version: string
  environment: string
  database: 'ok' | 'unavailable'
  database_error: string | null
}

export interface CustomerListItem {
  customer_id: string
  name: string
  total_orders: number
  total_returns: number
  return_percentage: number
  risk_score: number | null
  risk_level: RiskLevel | null
  last_return_date: string | null
  review_status: ReviewStatus | null
}

export interface RiskFactor {
  rule_id: string
  factor: string
  group: string
  contribution: number
  raw_points: number
  description: string
}

export interface Assessment {
  customer_id: string
  risk_score: number
  risk_level: RiskLevel
  risk_factors: RiskFactor[]
  requires_manual_review: boolean
  scoring_method: 'RULE_BASED' | 'ML'
  config_version: string
  notes: string[]
  features: Record<string, number | string | null | string[]>
  assessed_at: string
}

export interface CustomerDetail {
  customer_id: string
  name: string
  email: string
  created_at: string
  total_orders: number
  total_returns: number
  return_percentage: number
  total_order_value: string
  total_refunded: string
  mismatch_count: number
  last_return_date: string | null
  review_status: ReviewStatus | null
  latest_assessment: Assessment | null
  categories: { category: string; orders: number; returns: number }[]
}

export interface OrderItem {
  order_id: string
  product_id: string
  product_name: string
  category: string
  order_date: string
  delivery_date: string | null
  order_amount: string
  order_status: OrderStatus
  customer_rating: number | null
  returned: boolean
}

export interface ReturnItem {
  return_id: string
  order_id: string
  product_name: string
  category: string
  order_date: string
  delivery_date: string | null
  return_date: string
  days_to_return: number
  reason_code: string
  reason_text: string | null
  is_vague: boolean
  mismatch_flag: boolean
  refund_amount: string
  return_status: ReturnStatus
}

export interface HistoryPoint {
  risk_score: number
  risk_level: RiskLevel
  config_version: string
  assessed_at: string
}

export interface HighRiskItem {
  customer_id: string
  name: string
  risk_score: number
  risk_level: RiskLevel
  top_factors: RiskFactor[]
  review_status: ReviewStatus | null
  review_updated_at: string | null
  assessed_at: string
}

export interface ReviewRecord {
  id: number
  customer_id: string
  previous_status: ReviewStatus | null
  review_status: ReviewStatus
  review_notes: string | null
  updated_by: string
  updated_at: string
}

export interface AnalyticsSummary {
  total_customers: number
  total_orders: number
  total_returns: number
  average_return_ratio: number
  high_risk_customers: number
  medium_risk_customers: number
  low_risk_customers: number
  total_refunded: number
  date_from: string | null
  date_to: string | null
}

export interface CategoryReturns {
  category: string
  orders: number
  returns: number
  return_rate: number
  mismatches: number
}

export interface LevelCount {
  risk_level: RiskLevel
  count: number
  percentage: number
}

export interface TrendPoint {
  period_start: string
  returns: number
  orders: number
  mismatches: number
}

export interface RatioBucket {
  bucket: string
  lower: number
  upper: number
  customers: number
}

export interface ReasonCount {
  reason_code: string
  count: number
  vague: number
}

export interface MlPrediction {
  customer_id: string | null
  model: string
  probability_suspicious_pattern: number
  predicted_label: string
  threshold: number
  rule_based_score: number | null
  rule_based_level: string | null
  disclaimer: string
}

export interface ModelMetrics {
  model: string
  threshold?: number
  accuracy: number
  precision: number
  recall: number
  f1: number
  roc_auc?: number
  cv_f1_mean?: number
  cv_f1_std?: number
  confusion_matrix: { true_negative: number; false_positive: number; false_negative: number; true_positive: number }
}

export interface MlMetrics {
  trained_at: string
  data_source: string
  dataset: { customers: number; train: number; test: number; positive_rate: number; test_positives: number }
  features: string[]
  selected_model: string
  selection_rule: string
  models: Record<string, ModelMetrics>
  rule_based_baseline: ModelMetrics
  logistic_regression_coefficients: [string, number][]
  decision_tree_importances: [string, number][]
}

interface RuleBase {
  enabled: boolean
  points: number
  [param: string]: number | boolean
}

export interface ScoringConfig {
  version: string
  levels: { low_max: number; medium_max: number }
  vague_reason_codes: string[]
  vague_text_min_length: number
  high_return_category_margin: number
  group_caps: Record<string, number>
  rules: Record<string, RuleBase>
}

export interface RulesResponse {
  config: ScoringConfig
  source: string
  email_alerts_enabled: boolean
}

export interface DateRange {
  date_from?: string
  date_to?: string
}
