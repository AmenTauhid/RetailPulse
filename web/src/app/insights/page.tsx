"use client";

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ScatterChart,
  Scatter,
  ZAxis,
} from "recharts";
import { api } from "@/lib/api";
import type { Store, TopMover, WeatherImpactPoint } from "@/lib/types";
import StoreSelector from "@/components/StoreSelector";

export default function InsightsPage() {
  const [stores, setStores] = useState<Store[]>([]);
  const [storeId, setStoreId] = useState(1);
  const [topMovers, setTopMovers] = useState<TopMover[]>([]);
  const [weatherImpact, setWeatherImpact] = useState<WeatherImpactPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState(14);

  useEffect(() => {
    api.getStores().then(setStores);
  }, []);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [tm, wi] = await Promise.all([
          api.getTopMovers(period, 20),
          api.getWeatherImpact(storeId),
        ]);
        setTopMovers(tm.movers);
        setWeatherImpact(wi.data);
      } catch (e) {
        console.error("Failed to load insights:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [storeId, period]);

  // Prepare weather impact data grouped by category
  const seasonalCategories = ["Winter Tires", "BBQ Grills & Accessories", "Snow Blowers", "Patio Furniture", "Hockey Equipment"];
  const weatherChartData = weatherImpact
    .filter((w) => seasonalCategories.includes(w.category_name))
    .map((w) => ({
      category: w.category_name.length > 15 ? w.category_name.slice(0, 15) + "..." : w.category_name,
      temp_range: w.temp_range,
      avg_quantity: w.avg_quantity,
      sample_count: w.sample_count,
    }));

  // Group by temp range for bar chart
  const tempRanges = ["< -10\u00b0C", "-10 to 0\u00b0C", "0 to 10\u00b0C", "10 to 20\u00b0C", "> 20\u00b0C"];
  const winterTiresByTemp = tempRanges.map((tr) => {
    const match = weatherImpact.find((w) => w.category_name === "Winter Tires" && w.temp_range === tr);
    const bbq = weatherImpact.find((w) => w.category_name === "BBQ Grills & Accessories" && w.temp_range === tr);
    return {
      temp_range: tr,
      "Winter Tires": match?.avg_quantity || 0,
      "BBQ Grills": bbq?.avg_quantity || 0,
    };
  });

  const topUp = topMovers.filter((m) => m.direction === "up").slice(0, 5);
  const topDown = topMovers.filter((m) => m.direction === "down").slice(0, 5);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Insights</h1>
        <p className="mt-1 text-sm text-gray-500">Weather impact analysis and demand trends</p>
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-4">
        {stores.length > 0 && (
          <StoreSelector stores={stores} selectedId={storeId} onChange={setStoreId} />
        )}
        <select
          value={period}
          onChange={(e) => setPeriod(Number(e.target.value))}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm"
        >
          <option value={7}>7-day comparison</option>
          <option value={14}>14-day comparison</option>
          <option value={30}>30-day comparison</option>
        </select>
      </div>

      {loading ? (
        <div className="flex h-96 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
        </div>
      ) : (
        <div className="space-y-6">
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h3 className="mb-2 text-lg font-semibold text-gray-900">Weather Impact on Demand</h3>
            <p className="mb-4 text-sm text-gray-500">
              Average daily demand by temperature range — Winter Tires vs BBQ Grills
            </p>
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={winterTiresByTemp}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="temp_range" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} label={{ value: "Avg Qty", angle: -90, position: "insideLeft", fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="Winter Tires" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="BBQ Grills" fill="#f97316" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <h3 className="mb-4 text-lg font-semibold text-green-700">Top Gainers</h3>
              <div className="space-y-3">
                {topUp.map((m, i) => (
                  <div key={i} className="flex items-center justify-between rounded-lg bg-green-50 px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{m.category_name}</p>
                      <p className="text-xs text-gray-500">{m.store_name}</p>
                      <p className="text-xs text-gray-400">
                        {m.previous_avg_qty.toFixed(1)} &rarr; {m.current_avg_qty.toFixed(1)} units/day
                      </p>
                    </div>
                    <span className="text-lg font-bold text-green-700">+{m.pct_change.toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <h3 className="mb-4 text-lg font-semibold text-red-700">Top Decliners</h3>
              <div className="space-y-3">
                {topDown.map((m, i) => (
                  <div key={i} className="flex items-center justify-between rounded-lg bg-red-50 px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{m.category_name}</p>
                      <p className="text-xs text-gray-500">{m.store_name}</p>
                      <p className="text-xs text-gray-400">
                        {m.previous_avg_qty.toFixed(1)} &rarr; {m.current_avg_qty.toFixed(1)} units/day
                      </p>
                    </div>
                    <span className="text-lg font-bold text-red-700">{m.pct_change.toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
