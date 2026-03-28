"use client";

import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { api } from "@/lib/api";
import type { ModelInfo, Store, Category, TopMover } from "@/lib/types";
import KpiCard from "@/components/KpiCard";

export default function Dashboard() {
  const [stores, setStores] = useState<Store[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [topMovers, setTopMovers] = useState<TopMover[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [s, c, m, tm] = await Promise.all([
          api.getStores(),
          api.getCategories(),
          api.getModelInfo(),
          api.getTopMovers(14, 10),
        ]);
        setStores(s);
        setCategories(c);
        setModelInfo(m);
        setTopMovers(tm.movers);
      } catch (e) {
        console.error("Failed to load dashboard data:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  const featureData = modelInfo
    ? Object.entries(modelInfo.feature_importance)
        .slice(0, 8)
        .map(([name, value]) => ({ name: name.replace(/_/g, " "), importance: +(value * 100).toFixed(1) }))
    : [];

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">AI-powered retail demand intelligence overview</p>
      </div>

      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard title="Stores" value={stores.length} subtitle="Across 5 Canadian cities" />
        <KpiCard title="Product Categories" value={categories.length} subtitle={`${categories.filter((c) => c.is_seasonal).length} seasonal`} />
        <KpiCard
          title="Model R-squared"
          value={modelInfo ? `${(modelInfo.metrics.r2 * 100).toFixed(1)}%` : "N/A"}
          subtitle="Demand variance explained"
        />
        <KpiCard
          title="Forecast RMSE"
          value={modelInfo ? modelInfo.metrics.rmse.toFixed(2) : "N/A"}
          subtitle="Root mean square error"
        />
      </div>

      <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-semibold text-gray-900">Feature Importance</h3>
          <p className="mb-4 text-sm text-gray-500">What drives demand predictions</p>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={featureData} layout="vertical" margin={{ left: 100 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis type="number" tick={{ fontSize: 12 }} tickFormatter={(v) => `${v}%`} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} width={100} />
              <Tooltip formatter={(v) => `${v}%`} />
              <Bar dataKey="importance" fill="#3b82f6" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-semibold text-gray-900">Top Movers (14-day)</h3>
          <p className="mb-4 text-sm text-gray-500">Biggest demand changes vs prior period</p>
          <div className="space-y-3 max-h-[300px] overflow-y-auto">
            {topMovers.slice(0, 8).map((m, i) => (
              <div key={i} className="flex items-center justify-between rounded-lg border border-gray-100 px-4 py-3">
                <div>
                  <p className="text-sm font-medium text-gray-900">{m.category_name}</p>
                  <p className="text-xs text-gray-500">{m.store_name}</p>
                </div>
                <span
                  className={`rounded-full px-3 py-1 text-sm font-bold ${
                    m.direction === "up"
                      ? "bg-green-100 text-green-700"
                      : "bg-red-100 text-red-700"
                  }`}
                >
                  {m.direction === "up" ? "+" : ""}
                  {m.pct_change.toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
