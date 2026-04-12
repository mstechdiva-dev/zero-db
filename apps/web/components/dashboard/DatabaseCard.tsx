"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase";

interface Database {
  id: string;
  engine: string;
  display_name: string;
  is_active: boolean;
  created_at: string;
}

export default function DatabaseCard() {
  const [databases, setDatabases] = useState<Database[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const supabase = createClient();
    supabase
      .from("connected_databases")
      .select("id, engine, display_name, is_active, created_at")
      .then(({ data }) => {
        setDatabases(data ?? []);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="space-y-3">
        {[...Array(2)].map((_, i) => (
          <div
            key={i}
            className="h-20 bg-[#111] border border-gray-800 rounded-xl animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (databases.length === 0) {
    return (
      <div className="bg-[#111] border border-gray-800 rounded-xl p-12 text-center">
        <p className="text-gray-500 mb-4">No databases connected yet.</p>
        <a
          href="/onboarding"
          className="px-4 py-2 bg-[#00e87a] text-black font-semibold rounded-lg hover:bg-[#00c96a] transition-colors text-sm"
        >
          Connect your first database
        </a>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {databases.map((db) => (
        <div
          key={db.id}
          className="bg-[#111] border border-gray-800 rounded-xl p-5 flex items-center justify-between"
        >
          <div>
            <span className="text-white font-semibold">{db.display_name}</span>
            <p className="text-gray-500 text-sm capitalize mt-0.5">{db.engine}</p>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${db.is_active ? "bg-[#00e87a]" : "bg-gray-600"}`}
            />
            <span className="text-xs text-gray-400">
              {db.is_active ? "Scout watching" : "Inactive"}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
