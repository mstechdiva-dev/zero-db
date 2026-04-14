import { createClient } from "@supabase/supabase-js";
import Link from "next/link";
import fs from "fs";
import path from "path";

function serviceDb() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false } }
  );
}

const MODEL_LABELS: Record<string, string> = {
  "claude-opus-4-6": "Opus 4.6",
  "claude-sonnet-4-6": "Sonnet 4.6",
  "claude-haiku-4-5-20251001": "Haiku 4.5",
};

function parseSettings(content: string) {
  const model = content.match(/Model:\s*(\S+)/i)?.[1] ?? null;
  const temp = content.match(/Temperature:\s*([\d.]+)/i)?.[1];
  const tokens = content.match(/Max tokens:\s*(\d+)/i)?.[1];
  return {
    model: model ?? null,
    temperature: temp ? parseFloat(temp) : null,
    max_tokens: tokens ? parseInt(tokens) : null,
  };
}

function parseRole(content: string): string {
  return content.match(/## Role\s*\n\s*\n(.+)/)?.[1]?.trim() ?? "";
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// Agent names derived from MD files in the repo
const AGENT_NAMES = ["obi", "sal", "scout", "sully", "zero"];

const BADGE_COLORS: Record<string, string> = {
  scout: "text-blue-400 bg-blue-400/10 border-blue-400/30",
  zero: "text-purple-400 bg-purple-400/10 border-purple-400/30",
  obi: "text-[#00e87a] bg-[#00e87a]/10 border-[#00e87a]/30",
  sal: "text-yellow-400 bg-yellow-400/10 border-yellow-400/30",
  sully: "text-orange-400 bg-orange-400/10 border-orange-400/30",
};

export default async function AgentsPage() {
  const db = serviceDb();

  // Load all agent content from Supabase (source of truth after first edit)
  const { data: rows } = await db
    .from("agent_skills")
    .select("name, content, saved_by, updated_at")
    .in("name", AGENT_NAMES);

  const byName = Object.fromEntries((rows ?? []).map((r) => [r.name, r]));

  const agents = AGENT_NAMES.map((name) => {
    const row = byName[name];
    const content = row?.content ?? "";
    return {
      name,
      content,
      role: parseRole(content),
      settings: parseSettings(content),
      saved_by: row?.saved_by ?? null,
      updated_at: row?.updated_at ?? null,
      inSupabase: !!row,
    };
  });

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold">Agent Skills</h1>
        <p className="text-gray-500 text-sm mt-1">
          Edit the MD files that define each agent&apos;s behavior, knowledge, and settings.
          Changes are saved to Supabase and take effect on the next agent call — no redeploy needed.
        </p>
      </div>

      <div className="bg-[#111] border border-gray-800 rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-800 text-xs uppercase tracking-wider text-gray-500">
              <th className="text-left px-6 py-3">Agent</th>
              <th className="text-left px-6 py-3">Role</th>
              <th className="text-left px-6 py-3">Model</th>
              <th className="text-right px-6 py-3">Temp</th>
              <th className="text-left px-6 py-3">Last saved</th>
              <th className="px-6 py-3" />
            </tr>
          </thead>
          <tbody>
            {agents.map((agent) => (
              <tr
                key={agent.name}
                className="border-b border-gray-900 hover:bg-white/[0.02] transition-colors"
              >
                <td className="px-6 py-4">
                  <span
                    className={`text-xs font-mono font-bold px-2 py-1 rounded border uppercase ${
                      BADGE_COLORS[agent.name] ?? "text-gray-400 bg-gray-400/10 border-gray-400/30"
                    }`}
                  >
                    {agent.name}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-300 max-w-xs truncate">
                  {agent.role || <span className="text-gray-600 italic">—</span>}
                </td>
                <td className="px-6 py-4 text-sm font-mono text-gray-400">
                  {agent.settings.model
                    ? (MODEL_LABELS[agent.settings.model] ?? agent.settings.model)
                    : <span className="text-gray-700">—</span>}
                </td>
                <td className="px-6 py-4 text-right text-sm font-mono text-gray-400 tabular-nums">
                  {agent.settings.temperature ?? <span className="text-gray-700">—</span>}
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {agent.updated_at ? (
                    <span title={agent.updated_at}>{timeAgo(agent.updated_at)}</span>
                  ) : (
                    <span className="text-gray-700">never edited</span>
                  )}
                </td>
                <td className="px-6 py-4 text-right">
                  <Link
                    href={`/admin/agents/${agent.name}`}
                    className="text-xs font-medium text-[#00e87a] hover:text-white border border-[#00e87a]/40 hover:border-white/30 px-3 py-1.5 rounded transition-colors"
                  >
                    Edit
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-4 text-xs text-gray-600">
        Version history is in git. To roll back, revert the commit and the next agent call picks it up.
      </p>
    </div>
  );
}
