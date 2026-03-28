interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: { value: number; label: string };
  icon?: React.ReactNode;
}

export default function KpiCard({ title, value, subtitle, trend, icon }: KpiCardProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-gray-500">{title}</p>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>
      <p className="mt-2 text-3xl font-bold text-gray-900">{value}</p>
      {subtitle && <p className="mt-1 text-sm text-gray-500">{subtitle}</p>}
      {trend && (
        <p className={`mt-2 text-sm font-medium ${trend.value >= 0 ? "text-green-600" : "text-red-600"}`}>
          {trend.value >= 0 ? "+" : ""}
          {trend.value.toFixed(1)}% {trend.label}
        </p>
      )}
    </div>
  );
}
