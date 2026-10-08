"use client";

import { useState } from "react";

const ENGINES = [
  { id: "postgresql", label: "PostgreSQL", hint: "postgresql://user:password@host:5432/dbname" },
  { id: "supabase", label: "Supabase", hint: "postgresql://postgres:password@db.xxxx.supabase.co:5432/postgres" },
  { id: "neon", label: "Neon", hint: "postgresql://user:password@ep-xxxx.neon.tech/dbname" },
  { id: "cockroachdb", label: "CockroachDB", hint: "postgresql://user:password@host:26257/dbname" },
  { id: "mysql", label: "MySQL", hint: "mysql://user:password@host:3306/dbname" },
  { id: "mariadb", label: "MariaDB", hint: "mysql://user:password@host:3306/dbname" },
  { id: "mongodb", label: "MongoDB", hint: "mongodb+srv://user:password@cluster.mongodb.net/dbname" },
  { id: "redis", label: "Redis", hint: "redis://user:password@host:6379" },
];

export default function ConnectForm({ onConnected }: { onConnected: () => void }) {
  const [engine, setEngine] = useState("postgresql");
  const [name, setName] = useState("");
  const [conn, setConn] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const hint = ENGINES.find((e) => e.id === engine)?.hint ?? "";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/databases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          engine,
          display_name: name.trim() || "My database",
          connection_string: conn.trim(),
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.error ?? "Couldn't connect. Check the connection string and try again.");
      } else {
        setConn(""); // don't keep the password in the page
        setDone(true);
      }
    } catch {
      setError("Couldn't reach SchemaZero. Check your connection and try again.");
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div className="bg-[#111] border border-[#00e87a]/30 rounded-xl p-6">
        <p className="text-[#00e87a] font-medium mb-2">Connected</p>
        <p className="text-sm text-gray-300 mb-5">
          We tested the connection and saved it encrypted. Scout starts watching within about a
          minute. The status light on your dashboard turns green once it is.
        </p>
        <button
          onClick={onConnected}
          className="px-5 py-2.5 bg-[#00e87a] text-black font-semibold text-sm rounded-lg hover:bg-[#00c96a] transition-colors"
        >
          Go to dashboard
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="bg-[#111] border border-gray-800 rounded-xl p-6 space-y-4">
      <div>
        <p className="text-sm font-medium text-white">Secure connection</p>
        <p className="text-xs text-gray-500 mt-1">
          Goes straight to SchemaZero and is encrypted before it&apos;s stored. It is never sent
          to the chat.
        </p>
      </div>

      <label className="block">
        <span className="text-xs text-gray-400">Database type</span>
        <select
          value={engine}
          onChange={(e) => setEngine(e.target.value)}
          className="mt-1 w-full px-3 py-2.5 bg-[#0a0a0a] border border-gray-800 rounded-lg text-white text-sm focus:outline-none focus:border-[#00e87a]"
        >
          {ENGINES.map((e) => (
            <option key={e.id} value={e.id}>
              {e.label}
            </option>
          ))}
        </select>
      </label>

      <label className="block">
        <span className="text-xs text-gray-400">Name</span>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Production"
          maxLength={80}
          className="mt-1 w-full px-3 py-2.5 bg-[#0a0a0a] border border-gray-800 rounded-lg text-white placeholder-gray-600 text-sm focus:outline-none focus:border-[#00e87a]"
        />
      </label>

      <label className="block">
        <span className="text-xs text-gray-400">Connection string</span>
        <input
          type="password"
          value={conn}
          onChange={(e) => setConn(e.target.value)}
          placeholder={hint}
          autoComplete="off"
          spellCheck={false}
          required
          className="mt-1 w-full px-3 py-2.5 bg-[#0a0a0a] border border-gray-800 rounded-lg text-white placeholder-gray-600 text-sm font-mono focus:outline-none focus:border-[#00e87a]"
        />
      </label>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <button
        type="submit"
        disabled={busy || !conn.trim()}
        className="w-full px-4 py-2.5 bg-[#00e87a] text-black font-semibold text-sm rounded-lg hover:bg-[#00c96a] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {busy ? "Testing connection…" : "Test and connect"}
      </button>
    </form>
  );
}
