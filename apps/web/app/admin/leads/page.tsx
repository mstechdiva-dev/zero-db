import { createClient } from "@supabase/supabase-js";
import Link from "next/link";

function adminDb() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false } }
  );
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

export default async function LeadsPage() {
  const db = adminDb();

  const { data: leads } = await db
    .from("leads")
    .select("id, org_id, user_email, sal_summary, created_at")
    .order("created_at", { ascending: false })
    .limit(50);

  // Load full conversation only for the leads we're displaying
  const leadIds = (leads ?? []).map((l: any) => l.id);
  const { data: conversations } =
    leadIds.length > 0
      ? await db.from("leads").select("id, conversation").in("id", leadIds)
      : { data: [] };

  const conversationById = (conversations ?? []).reduce(
    (acc: Record<string, any[]>, c: { id: string; conversation: any[] }) => {
      acc[c.id] = c.conversation;
      return acc;
    },
    {}
  );

  // Fetch org names for display
  const orgIds = Array.from(new Set((leads ?? []).map((l: any) => l.org_id).filter(Boolean)));
  const { data: orgs } =
    orgIds.length > 0
      ? await db
          .from("organizations")
          .select("id, name")
          .in("id", orgIds)
      : { data: [] };

  const orgNameById = (orgs ?? []).reduce(
    (acc: Record<string, string>, o: { id: string; name: string }) => {
      acc[o.id] = o.name;
      return acc;
    },
    {}
  );

  const leadList = leads ?? [];

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Leads</h1>
          <p className="text-gray-500 text-sm mt-1">
            Qualified sales leads captured by Sal —{leadList.length} total
          </p>
        </div>
      </div>

      {leadList.length === 0 ? (
        <div className="bg-[#111] border border-gray-800 rounded-xl p-16 text-center">
          <p className="text-gray-600">No leads yet.</p>
          <p className="text-gray-700 text-sm mt-1">
            Sal will capture qualified Teams and Enterprise leads here when
            they chat on the Pricing page.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {leadList.map((lead: any) => {
            const messages: { role: string; content: string }[] =
              Array.isArray(conversationById[lead.id]) ? conversationById[lead.id] : [];
            const userMessages = messages.filter((m) => m.role === "user");

            return (
              <div
                key={lead.id}
                className="bg-[#111] border border-gray-800 rounded-xl overflow-hidden"
              >
                {/* Lead header */}
                <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-3">
                      <span className="text-white font-medium">
                        {lead.user_email ?? "Unknown"}
                      </span>
                      {lead.org_id && orgNameById[lead.org_id] && (
                        <Link
                          href={`/admin/orgs/${lead.org_id}`}
                          className="text-xs text-gray-500 hover:text-[#00e87a] transition-colors"
                        >
                          {orgNameById[lead.org_id]} →
                        </Link>
                      )}
                    </div>
                    <p className="text-gray-600 text-xs mt-0.5">
                      {timeAgo(lead.created_at)} · {userMessages.length} messages
                    </p>
                  </div>
                  <span className="text-xs font-mono px-2 py-1 rounded border text-purple-400 bg-purple-400/10 border-purple-400/30">
                    LEAD
                  </span>
                </div>

                {/* Sal's summary (the message that triggered CREATE_LEAD) */}
                {lead.sal_summary && (
                  <div className="px-6 py-4 border-b border-gray-900">
                    <p className="text-xs uppercase tracking-wider text-gray-600 mb-2">
                      Sal's summary
                    </p>
                    <p className="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
                      {lead.sal_summary}
                    </p>
                  </div>
                )}

                {/* Conversation transcript */}
                {messages.length > 0 && (
                  <details className="group">
                    <summary className="px-6 py-3 text-xs text-gray-600 cursor-pointer hover:text-gray-400 transition-colors list-none flex items-center gap-2">
                      <span className="group-open:hidden">▶</span>
                      <span className="hidden group-open:inline">▼</span>
                      View full conversation ({messages.length} messages)
                    </summary>
                    <div className="px-6 pb-4 space-y-3 border-t border-gray-900 pt-4">
                      {messages.map((msg, i) => (
                        <div
                          key={i}
                          className={`flex ${
                            msg.role === "user" ? "justify-end" : "justify-start"
                          }`}
                        >
                          <div
                            className={`max-w-[80%] rounded-xl px-4 py-2 text-sm ${
                              msg.role === "user"
                                ? "bg-[#00e87a]/10 text-white rounded-br-sm"
                                : "bg-gray-900 text-gray-300 rounded-bl-sm"
                            }`}
                          >
                            <p className="text-xs mb-1 opacity-50 capitalize">
                              {msg.role === "user" ? lead.user_email ?? "User" : "Sal"}
                            </p>
                            <p className="whitespace-pre-wrap leading-relaxed">
                              {msg.content}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
