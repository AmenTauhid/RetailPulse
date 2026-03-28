import type {
  AnomalyListResponse,
  Category,
  ForecastResponse,
  HistoricalResponse,
  ModelInfo,
  Store,
  TopMoversResponse,
  WeatherImpactPoint,
  WeatherResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  }
  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export const api = {
  getStores: () => fetchAPI<Store[]>("/api/v1/stores"),

  getCategories: () => fetchAPI<Category[]>("/api/v1/categories"),

  getHistorical: (storeId: number, categoryId: number, startDate?: string, endDate?: string) => {
    const params: Record<string, string> = {};
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    return fetchAPI<HistoricalResponse>(`/api/v1/historical/${storeId}/${categoryId}`, params);
  },

  getForecast: (storeId: number, categoryId: number, days = 14) =>
    fetchAPI<ForecastResponse>(`/api/v1/forecasts/${storeId}/${categoryId}`, {
      days: days.toString(),
    }),

  getAnomalies: (params?: { store_id?: number; category_id?: number; severity?: string; days?: number; limit?: number }) => {
    const p: Record<string, string> = {};
    if (params?.store_id) p.store_id = params.store_id.toString();
    if (params?.category_id) p.category_id = params.category_id.toString();
    if (params?.severity) p.severity = params.severity;
    if (params?.days) p.days = params.days.toString();
    if (params?.limit) p.limit = params.limit.toString();
    return fetchAPI<AnomalyListResponse>("/api/v1/anomalies", p);
  },

  getTopMovers: (days = 14, limit = 10) =>
    fetchAPI<TopMoversResponse>("/api/v1/insights/top-movers", {
      days: days.toString(),
      limit: limit.toString(),
    }),

  getWeatherImpact: (storeId = 1) =>
    fetchAPI<{ data: WeatherImpactPoint[] }>("/api/v1/insights/weather-impact", {
      store_id: storeId.toString(),
    }),

  getWeather: (storeId: number, limit = 30) =>
    fetchAPI<WeatherResponse[]>(`/api/v1/weather/${storeId}`, { limit: limit.toString() }),

  getModelInfo: () => fetchAPI<ModelInfo>("/api/v1/model/info"),

  getHealth: () => fetchAPI<{ status: string; model_loaded: boolean }>("/api/v1/health"),
};
