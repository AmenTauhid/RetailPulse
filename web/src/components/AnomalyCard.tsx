import type { Anomaly } from "@/lib/types";

const SEVERITY_STYLES = {
  high: "border-red-200 bg-red-50 text-red-800",
  medium: "border-amber-200 bg-amber-50 text-amber-800",
  low: "border-blue-200 bg-blue-50 text-blue-800",
};

const SEVERITY_DOT = {
  high: "bg-red-500",
  medium: "bg-amber-500",
  low: "bg-blue-500",
};

interface AnomalyCardProps {
  anomaly: Anomaly;
}

export default function AnomalyCard({ anomaly }: AnomalyCardProps) {
  const direction = anomaly.residual > 0 ? "above" : "below";
  const pctDiff =
    anomaly.predicted_quantity > 0
      ? Math.abs((anomaly.residual / anomaly.predicted_quantity) * 100).toFixed(0)
      : "N/A";

  return (
    <div className={`rounded-lg border p-4 ${SEVERITY_STYLES[anomaly.severity]}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <span className={`inline-block h-2.5 w-2.5 rounded-full ${SEVERITY_DOT[anomaly.severity]}`} />
          <span className="text-sm font-semibold capitalize">{anomaly.severity} severity</span>
        </div>
        <span className="text-xs font-medium opacity-70">
          {new Date(anomaly.date).toLocaleDateString("en-CA", { month: "short", day: "numeric", year: "numeric" })}
        </span>
      </div>
      <p className="mt-2 text-sm">
        <span className="font-medium">{anomaly.category_name}</span> at{" "}
        <span className="font-medium">{anomaly.store_name}</span>
      </p>
      <p className="mt-1 text-sm">
        Actual: <span className="font-bold">{anomaly.actual_quantity}</span> units
        {" | "}
        Predicted: <span className="font-bold">{anomaly.predicted_quantity}</span> units
      </p>
      <p className="mt-1 text-xs opacity-80">
        {pctDiff}% {direction} forecast (z-score: {anomaly.z_score.toFixed(2)})
      </p>
    </div>
  );
}
