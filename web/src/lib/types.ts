export interface Store {
  id: number;
  store_code: string;
  name: string;
  city: string;
  province: string;
  latitude: number;
  longitude: number;
  store_type: string;
  opened_date: string;
}

export interface Category {
  id: number;
  name: string;
  department: string;
  is_seasonal: boolean;
  peak_season: string | null;
}

export interface DailyDemandPoint {
  date: string;
  total_quantity: number;
  total_revenue: number;
  transaction_count: number;
}

export interface HistoricalResponse {
  store_id: number;
  category_id: number;
  data: DailyDemandPoint[];
  start_date: string;
  end_date: string;
}

export interface ForecastPoint {
  date: string;
  predicted_quantity: number;
  lower_bound: number | null;
  upper_bound: number | null;
}

export interface ForecastResponse {
  store_id: number;
  category_id: number;
  forecasts: ForecastPoint[];
  model_type: string;
  model_metrics: Record<string, number> | null;
  feature_importance: Record<string, number> | null;
}

export interface Anomaly {
  store_id: number;
  category_id: number;
  date: string;
  actual_quantity: number;
  predicted_quantity: number;
  residual: number;
  severity: "low" | "medium" | "high";
  z_score: number;
  store_name: string | null;
  category_name: string | null;
}

export interface AnomalyListResponse {
  anomalies: Anomaly[];
  total: number;
}

export interface TopMover {
  category_id: number;
  category_name: string;
  store_id: number;
  store_name: string;
  current_avg_qty: number;
  previous_avg_qty: number;
  pct_change: number;
  direction: "up" | "down";
}

export interface TopMoversResponse {
  period_days: number;
  movers: TopMover[];
}

export interface WeatherImpactPoint {
  category_name: string;
  temp_range: string;
  avg_quantity: number;
  sample_count: number;
}

export interface WeatherResponse {
  store_id: number;
  date: string;
  temp_high_c: number | null;
  temp_low_c: number | null;
  temp_mean_c: number | null;
  precipitation_mm: number | null;
  snowfall_cm: number | null;
  weather_description: string | null;
}

export interface ModelInfo {
  model_type: string;
  metrics: Record<string, number>;
  feature_importance: Record<string, number>;
  train_date_range: string[];
  test_date_range: string[];
}
