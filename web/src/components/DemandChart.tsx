"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface DataPoint {
  date: string;
  actual?: number;
  predicted?: number;
  lower?: number;
  upper?: number;
}

interface DemandChartProps {
  data: DataPoint[];
  title?: string;
  showConfidence?: boolean;
}

export default function DemandChart({ data, title, showConfidence = false }: DemandChartProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      {title && <h3 className="mb-4 text-lg font-semibold text-gray-900">{title}</h3>}
      <ResponsiveContainer width="100%" height={350}>
        <AreaChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <defs>
            <linearGradient id="actualGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="predictedGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12 }}
            tickFormatter={(v) => new Date(v).toLocaleDateString("en-CA", { month: "short", day: "numeric" })}
          />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip
            contentStyle={{ borderRadius: "8px", fontSize: "13px" }}
            labelFormatter={(v) => new Date(v).toLocaleDateString("en-CA", { weekday: "short", month: "short", day: "numeric" })}
          />
          <Legend />
          {showConfidence && (
            <Area
              type="monotone"
              dataKey="upper"
              stroke="none"
              fill="#10b981"
              fillOpacity={0.1}
              name="Confidence Band"
            />
          )}
          {showConfidence && (
            <Area
              type="monotone"
              dataKey="lower"
              stroke="none"
              fill="#ffffff"
              fillOpacity={1}
              name=""
              legendType="none"
            />
          )}
          <Area
            type="monotone"
            dataKey="actual"
            stroke="#3b82f6"
            fill="url(#actualGrad)"
            strokeWidth={2}
            name="Actual"
            dot={false}
          />
          <Area
            type="monotone"
            dataKey="predicted"
            stroke="#10b981"
            fill="url(#predictedGrad)"
            strokeWidth={2}
            strokeDasharray="5 5"
            name="Predicted"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
