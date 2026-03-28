"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Anomaly, Store, Category } from "@/lib/types";
import AnomalyCard from "@/components/AnomalyCard";

export default function AnomaliesPage() {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [severity, setSeverity] = useState<string>("");
  const [days, setDays] = useState(60);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const params: Record<string, any> = { days, limit: 50 };
        if (severity) params.severity = severity;
        const res = await api.getAnomalies(params);
        setAnomalies(res.anomalies);
        setTotal(res.total);
      } catch (e) {
        console.error("Failed to load anomalies:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [severity, days]);

  const highCount = anomalies.filter((a) => a.severity === "high").length;
  const mediumCount = anomalies.filter((a) => a.severity === "medium").length;
  const lowCount = anomalies.filter((a) => a.severity === "low").length;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Anomaly Detection</h1>
        <p className="mt-1 text-sm text-gray-500">
          Demand spikes and drops that deviate significantly from predictions
        </p>
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-4">
        <select
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm"
        >
          <option value="">All severities</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm"
        >
          <option value={30}>Last 30 days</option>
          <option value={60}>Last 60 days</option>
          <option value={90}>Last 90 days</option>
        </select>

        <div className="ml-auto flex gap-3 text-sm">
          <span className="rounded-full bg-red-100 px-3 py-1 font-medium text-red-700">
            {highCount} High
          </span>
          <span className="rounded-full bg-amber-100 px-3 py-1 font-medium text-amber-700">
            {mediumCount} Medium
          </span>
          <span className="rounded-full bg-blue-100 px-3 py-1 font-medium text-blue-700">
            {lowCount} Low
          </span>
          <span className="rounded-full bg-gray-100 px-3 py-1 font-medium text-gray-600">
            {total} Total
          </span>
        </div>
      </div>

      {loading ? (
        <div className="flex h-96 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
        </div>
      ) : anomalies.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white p-12 text-center">
          <p className="text-gray-500">No anomalies detected for the selected filters.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {anomalies.map((a, i) => (
            <AnomalyCard key={`${a.store_id}-${a.category_id}-${a.date}-${i}`} anomaly={a} />
          ))}
        </div>
      )}
    </div>
  );
}
