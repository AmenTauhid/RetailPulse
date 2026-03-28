"use client";

import type { Store } from "@/lib/types";

interface StoreSelectorProps {
  stores: Store[];
  selectedId: number;
  onChange: (id: number) => void;
}

export default function StoreSelector({ stores, selectedId, onChange }: StoreSelectorProps) {
  return (
    <select
      value={selectedId}
      onChange={(e) => onChange(Number(e.target.value))}
      className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
    >
      {stores.map((store) => (
        <option key={store.id} value={store.id}>
          {store.name}
        </option>
      ))}
    </select>
  );
}
