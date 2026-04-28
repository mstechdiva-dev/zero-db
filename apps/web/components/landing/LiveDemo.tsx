"use client";

import { useEffect, useState } from "react";

const TOTAL_STEPS = 11;
const STEP_MS = 780;
const HOLD_MS = 4500;

function cx(step: number, min: number) {
  return step >= min
    ? "opacity-100 translate-y-0"
    : "opacity-0 translate-y-1";
}

function Line({
  step,
  min,
  children,
  className = "",
}: {
  step: number;
  min: number;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`transition-all duration-500 font-mono text-[11.5px] leading-[1.85] ${cx(step, min)} ${className}`}
    >
      {children}
    </div>
  );
}

function TitleBar({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-1.5 px-5 py-3 border-b border-white/[0.06] flex-shrink-0">
      <span className="w-2.5 h-2.5 rounded-full bg-[#e83232]" />
      <span className="w-2.5 h-2.5 rounded-full bg-[#ffb200]" />
      <span className="w-2.5 h-2.5 rounded-full bg-[#00e87a]" />
      <span className="font-mono text-[10px] text-white/22 ml-2">{label}</span>
    </div>
  );
}

function UserWindow({ step }: { step: number }) {
  return (
    <div className="bg-[#0d0d0d] rounded-2xl border border-white/[0.06] overflow-hidden flex flex-col">
      <TitleBar label="migrations/003_cleanup.sql · psql" />
      <div className="p-5 flex-1">

        <Line step={step} min={1} className="text-white/30">
          $ psql postgresql://prod-postgres/app
        </Line>
        <Line step={step} min={1} className="text-white/18">
          psql (15.4) · SSL on · Type "help" for help.
        </Line>

        <div className={`h-4 transition-opacity duration-500 ${step >= 2 ? "opacity-100" : "opacity-0"}`} />

        <Line step={step} min={2} className="text-white/45">
          app={"#"} \i migrations/003_cleanup.sql
        </Line>

        <div className={`h-3 transition-opacity duration-500 ${step >= 3 ? "opacity-100" : "opacity-0"}`} />

        <Line step={step} min={3} className="text-white/22">
          {"-- cleanup: remove an index flagged for removal"}
        </Line>

        <Line step={step} min={4}>
          <span className="text-[#e85858]">DROP INDEX</span>
          <span className="text-white/45"> CONCURRENTLY </span>
          <span className="text-[#c8bfff]">idx_sessions_token</span>
          <span className="text-white/35">;</span>
        </Line>

        <div className={`h-3 transition-opacity duration-500 ${step >= 5 ? "opacity-100" : "opacity-0"}`} />

        <Line step={step} min={5} className="text-white/28">DROP INDEX</Line>
        <Line step={step} min={5} className="text-white/20">
          migrations/003_cleanup.sql complete
        </Line>
      </div>
    </div>
  );
}

function SchemaZeroWindow({ step }: { step: number }) {
  return (
    <div className="bg-[#0d0d0d] rounded-2xl border border-white/[0.06] overflow-hidden flex flex-col">
      <div className="flex items-center gap-1.5 px-5 py-3 border-b border-white/[0.06] flex-shrink-0">
        <span className="w-2.5 h-2.5 rounded-full bg-[#e83232]" />
        <span className="w-2.5 h-2.5 rounded-full bg-[#ffb200]" />
        <span className="w-2.5 h-2.5 rounded-full bg-[#00e87a]" />
        <span className="font-mono text-[10px] text-white/22 ml-2">
          schemazero · agent-engine
        </span>
        <span className="ml-auto flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-[#00e87a] animate-pulse" />
          <span className="font-mono text-[9px] text-white/25">watching</span>
        </span>
      </div>

      <div className="p-5 flex-1 flex flex-col gap-0.5 overflow-hidden">

        {/* Scout */}
        <Line step={step} min={6} className="text-[#c8bfff]">
          {"// "}scout.ts
        </Line>
        <Line step={step} min={6} className="text-white/30">
          [03:47:22]{" "}
          <span className="text-[#00e87a]">pg_notify</span>
          <span className="text-white/30"> DDL_EVENT received</span>
        </Line>

        <div className={`my-1.5 bg-black/30 border-l-2 border-white/[0.08] rounded-r px-3 py-1.5 transition-all duration-500 ${cx(step, 6)}`}>
          <div className="font-mono text-[11px] text-white/22">{"{"}</div>
          <div className="font-mono text-[11px] pl-3">
            <span className="text-[#c8bfff]">event</span>
            <span className="text-white/22">: </span>
            <span className="text-[#ffb200]">"DROP INDEX"</span>
            <span className="text-white/22">,</span>
          </div>
          <div className="font-mono text-[11px] pl-3">
            <span className="text-[#c8bfff]">index</span>
            <span className="text-white/22">: </span>
            <span className="text-[#ffb200]">"idx_sessions_token"</span>
            <span className="text-white/22">,</span>
          </div>
          <div className="font-mono text-[11px] pl-3">
            <span className="text-[#c8bfff]">table</span>
            <span className="text-white/22">: </span>
            <span className="text-[#ffb200]">"sessions"</span>
          </div>
          <div className="font-mono text-[11px] text-white/22">{"}"}</div>
        </div>

        {/* Risk scorer */}
        <div className={`mt-2 transition-all duration-500 ${cx(step, 7)}`}>
          <span className="font-mono text-[10px] text-white/22 uppercase tracking-[0.5px]">
            {"// "}risk-scorer.py
          </span>
        </div>
        <Line step={step} min={7} className="text-white/35">
          → change_type:{" "}
          <span className="text-white/55">index_dropped</span>
        </Line>
        <Line step={step} min={7} className="text-white/35">
          → table:{" "}
          <span className="text-white/55">sessions</span>
          <span className="text-white/22"> (high-traffic)</span>
        </Line>
        <Line step={step} min={7}>
          <span className="text-white/35">→ risk: </span>
          <span className="text-[#e85858] font-bold">HIGH</span>
        </Line>

        {/* Agent Zero */}
        <div className={`mt-2 transition-all duration-500 ${cx(step, 8)}`}>
          <span className="font-mono text-[10px] text-white/22 uppercase tracking-[0.5px]">
            {"// "}agent-zero.ts · analyzing
          </span>
        </div>
        <Line step={step} min={8} className="text-white/35">
          → scanning query catalog
          <span className="text-white/20">...</span>
        </Line>
        <Line step={step} min={9}>
          <span className="text-white/35">→ </span>
          <span className="text-[#00e87a]">2 queries</span>
          <span className="text-white/45"> in api-gateway reference this index</span>
        </Line>
        <Line step={step} min={9} className="text-white/35">
          → affected_services:{" "}
          <span className="text-white/55">api-gateway (auth flow)</span>
        </Line>
        <Line step={step} min={9} className="text-white/35">
          → without this index:{" "}
          <span className="text-[#e85858]">full table scans</span>
        </Line>
        <Line step={step} min={9} className="text-white/35">
          → next_action:{" "}
          <span className="text-white font-semibold">Do not deploy.</span>
        </Line>

        {/* Alert */}
        <Line step={step} min={10} className="mt-2 text-white/22 uppercase tracking-[0.5px]">
          {"// "}alert-dispatcher.py
        </Line>
        <Line step={step} min={10} className="text-white/35">
          → slack: HIGH alert fired{" "}
          <span className="text-[#00e87a]">✓</span>
        </Line>

        {/* Slack card */}
        <div
          className={`mt-3 bg-[#1a1d21] border border-white/[0.08] rounded-xl overflow-hidden transition-all duration-700 ${
            step >= 11 ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2"
          }`}
        >
          <div className="flex items-center gap-2 px-3 py-2 border-b border-white/[0.06]">
            <span className="font-mono text-[9px] text-white/25 uppercase tracking-[0.4px]">
              Slack · #incidents
            </span>
          </div>
          <div className="px-3 py-3 border-l-4 border-[#e85858]">
            <p className="text-[11px] font-semibold text-white mb-1">
              ⚠ HIGH Risk — Schema Change Detected
            </p>
            <p className="text-[10px] text-white/45 mb-2">
              prod-postgres · sessions · index dropped
            </p>
            <p className="text-[11px] text-white/60 leading-[1.5] mb-2">
              <span className="text-[#e85858] font-semibold">Do not deploy.</span>{" "}
              idx_sessions_token covers 2 frequent queries in api-gateway.
              Expect full sequential scans until rebuilt.
            </p>
            <span className="inline-block font-mono text-[9px] text-[#00e87a] bg-[rgba(0,232,122,0.08)] border border-[rgba(0,232,122,0.2)] px-2 py-0.5 rounded">
              View in Dashboard →
            </span>
          </div>
        </div>

      </div>
    </div>
  );
}

export default function LiveDemo() {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const t = setTimeout(
      () => setStep((s) => (s >= TOTAL_STEPS ? 0 : s + 1)),
      step >= TOTAL_STEPS ? HOLD_MS : STEP_MS
    );
    return () => clearTimeout(t);
  }, [step]);

  return (
    <section className="bg-[#0a0a0a] border-t border-white/[0.06] px-5 sm:px-10 py-20">
      <div className="max-w-[1100px] mx-auto">

        <div className="mb-10">
          <p className="font-mono text-[11px] text-white/22 uppercase tracking-[0.8px] mb-3">
            Live workflow
          </p>
          <h2 className="text-3xl font-semibold text-white tracking-[-1px] leading-[1.15] mb-4">
            Migration runs. SchemaZero responds.<br />
            <span className="text-[#00e87a]">Before anyone is paged.</span>
          </h2>
          <p className="text-base text-white/45 max-w-[520px] leading-[1.65]">
            Left: an engineer drops an index in a migration script.
            Right: Scout catches it, Agent Zero traces the impact to two queries in api-gateway,
            and the alert lands in Slack — with a plain-English "do not deploy" before anyone ships.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <UserWindow step={step} />
          <SchemaZeroWindow step={step} />
        </div>

      </div>
    </section>
  );
}
