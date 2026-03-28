"use client";

import type { Category } from "@/lib/types";

interface CategorySelectorProps {
  categories: Category[];
  selectedId: number;
  onChange: (id: number) => void;
}

export default function CategorySelector({ categories, selectedId, onChange }: CategorySelectorProps) {
  return (
    <select
      value={selectedId}
      onChange={(e) => onChange(Number(e.target.value))}
      className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
    >
      {categories.map((cat) => (
        <option key={cat.id} value={cat.id}>
          {cat.name}
        </option>
      ))}
    </select>
  );
}
