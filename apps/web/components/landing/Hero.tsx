"use client";

import { useEffect, useState } from "react";
import type { Tab } from "@/lib/types";

const RISK_STYLES: Record<string, string> = {
  LOW: "bg-[rgba(0,232,122,0.08)] text-[rgba(0,232,122,0.65)]",
  MEDIUM: "bg-[rgba(255,178,0,0.1)] text-[rgba(255,178,0,0.8)]",
  HIGH: "bg-[rgba(232,50,50,0.12)] text-[#e85858]",
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

const TOTAL_STEPS = 7;
const STEP_MS = 950;
const HOLD_MS = 3500;

function show(step: number, threshold: number) {
  return step >= threshold
    ? "opacity-100 translate-y-0"
    : "opacity-0 translate-y-1";
}

function EngineDemoPanel() {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const t = setTimeout(
      () => setStep((s) => (s >= TOTAL_STEPS ? 0 : s + 1)),
      step >= TOTAL_STEPS ? HOLD_MS : STEP_MS
    );
    return () => clearTimeout(t);
  }, [step]);

  return (
    <div className="bg-[#0d0d0d] flex flex-col overflow-hidden h-full">

      {/* Title bar */}
      <div className="flex items-center gap-1.5 px-5 py-3 border-b border-white/[0.06] flex-shrink-0">
        <span className="w-2.5 h-2.5 rounded-full bg-[#e83232]" />
        <span className="w-2.5 h-2.5 rounded-full bg-[#ffb200]" />
        <span className="w-2.5 h-2.5 rounded-full bg-[#00e87a]" />
        <span className="font-mono text-[10px] text-white/22 ml-2">
          agent-engine · live
        </span>
        <span className="ml-auto flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-[#00e87a] animate-pulse" />
          <span className="font-mono text-[9px] text-white/25">prod-postgres</span>
        </span>
      </div>

      {/* Code pane */}
      <div className="flex-1 px-5 py-5 font-mono text-[11px] leading-[1.8] overflow-hidden">

        {/* Scout header */}
        <div className={`transition-all duration-500 ${show(step, 1)}`}>
          <span className="text-white/22">{"// "}</span>
          <span className="text-[#c8bfff]">scout.ts</span>
          <span className="text-white/22"> — watching prod-postgres</span>
        </div>

        {/* Event received */}
        <div className={`transition-all duration-500 ${show(step, 2)}`}>
          <span className="text-white/25">[03:47:22] </span>
          <span className="text-[#00e87a]">pg_notify</span>
          <span className="text-white/45"> received DDL_EVENT</span>
        </div>
        <div className={`transition-all duration-500 mt-1 mb-2 bg-black/30 border-l-2 border-white/[0.08] rounded-r px-3 py-2 ${show(step, 2)}`}>
          <div className="text-white/25">{"{"}</div>
          <div className="pl-3">
            <span className="text-[#c8bfff]">event</span>
            <span className="text-white/25">: </span>
            <span className="text-[#ffb200]">"DROP INDEX"</span>
            <span className="text-white/25">,</span>
          </div>
          <div className="pl-3">
            <span className="text-[#c8bfff]">index</span>
            <span className="text-white/25">: </span>
            <span className="text-[#ffb200]">"idx_sessions_token"</span>
            <span className="text-white/25">,</span>
          </div>
          <div className="pl-3">
            <span className="text-[#c8bfff]">table</span>
            <span className="text-white/25">: </span>
            <span className="text-[#ffb200]">"sessions"</span>
          </div>
          <div className="text-white/25">{"}"}</div>
        </div>

        {/* Agent Zero header */}
        <div className={`transition-all duration-500 mt-3 ${show(step, 3)}`}>
          <span className="text-white/22">{"// "}</span>
          <span className="text-[#c8bfff]">agent-zero.ts</span>
          <span className="text-white/22"> — analyzing impact</span>
        </div>

        {/* Scan */}
        <div className={`transition-all duration-500 ${show(step, 3)}`}>
          <span className="text-white/35">→ </span>
          <span className="text-white/50">scanning query catalog</span>
          <span className="text-white/25">...</span>
        </div>

        {/* Results */}
        <div className={`transition-all duration-500 ${show(step, 4)}`}>
          <span className="text-white/35">→ </span>
          <span className="text-[#00e87a]">2 queries</span>
          <span className="text-white/50"> in api-gateway reference this index</span>
        </div>
        <div className={`transition-all duration-500 ${show(step, 4)}`}>
          <span className="text-white/35">→ </span>
          <span className="text-white/50">removal causes full sequential scans</span>
        </div>

        {/* Risk */}
        <div className={`transition-all duration-500 ${show(step, 5)}`}>
          <span className="text-white/35">→ </span>
          <span className="text-white/50">risk score: </span>
          <span className="text-[#e85858] font-bold">HIGH</span>
        </div>

        {/* Fire */}
        <div className={`transition-all duration-500 ${show(step, 6)}`}>
          <span className="text-white/35">→ </span>
          <span className="text-white/50">firing alert </span>
          <span className="text-white/25">{"{ "}</span>
          <span className="text-[#c8bfff]">channel</span>
          <span className="text-white/25">{": "}</span>
          <span className="text-[#ffb200]">"slack"</span>
          <span className="text-white/25">{" }"}</span>
        </div>

      </div>

      {/* Result pane */}
      <div className={`flex-shrink-0 border-t border-white/[0.06] transition-all duration-700 ${step >= 7 ? "opacity-100" : "opacity-0"}`}>
        <div className="px-4 py-2 border-b border-white/[0.04]">
          <span className="font-mono text-[9px] text-white/22 uppercase tracking-[0.6px]">Alert fired · Slack</span>
        </div>
        <div className="p-4">
          <div className="bg-[#141414] border border-[rgba(232,88,88,0.2)] rounded-xl px-4 py-3">
            <div className="flex items-center gap-2 mb-2">
              <span className={`font-mono text-[9px] font-bold px-2 py-0.5 rounded uppercase ${RISK_STYLES.HIGH}`}>
                HIGH
              </span>
              <span className="font-mono text-[10px] text-white/25">DROPPED</span>
              <span className="font-mono text-[11px] text-white/60">sessions</span>
            </div>
            <p className="font-mono text-[10px] text-white/35 mb-1.5">idx_sessions_token</p>
            <p className="text-[11px] text-white/50 leading-[1.55]">
              <span className="text-[#e85858] font-semibold">Do not deploy.</span>{" "}
              This index covers 2 frequent queries in{" "}
              <span className="font-mono text-white/65">api-gateway</span>.
              Expect full sequential scans until rebuilt.
            </p>
          </div>
        </div>
      </div>

    </div>
  );
}

interface HeroProps {
  onTabChange: (tab: Tab) => void;
}

export default function Hero({ onTabChange }: HeroProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 min-h-[calc(100vh-64px)]">
      {/* Left: copy */}
      <div className="flex flex-col justify-center px-5 sm:px-10 py-12 lg:py-16 lg:border-r border-white/[0.06]">
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
          affects, why it matters, and what to review, before it becomes a
          production incident.
        </p>

        <p className="text-[13px] text-[#00e87a] opacity-75 mb-3 max-w-[380px]">
          Connects to your database and reads your schema automatically. No
          setup, no declarations, no configuration.
        </p>

        <p className="text-[13px] text-white/25 mb-5 max-w-[380px]">
          Alerts land in your own <strong className="text-white/45 font-medium">custom webhook</strong>,{" "}
          <strong className="text-white/45 font-medium">Slack</strong>,{" "}
          <strong className="text-white/45 font-medium">PagerDuty</strong>, or{" "}
          <strong className="text-white/45 font-medium">email</strong>, where your team already works.
        </p>

        <div className="border-l-2 border-[#00e87a] pl-3 mb-9">
          <p className="text-[13px] text-white/60">
            <strong>SchemaZero never sees your data. It only sees your structure.</strong>
          </p>
        </div>

        <div className="flex gap-3 items-center flex-wrap mb-10">
          <a
            href="#waitlist"
            className="px-6 py-3 bg-[#00e87a] text-black text-sm font-semibold rounded-lg hover:opacity-85 transition-opacity"
          >
            Join waitlist
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

      {/* Right: engine demo */}
      <EngineDemoPanel />
    </div>
  );
}
