"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Store, Category, ForecastResponse, HistoricalResponse } from "@/lib/types";
import StoreSelector from "@/components/StoreSelector";
import CategorySelector from "@/components/CategorySelector";
import DemandChart from "@/components/DemandChart";

export default function ForecastsPage() {
  const [stores, setStores] = useState<Store[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [storeId, setStoreId] = useState(1);
  const [categoryId, setCategoryId] = useState(1);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [historical, setHistorical] = useState<HistoricalResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(14);

  useEffect(() => {
    async function loadSelectors() {
      const [s, c] = await Promise.all([api.getStores(), api.getCategories()]);
      setStores(s);
      setCategories(c);
    }
    loadSelectors();
  }, []);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const [f, h] = await Promise.all([
          api.getForecast(storeId, categoryId, days),
          api.getHistorical(storeId, categoryId, "2025-10-01", "2025-12-31"),
        ]);
        setForecast(f);
        setHistorical(h);
      } catch (e) {
        console.error("Failed to load forecast:", e);
      } finally {
        setLoading(false);
      }
    }
    if (stores.length > 0) loadData();
  }, [storeId, categoryId, days, stores.length]);

  const chartData = [
    ...(historical?.data.map((d) => ({
      date: d.date,
      actual: d.total_quantity,
    })) || []),
    ...(forecast?.forecasts.map((f) => ({
      date: f.date,
      predicted: f.predicted_quantity,
      lower: f.lower_bound ?? undefined,
      upper: f.upper_bound ?? undefined,
    })) || []),
  ];

  const selectedCategory = categories.find((c) => c.id === categoryId);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Demand Forecasts</h1>
        <p className="mt-1 text-sm text-gray-500">Historical demand and predicted future demand</p>
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-4">
        {stores.length > 0 && (
          <StoreSelector stores={stores} selectedId={storeId} onChange={setStoreId} />
        )}
        {categories.length > 0 && (
          <CategorySelector categories={categories} selectedId={categoryId} onChange={setCategoryId} />
        )}
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm"
        >
          <option value={7}>7-day forecast</option>
          <option value={14}>14-day forecast</option>
          <option value={30}>30-day forecast</option>
        </select>
      </div>

      {loading ? (
        <div className="flex h-96 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
        </div>
      ) : (
        <>
          <DemandChart
            data={chartData}
            title={`${selectedCategory?.name || "Category"} Demand`}
            showConfidence
          />

          {forecast?.model_metrics && (
            <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div className="rounded-lg border border-gray-200 bg-white p-4 text-center">
                <p className="text-sm text-gray-500">RMSE</p>
                <p className="text-xl font-bold">{forecast.model_metrics.rmse.toFixed(3)}</p>
              </div>
              <div className="rounded-lg border border-gray-200 bg-white p-4 text-center">
                <p className="text-sm text-gray-500">MAE</p>
                <p className="text-xl font-bold">{forecast.model_metrics.mae.toFixed(3)}</p>
              </div>
              <div className="rounded-lg border border-gray-200 bg-white p-4 text-center">
                <p className="text-sm text-gray-500">R-squared</p>
                <p className="text-xl font-bold">{(forecast.model_metrics.r2 * 100).toFixed(1)}%</p>
              </div>
              <div className="rounded-lg border border-gray-200 bg-white p-4 text-center">
                <p className="text-sm text-gray-500">MAPE</p>
                <p className="text-xl font-bold">{forecast.model_metrics.mape.toFixed(1)}%</p>
              </div>
            </div>
          )}

          {forecast?.feature_importance && (
            <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <h3 className="mb-3 text-sm font-semibold text-gray-700">Top Prediction Drivers</h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(forecast.feature_importance).map(([name, value]) => (
                  <span
                    key={name}
                    className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700"
                  >
                    {name.replace(/_/g, " ")}: {(value * 100).toFixed(1)}%
                  </span>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
