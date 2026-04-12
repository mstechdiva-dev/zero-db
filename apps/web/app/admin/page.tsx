import { createClient } from "@supabase/supabase-js";
import Link from "next/link";

// Service-role client — bypasses RLS, server-only, never sent to the browser
function adminDb() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false } }
  );
}

function planBadge(org: {
  plan: string;
  trial_converted: boolean;
  trial_ends_at: string;
}) {
  if (org.trial_converted || org.plan === "solo") {
    return { label: "SOLO", cls: "text-[#00e87a] bg-[#00e87a]/10 border-[#00e87a]/30" };
  }
  if (org.plan === "teams") {
    return { label: "TEAMS", cls: "text-purple-400 bg-purple-400/10 border-purple-400/30" };
  }
  if (org.plan === "enterprise") {
    return { label: "ENTERPRISE", cls: "text-yellow-400 bg-yellow-400/10 border-yellow-400/30" };
  }
  // plan === 'trial'
  const daysLeft = Math.ceil(
    (new Date(org.trial_ends_at).getTime() - Date.now()) / 86_400_000
  );
  if (daysLeft > 0) {
    return {
      label: `${daysLeft}d left`,
      cls: "text-blue-400 bg-blue-400/10 border-blue-400/30",
    };
  }
  return { label: "EXPIRED", cls: "text-red-400 bg-red-400/10 border-red-400/30" };
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

export default async function AdminOverviewPage() {
  const db = adminDb();

  const [
    { data: orgs },
    { count: activeDbs },
    { count: events7d },
    { count: totalEvents },
    { count: leadCount },
    { data: userRows },
    { data: dbRows },
    { data: recentChanges },
  ] = await Promise.all([
    db.from("organizations").select("*").order("created_at", { ascending: false }),
    db
      .from("connected_databases")
      .select("*", { count: "exact", head: true })
      .eq("is_active", true),
    db
      .from("change_events")
      .select("*", { count: "exact", head: true })
      .gte(
        "detected_at",
        new Date(Date.now() - 7 * 86_400_000).toISOString()
      ),
    db.from("change_events").select("*", { count: "exact", head: true }),
    db.from("leads").select("*", { count: "exact", head: true }),
    db.from("users").select("org_id"),
    db.from("connected_databases").select("org_id").eq("is_active", true),
    db
      .from("change_events")
      .select("org_id, detected_at")
      .order("detected_at", { ascending: false })
      .limit(500),
  ]);

  const now = Date.now();
  const orgList = orgs ?? [];

  const activeTrials = orgList.filter(
    (o) =>
      o.plan === "trial" &&
      new Date(o.trial_ends_at).getTime() > now &&
      !o.trial_converted
  ).length;
  const conversions = orgList.filter((o) => o.trial_converted).length;
  const expired = orgList.filter(
    (o) =>
      o.plan === "trial" &&
      new Date(o.trial_ends_at).getTime() <= now &&
      !o.trial_converted
  ).length;

  const userCountByOrg = (userRows ?? []).reduce(
    (acc: Record<string, number>, u: { org_id: string }) => {
      acc[u.org_id] = (acc[u.org_id] ?? 0) + 1;
      return acc;
    },
    {}
  );
  const dbCountByOrg = (dbRows ?? []).reduce(
    (acc: Record<string, number>, d: { org_id: string }) => {
      acc[d.org_id] = (acc[d.org_id] ?? 0) + 1;
      return acc;
    },
    {}
  );
  const lastEventByOrg = (recentChanges ?? []).reduce(
    (acc: Record<string, string>, c: { org_id: string; detected_at: string }) => {
      if (!acc[c.org_id]) acc[c.org_id] = c.detected_at;
      return acc;
    },
    {}
  );

  const stats = [
    { label: "Total orgs", value: orgList.length, color: "text-white" },
    { label: "Active trials", value: activeTrials, color: "text-blue-400" },
    { label: "Converted", value: conversions, color: "text-[#00e87a]" },
    { label: "Expired", value: expired, color: "text-red-400" },
    { label: "Active DBs", value: activeDbs ?? 0, color: "text-white" },
    { label: "Events (7d)", value: events7d ?? 0, color: "text-white" },
    { label: "Events (total)", value: totalEvents ?? 0, color: "text-gray-400" },
    { label: "Leads", value: leadCount ?? 0, color: "text-purple-400" },
  ];

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold">Overview</h1>
        <p className="text-gray-500 text-sm mt-1">
          Managed SaaS — all customer organizations
        </p>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-4 gap-4 mb-10">
        {stats.map((s) => (
          <div
            key={s.label}
            className="bg-[#111] border border-gray-800 rounded-lg p-5"
          >
            <div className="text-gray-500 text-xs uppercase tracking-wider mb-2">
              {s.label}
            </div>
            <div className={`text-3xl font-bold ${s.color}`}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Org table */}
      <div className="bg-[#111] border border-gray-800 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
          <h2 className="font-semibold">All Organizations</h2>
          <span className="text-gray-600 text-sm">{orgList.length} total</span>
        </div>

        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-800 text-xs uppercase tracking-wider text-gray-500">
              <th className="text-left px-6 py-3">Organization</th>
              <th className="text-left px-6 py-3">Plan / Status</th>
              <th className="text-right px-6 py-3">Users</th>
              <th className="text-right px-6 py-3">DBs</th>
              <th className="text-left px-6 py-3">Last event</th>
              <th className="text-left px-6 py-3">Joined</th>
            </tr>
          </thead>
          <tbody>
            {orgList.map((org) => {
              const badge = planBadge(org);
              const lastEvent = lastEventByOrg[org.id];
              return (
                <tr
                  key={org.id}
                  className="border-b border-gray-900 hover:bg-white/[0.02] transition-colors"
                >
                  <td className="px-6 py-4">
                    <Link
                      href={`/admin/orgs/${org.id}`}
                      className="font-medium text-white hover:text-[#00e87a] transition-colors"
                    >
                      {org.name || (
                        <span className="text-gray-600 italic">Unnamed</span>
                      )}
                    </Link>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`text-xs font-mono font-bold px-2 py-1 rounded border ${badge.cls}`}
                    >
                      {badge.label}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right text-gray-400 tabular-nums">
                    {userCountByOrg[org.id] ?? 0}
                  </td>
                  <td className="px-6 py-4 text-right text-gray-400 tabular-nums">
                    {dbCountByOrg[org.id] ?? 0}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {lastEvent ? (
                      <span className="text-gray-400">{timeAgo(lastEvent)}</span>
                    ) : (
                      <span className="text-gray-700">—</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {new Date(org.created_at).toLocaleDateString()}
                  </td>
                </tr>
              );
            })}
            {orgList.length === 0 && (
              <tr>
                <td
                  colSpan={6}
                  className="px-6 py-16 text-center text-gray-700"
                >
                  No organizations yet
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
