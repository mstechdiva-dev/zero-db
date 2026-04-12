"use client";

import type { Tab } from "@/lib/types";

const DEMO_EVENTS = [
  {
    id: "1",
    type: "ADDED",
    engine: "postgres",
    schema: "public",
    table: "users",
    risk: "LOW",
    time: "just now",
    diff: { prefix: "+", item: "column", name: "verified_at", detail: "timestamptz DEFAULT null", added: true },
    impact: (
      <>
        <strong>What to review:</strong> 3 queries in <code>auth-service</code> select all columns — they will now return this field. Check your serializers before deploying.
      </>
    ),
  },
  {
    id: "2",
    type: "MODIFIED",
    engine: "postgres",
    schema: "public",
    table: "orders",
    risk: "LOW",
    time: "2m ago",
    diff: { prefix: null, item: "status", name: "varchar(20)", detail: "→ varchar(50)", added: false },
    impact: (
      <>
        <strong>What to review:</strong> Column widened — no truncation possible, existing CHECK constraints remain valid. Safe to deploy.
      </>
    ),
  },
  {
    id: "3",
    type: "DROPPED",
    engine: "postgres",
    schema: "public",
    table: "sessions",
    risk: "HIGH",
    time: "7m ago",
    diff: { prefix: "-", item: "index", name: "idx_sessions_token", detail: "", added: false },
    impact: (
      <>
        <span className="text-red-400 font-semibold">Do not deploy.</span> This index covers 2 frequent queries in <code>api-gateway</code>. Expect full sequential scans until rebuilt. Rebuild the index before your next release.
      </>
    ),
  },
  {
    id: "4",
    type: "DROPPED",
    engine: "mongodb",
    schema: "events",
    table: "user_events",
    risk: "MEDIUM",
    time: "14m ago",
    diff: { prefix: "-", item: "index", name: "idx_user_events_session_id", detail: "", added: false },
    impact: (
      <>
        <strong>What to review:</strong> Aggregation pipeline in <code>analytics-service</code> will degrade without this index. Rebuild before traffic peaks or expect slow queries.
      </>
    ),
  },
];

const RISK_STYLES: Record<string, string> = {
  LOW: "bg-[rgba(0,232,122,0.08)] text-[rgba(0,232,122,0.65)]",
  MEDIUM: "bg-[rgba(255,178,0,0.1)] text-[rgba(255,178,0,0.8)]",
  HIGH: "bg-[rgba(232,50,50,0.12)] text-[#e85858]",
  CRITICAL: "bg-[rgba(232,50,50,0.2)] text-[#e83232] border border-[rgba(232,50,50,0.3)]",
};

const TYPE_STYLES: Record<string, string> = {
  ADDED: "bg-[rgba(0,232,122,0.12)] text-[#00e87a]",
  MODIFIED: "bg-[rgba(255,178,0,0.12)] text-[#ffb200]",
  DROPPED: "bg-[rgba(232,50,50,0.12)] text-[#e83232]",
};

const ENGINES = [
  { label: "Postgres", active: true },
  { label: "Supabase", active: true },
  { label: "Neon", active: true },
  { label: "MySQL", active: true },
  { label: "MongoDB", active: true },
  { label: "Redis", active: true },
  { label: "CockroachDB", active: true },
  { label: "SQL Server", active: false, soon: true },
  { label: "Snowflake", active: false, soon: true },
];

interface HeroProps {
  onTabChange: (tab: Tab) => void;
}

export default function Hero({ onTabChange }: HeroProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 min-h-[calc(100vh-64px)]">
      {/* Left: copy */}
      <div className="flex flex-col justify-center px-10 py-16 lg:border-r border-white/[0.06]">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 bg-[rgba(0,232,122,0.08)] border border-[rgba(0,232,122,0.2)] text-[#00e87a] font-mono text-[10px] tracking-[0.5px] px-3 py-1.5 rounded-full mb-7 w-fit">
          <span className="w-1.5 h-1.5 bg-[#00e87a] rounded-full animate-pulse" />
          Database schema intelligence
        </div>

        <h1 className="text-4xl lg:text-5xl font-semibold text-white leading-[1.12] tracking-[-1.8px] mb-5">
          Stop investigating.<br />
          <span className="text-[#00e87a]">Start knowing.</span>
        </h1>

        <p className="text-base text-white/50 leading-[1.65] max-w-[400px] mb-3">
          When your schema changes, SchemaZero tells your team exactly what it
          affects, why it matters, and what to review — before it becomes a
          production incident.
        </p>

        <p className="text-[13px] text-[#00e87a] opacity-75 mb-3 max-w-[380px]">
          Connects to your database and reads your schema automatically — no
          setup, no declarations, no configuration.
        </p>

        <p className="text-[13px] text-white/25 mb-5 max-w-[380px]">
          Alerts land in your own <strong className="text-white/45 font-medium">custom webhook</strong>,{" "}
          <strong className="text-white/45 font-medium">Slack</strong>,{" "}
          <strong className="text-white/45 font-medium">PagerDuty</strong>, or{" "}
          <strong className="text-white/45 font-medium">email</strong> — where your team already works.
        </p>

        <div className="border-l-2 border-[#00e87a] pl-3 mb-9">
          <p className="text-[13px] text-white/60">
            <strong>SchemaZero never sees your data. It only sees your structure.</strong>
          </p>
        </div>

        <div className="flex gap-3 items-center flex-wrap mb-10">
          <a
            href="/auth/signup"
            className="px-6 py-3 bg-[#00e87a] text-black text-sm font-semibold rounded-lg hover:opacity-85 transition-opacity"
          >
            Start free trial
          </a>
          <button
            type="button"
            onClick={() => onTabChange("how")}
            className="px-6 py-3 border border-white/10 text-white/50 text-sm font-medium rounded-lg hover:text-white hover:border-white/22 transition-colors"
          >
            How it works
          </button>
        </div>

        {/* Engines strip */}
        <div className="border-t border-white/[0.06] pt-7">
          <p className="font-mono text-[11px] text-white/22 uppercase tracking-[0.8px] mb-3.5">
            Supported databases
          </p>
          <div className="flex flex-wrap gap-2">
            {ENGINES.map((e) => (
              <span
                key={e.label}
                className={`inline-flex items-center gap-1.5 bg-[#111] border border-white/[0.06] rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors ${
                  e.active
                    ? "text-white/45 hover:border-[rgba(0,232,122,0.2)] hover:text-white"
                    : "text-white/20 cursor-default"
                }`}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${e.active ? "bg-[#00e87a] opacity-50" : "bg-white/20"}`}
                />
                {e.label}
                {e.soon && <span className="text-[9px] ml-0.5 opacity-60">soon</span>}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Right: demo panel */}
      <div className="bg-[#0d0d0d] flex flex-col overflow-hidden">
        {/* Title bar */}
        <div className="flex items-center gap-1.5 px-6 py-3.5 border-b border-white/[0.06]">
          <span className="w-2.5 h-2.5 rounded-full bg-[#e83232]" />
          <span className="w-2.5 h-2.5 rounded-full bg-[#ffb200]" />
          <span className="w-2.5 h-2.5 rounded-full bg-[#00e87a]" />
          <span className="font-mono text-[10px] text-white/22 ml-2 tracking-[0.3px]">
            change_events · live feed
          </span>
        </div>

        {/* DB bar */}
        <div className="flex items-center gap-2 px-6 py-2.5 border-b border-white/[0.06] font-mono text-[11px] text-white/25">
          <span className="w-1.5 h-1.5 rounded-full bg-[#00e87a] animate-pulse" />
          <span className="text-white/45">prod-postgres</span>
          <span className="mx-1.5 opacity-30">·</span>
          <span>Scout watching</span>
        </div>

        {/* Feed */}
        <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-3">
          {DEMO_EVENTS.map((event) => (
            <div
              key={event.id}
              className="bg-[#141414] border border-white/[0.06] rounded-xl px-4 py-3.5 hover:border-[rgba(0,232,122,0.2)] transition-colors"
            >
              {/* Meta row */}
              <div className="flex items-center gap-2 mb-2.5 flex-wrap">
                <span
                  className={`font-mono text-[9px] font-bold tracking-[0.5px] px-2 py-0.5 rounded uppercase ${TYPE_STYLES[event.type]}`}
                >
                  {event.type}
                </span>
                <span className="font-mono text-[11px] text-white/45">
                  {event.schema}.<strong className="text-white">{event.table}</strong>
                </span>
                <span className="text-[10px] text-white/25 bg-white/[0.04] px-1.5 py-0.5 rounded font-mono">
                  {event.engine}
                </span>
                <span className="font-mono text-[9px] text-white/22 ml-auto">{event.time}</span>
              </div>

              {/* Diff */}
              <div className="font-mono text-[11px] text-white/45 bg-black/30 rounded-md px-3 py-2 mb-2.5 border-l-2 border-white/[0.08]">
                {event.diff.prefix && (
                  <span className={event.diff.added ? "text-[#00e87a]" : "text-[#e83232]"}>
                    {event.diff.prefix}{" "}
                  </span>
                )}
                {event.diff.item}{" "}
                <em className="not-italic text-[#c8bfff]">{event.diff.name}</em>
                {event.diff.detail && <> {event.diff.detail}</>}
              </div>

              {/* Impact */}
              <div className="text-[12px] text-white/45 leading-[1.55]">
                {event.impact}
                <span
                  className={`inline-block font-mono text-[9px] font-bold tracking-[0.5px] px-2 py-0.5 rounded ml-2 ${RISK_STYLES[event.risk]}`}
                >
                  {event.risk}
                </span>
              </div>
            </div>
          ))}

          {/* Connect CTA */}
          <div className="text-center py-1.5">
            <a
              href="/auth/signup"
              className="inline-block text-[13px] text-white/45 border border-white/10 px-4 py-2 rounded-lg hover:text-white hover:border-white/22 transition-colors"
            >
              Connect your database to see live changes →
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
