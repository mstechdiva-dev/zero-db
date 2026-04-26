import { createClient } from "@supabase/supabase-js";
import Link from "next/link";
import { notFound } from "next/navigation";

function adminDb() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false } }
  );
}

const RISK_STYLES: Record<string, string> = {
  low: "text-green-400 bg-green-400/10 border-green-400/30",
  medium: "text-yellow-400 bg-yellow-400/10 border-yellow-400/30",
  high: "text-orange-400 bg-orange-400/10 border-orange-400/30",
  critical: "text-red-400 bg-red-400/10 border-red-400/30",
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function trialStatus(org: {
  plan: string;
  trial_converted: boolean;
  trial_ends_at: string;
  trial_starts_at: string;
}): string {
  if (org.trial_converted) return "Converted to Solo";
  if (org.plan !== "trial") return org.plan.charAt(0).toUpperCase() + org.plan.slice(1);
  const daysLeft = Math.ceil(
    (new Date(org.trial_ends_at).getTime() - Date.now()) / 86_400_000
  );
  if (daysLeft > 0) return `Trial — ${daysLeft} days remaining`;
  return "Trial expired";
}

export default async function OrgDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const db = adminDb();
  const { id } = params;

  const [
    { data: org },
    { data: users },
    { data: databases },
    { data: changes },
    { data: alertConfig },
    { data: notifLog },
  ] = await Promise.all([
    db.from("organizations").select("*").eq("id", id).single(),
    db.from("users").select("id, email, role, created_at").eq("org_id", id),
    db
      .from("connected_databases")
      .select("*")
      .eq("org_id", id)
      .order("created_at", { ascending: false }),
    db
      .from("change_events")
      .select("id, change_type, object_type, object_name, risk_level, detected_at")
      .eq("org_id", id)
      .order("detected_at", { ascending: false })
      .limit(15),
    db
      .from("alert_configs")
      .select(
        "slack_webhook_url, pagerduty_api_key, email_recipients, notify_on, webhook_url"
      )
      .eq("org_id", id)
      .single(),
    db
      .from("notification_log")
      .select("id, channel, status, sent_at, change_event_id")
      .eq("org_id", id)
      .order("sent_at", { ascending: false })
      .limit(15),
  ]);

  if (!org) notFound();

  // Fetch heartbeats only for this org's databases to avoid cross-org data leakage
  const dbIds = (databases ?? []).map((d: any) => d.id as string);
  const { data: heartbeats } =
    dbIds.length > 0
      ? await db
          .from("scout_heartbeat")
          .select("database_id, last_seen")
          .in("database_id", dbIds)
      : { data: [] };

  const heartbeatByDb = (heartbeats ?? []).reduce(
    (acc: Record<string, { last_seen: string }>, h: any) => {
      acc[h.database_id] = h;
      return acc;
    },
    {}
  );

  const alertChannels = [
    { label: "Webhook", configured: !!(alertConfig?.webhook_url) },
    { label: "Slack", configured: !!(alertConfig?.slack_webhook_url) },
    { label: "PagerDuty", configured: !!(alertConfig?.pagerduty_api_key) },
    {
      label: "Email",
      configured:
        Array.isArray(alertConfig?.email_recipients) &&
        alertConfig.email_recipients.length > 0,
    },
  ];

  return (
    <div className="space-y-8">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Link href="/admin" className="hover:text-white transition-colors">
          Overview
        </Link>
        <span>/</span>
        <span className="text-white">{org.name || "Unnamed org"}</span>
      </div>

      {/* Org header */}
      <div className="bg-[#111] border border-gray-800 rounded-xl p-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-semibold">
              {org.name || <span className="text-gray-500 italic">Unnamed</span>}
            </h1>
            <p className="text-gray-500 text-sm mt-1">{trialStatus(org)}</p>
          </div>
          <div className="text-right text-sm text-gray-500">
            <div>ID: <span className="font-mono text-gray-400 text-xs">{org.id}</span></div>
            <div className="mt-1">
              Joined {new Date(org.created_at).toLocaleDateString()}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-4 mt-6">
          {[
            { label: "Plan", value: org.plan },
            {
              label: "Trial started",
              value: new Date(org.trial_starts_at).toLocaleDateString(),
            },
            {
              label: "Trial ends",
              value: new Date(org.trial_ends_at).toLocaleDateString(),
            },
            {
              label: "Converted",
              value: org.trial_converted ? "Yes" : "No",
            },
          ].map((f) => (
            <div key={f.label} className="bg-[#0a0a0a] rounded-lg p-4 border border-gray-900">
              <div className="text-gray-600 text-xs uppercase tracking-wider mb-1">
                {f.label}
              </div>
              <div className="text-white text-sm font-medium">{f.value}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-8">
        {/* Users */}
        <Section title="Users" count={(users ?? []).length}>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-wider text-gray-600 border-b border-gray-900">
                <th className="text-left py-2 pr-4">Email</th>
                <th className="text-left py-2 pr-4">Role</th>
                <th className="text-left py-2">Joined</th>
              </tr>
            </thead>
            <tbody>
              {(users ?? []).map((u: any) => (
                <tr key={u.id} className="border-b border-gray-900/50">
                  <td className="py-2 pr-4 text-gray-300">{u.email}</td>
                  <td className="py-2 pr-4 text-gray-500">{u.role}</td>
                  <td className="py-2 text-gray-600 text-xs">
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
              {(users ?? []).length === 0 && (
                <tr>
                  <td colSpan={3} className="py-4 text-gray-700 text-center">
                    No users
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </Section>

        {/* Alert config */}
        <Section title="Alert Channels" count={alertChannels.filter((c) => c.configured).length}>
          <div className="space-y-2">
            {alertChannels.map((ch) => (
              <div key={ch.label} className="flex items-center justify-between py-2 border-b border-gray-900/50">
                <span className="text-sm text-gray-300">{ch.label}</span>
                <span
                  className={`text-xs font-mono px-2 py-0.5 rounded border ${
                    ch.configured
                      ? "text-[#00e87a] bg-[#00e87a]/10 border-[#00e87a]/30"
                      : "text-gray-600 bg-gray-800/30 border-gray-800"
                  }`}
                >
                  {ch.configured ? "CONFIGURED" : "NOT SET"}
                </span>
              </div>
            ))}
            {alertConfig?.notify_on && (
              <div className="pt-2 text-xs text-gray-600">
                Alerts on:{" "}
                <span className="text-gray-400">
                  {(alertConfig.notify_on as string[]).join(", ")}
                </span>
              </div>
            )}
          </div>
        </Section>
      </div>

      {/* Connected databases */}
      <Section title="Databases" count={(databases ?? []).length}>
        <div className="space-y-2">
          {(databases ?? []).map((d: any) => {
            const hb = heartbeatByDb[d.id];
            const isActive =
              hb &&
              Date.now() - new Date(hb.last_seen).getTime() < 90_000;
            return (
              <div
                key={d.id}
                className="flex items-center justify-between py-3 border-b border-gray-900/50"
              >
                <div>
                  <span className="text-white font-medium">{d.display_name}</span>
                  <span className="text-gray-600 text-xs ml-2">{d.engine}</span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  {hb && (
                    <span className="text-gray-600">
                      {timeAgo(hb.last_seen)}
                    </span>
                  )}
                  <span
                    className={`flex items-center gap-1 ${
                      isActive ? "text-[#00e87a]" : "text-gray-600"
                    }`}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        isActive ? "bg-[#00e87a]" : "bg-gray-700"
                      }`}
                    />
                    {isActive ? "Active" : d.is_active ? "Inactive" : "Disabled"}
                  </span>
                </div>
              </div>
            );
          })}
          {(databases ?? []).length === 0 && (
            <p className="text-gray-700 text-sm py-4 text-center">
              No databases connected
            </p>
          )}
        </div>
      </Section>

      <div className="grid grid-cols-2 gap-8">
        {/* Recent changes */}
        <Section title="Recent Changes" count={(changes ?? []).length}>
          <div className="space-y-1">
            {(changes ?? []).map((c: any) => (
              <div
                key={c.id}
                className="flex items-center justify-between py-2 border-b border-gray-900/50 text-sm"
              >
                <div className="flex items-center gap-2 min-w-0">
                  {c.risk_level && (
                    <span
                      className={`text-xs font-mono px-1.5 py-0.5 rounded border flex-shrink-0 ${
                        RISK_STYLES[c.risk_level] ?? ""
                      }`}
                    >
                      {c.risk_level.toUpperCase()}
                    </span>
                  )}
                  <span className="font-mono text-xs text-gray-300 truncate">
                    {c.object_name}
                  </span>
                </div>
                <span className="text-gray-600 text-xs flex-shrink-0 ml-2">
                  {timeAgo(c.detected_at)}
                </span>
              </div>
            ))}
            {(changes ?? []).length === 0 && (
              <p className="text-gray-700 text-sm py-4 text-center">
                No changes detected yet
              </p>
            )}
          </div>
        </Section>

        {/* Notification log */}
        <Section title="Recent Alerts" count={(notifLog ?? []).length}>
          <div className="space-y-1">
            {(notifLog ?? []).map((n: any) => (
              <div
                key={n.id}
                className="flex items-center justify-between py-2 border-b border-gray-900/50 text-sm"
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                      n.status === "sent" ? "bg-[#00e87a]" : "bg-red-500"
                    }`}
                  />
                  <span className="text-gray-400 capitalize">{n.channel}</span>
                </div>
                <span className="text-gray-600 text-xs">{timeAgo(n.sent_at)}</span>
              </div>
            ))}
            {(notifLog ?? []).length === 0 && (
              <p className="text-gray-700 text-sm py-4 text-center">
                No alerts sent yet
              </p>
            )}
          </div>
        </Section>
      </div>
    </div>
  );
}

function Section({
  title,
  count,
  children,
}: {
  title: string;
  count: number;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-[#111] border border-gray-800 rounded-xl overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-800 flex items-center justify-between">
        <h2 className="font-semibold text-sm">{title}</h2>
        <span className="text-gray-600 text-xs">{count}</span>
      </div>
      <div className="px-5 py-3">{children}</div>
    </div>
  );
}
