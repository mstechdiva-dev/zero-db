import { notFound } from "next/navigation";
import Link from "next/link";
import AgentEditor from "./AgentEditor";

const RAILWAY_API_URL = process.env.RAILWAY_API_URL;
const ADMIN_SECRET = process.env.ADMIN_SECRET ?? "";

interface AgentData {
  name: string;
  content: string;
  role: string;
  settings: { model: string | null; temperature: number | null; max_tokens: number | null };
  versions: Array<{ id: string; saved_by: string | null; saved_at: string; label: string | null }>;
}

async function loadAgent(name: string): Promise<AgentData | null> {
  if (!RAILWAY_API_URL) return null;
  try {
    const res = await fetch(`${RAILWAY_API_URL}/admin/agents/${name}`, {
      headers: { "x-admin-secret": ADMIN_SECRET },
      cache: "no-store",
    });
    if (res.status === 404) return null;
    if (!res.ok) return null;
    return await res.json();
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
  const agent = await loadAgent(name);

  if (!agent) notFound();

  return (
    <div className="flex flex-col h-full">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-gray-600 mb-6 flex-shrink-0">
        <Link href="/admin" className="hover:text-white transition-colors">
          Admin
        </Link>
        <span>/</span>
        <Link href="/admin/agents" className="hover:text-white transition-colors">
          Agents
        </Link>
        <span>/</span>
        <span className="text-white font-medium">{agent.name}</span>
      </nav>

      <AgentEditor
        agentName={agent.name}
        role={agent.role}
        initialContent={agent.content}
        initialSettings={agent.settings}
        initialVersions={agent.versions}
      />
    </div>
  );
}
