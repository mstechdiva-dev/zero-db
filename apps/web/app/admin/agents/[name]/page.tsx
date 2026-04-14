import { createClient } from "@supabase/supabase-js";
import { notFound } from "next/navigation";
import Link from "next/link";
import path from "path";
import fs from "fs";
import AgentEditor from "./AgentEditor";

function serviceDb() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false } }
  );
}

const AGENT_NAMES = ["obi", "sal", "scout", "sully", "zero"];

function parseRole(content: string): string {
  return content.match(/## Role\s*\n\s*\n(.+)/)?.[1]?.trim() ?? "";
}

async function loadContent(name: string): Promise<string | null> {
  // 1. Try Supabase (source of truth after first edit)
  const db = serviceDb();
  const { data } = await db
    .from("agent_skills")
    .select("content")
    .eq("name", name)
    .single();
  if (data?.content) return data.content;

  // 2. Fall back to disk (repo file, before any admin edit)
  try {
    const filePath = path.join(process.cwd(), "..", "..", "agents", `${name}.md`);
    return fs.readFileSync(filePath, "utf-8");
  } catch {
    return null;
  }
}

export default async function AgentEditorPage({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = await params;

  if (!AGENT_NAMES.includes(name)) notFound();

  const content = await loadContent(name);
  if (content === null) notFound();

  const role = parseRole(content);

  return (
    <div className="flex flex-col h-full">
      <nav className="flex items-center gap-2 text-sm text-gray-600 mb-6 flex-shrink-0">
        <Link href="/admin" className="hover:text-white transition-colors">Admin</Link>
        <span>/</span>
        <Link href="/admin/agents" className="hover:text-white transition-colors">Agents</Link>
        <span>/</span>
        <span className="text-white font-medium">{name}</span>
      </nav>

      <AgentEditor agentName={name} role={role} initialContent={content} />
    </div>
  );
}
