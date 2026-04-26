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
  const [toggling, setToggling] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

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

  async function toggleActive(db: Database) {
    setToggling(db.id);
    const supabase = createClient();
    const newValue = !db.is_active;
    const { error } = await supabase
      .from("connected_databases")
      .update({ is_active: newValue })
      .eq("id", db.id);
    if (!error) {
      setDatabases((prev) =>
        prev.map((d) => (d.id === db.id ? { ...d, is_active: newValue } : d))
      );
    }
    setToggling(null);
  }

  async function deleteDatabase(id: string) {
    setDeleting(id);
    const supabase = createClient();
    const { error } = await supabase
      .from("connected_databases")
      .delete()
      .eq("id", id);
    if (!error) {
      setDatabases((prev) => prev.filter((d) => d.id !== id));
    }
    setDeleting(null);
    setConfirmDelete(null);
  }

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
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span
                className={`w-2 h-2 rounded-full ${db.is_active ? "bg-[#00e87a]" : "bg-gray-600"}`}
              />
              <span className="text-xs text-gray-400">
                {db.is_active ? "Scout watching" : "Inactive"}
              </span>
            </div>
            <button
              onClick={() => toggleActive(db)}
              disabled={toggling === db.id || deleting === db.id}
              className="text-xs px-3 py-1.5 rounded-lg border transition-colors disabled:opacity-40 disabled:cursor-not-allowed border-gray-700 text-gray-400 hover:border-gray-500 hover:text-white"
            >
              {toggling === db.id ? "…" : db.is_active ? "Disable" : "Enable"}
            </button>
            {confirmDelete === db.id ? (
              <div className="flex items-center gap-2">
                <span className="text-xs text-red-400">Remove?</span>
                <button
                  onClick={() => setConfirmDelete(null)}
                  className="text-xs px-2 py-1 rounded border border-gray-700 text-gray-400 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => deleteDatabase(db.id)}
                  disabled={deleting === db.id}
                  className="text-xs px-2 py-1 rounded border border-red-800 text-red-400 hover:bg-red-900/30 transition-colors disabled:opacity-40"
                >
                  {deleting === db.id ? "…" : "Remove"}
                </button>
              </div>
            ) : (
              <button
                onClick={() => setConfirmDelete(db.id)}
                disabled={deleting === db.id}
                className="text-xs px-3 py-1.5 rounded-lg border transition-colors disabled:opacity-40 disabled:cursor-not-allowed border-gray-800 text-gray-600 hover:border-red-800 hover:text-red-400"
              >
                Remove
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
