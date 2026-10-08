"use client";

import { useEffect, useState } from "react";

const SCENES = [
  "1 · Connect",
  "2 · Migration",
  "3 · Detect",
  "4 · Analyze",
  "5 · Alert",
  "6 · Before merge",
  "7 · Dashboard",
];
const SCENE_MS = 6200;
const STEP_MS = 650;

// ── helpers ────────────────────────────────────────────────────────────────

/** Fades a block in once the scene tick reaches `at`. */
function Reveal({
  tick,
  at,
  className = "",
  children,
}: {
  tick: number;
  at: number;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={`transition-all duration-500 ${
        tick >= at ? "opacity-100 translate-y-0" : "opacity-0 translate-y-1"
      } ${className}`}
    >
      {children}
    </div>
  );
}

/** Types text out character by character once mounted. */
function Typed({ text, className = "" }: { text: string; className?: string }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    if (n >= text.length) return;
    const t = setTimeout(() => setN(n + 1), 22);
    return () => clearTimeout(t);
  }, [n, text]);
  return (
    <span className={className}>
      {text.slice(0, n)}
      {n < text.length && <span className="text-[#00e87a] animate-pulse">▍</span>}
    </span>
  );
}

function Window({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-[#0d0d0d] rounded-xl border border-white/[0.06] overflow-hidden">
      <div className="flex items-center gap-1.5 px-4 py-2.5 border-b border-white/[0.06]">
        <span className="w-2.5 h-2.5 rounded-full bg-[#e83232]" />
        <span className="w-2.5 h-2.5 rounded-full bg-[#ffb200]" />
        <span className="w-2.5 h-2.5 rounded-full bg-[#00e87a]" />
        <span className="font-mono text-[10px] text-white/22 ml-2">{title}</span>
      </div>
      <div className="p-4 font-mono text-[12px] leading-[1.9]">{children}</div>
    </div>
  );
}

const RISK_STYLE = {
  CRITICAL: "text-[#e83232] border-[#e83232]/35 bg-[#e83232]/[0.08]",
  HIGH: "text-[#e83232] border-[#e83232]/35 bg-[#e83232]/[0.08]",
  MEDIUM: "text-[#ffb200] border-[#ffb200]/35 bg-[#ffb200]/[0.08]",
  LOW: "text-[#00e87a] border-[#00e87a]/20 bg-[#00e87a]/[0.08]",
  OK: "text-[#00e87a] border-[#00e87a]/20 bg-[#00e87a]/[0.08]",
} as const;

function Pill({ kind, children }: { kind: keyof typeof RISK_STYLE; children: React.ReactNode }) {
  return (
    <span className={`inline-block font-mono text-[10px] px-2.5 py-0.5 rounded-full border ${RISK_STYLE[kind]}`}>
      {children}
    </span>
  );
}

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-[#141414] border border-white/[0.06] rounded-xl px-4 py-3 ${className}`}>
      {children}
    </div>
  );
}

// ── scenes ─────────────────────────────────────────────────────────────────

function Connect({ tick }: { tick: number }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5">
      <Window title="/onboarding">
        <Reveal tick={tick} at={0}><span className="text-[#00e87a]">Obi</span> <span className="text-white/22">›</span> Which database are we connecting?</Reveal>
        <Reveal tick={tick} at={1}><span className="text-[#4a9eff]">you</span> <span className="text-white/22">›</span> Supabase</Reveal>
        <Reveal tick={tick} at={2}><span className="text-[#00e87a]">Obi</span> <span className="text-white/22">›</span> Paste your connection string.</Reveal>
        <div className="min-h-[1.9em] break-all">
          {tick >= 3 && (
            <>
              <span className="text-[#4a9eff]">you</span> <span className="text-white/22">›</span>{" "}
              <Typed text="postgresql://postgres:••••@db.acme.supabase.co:5432/postgres" className="text-white/70" />
            </>
          )}
        </div>
      </Window>
      <div className="flex flex-col gap-2.5">
        {[
          ["Reachability", "connected"],
          ["Detection mode", "real-time · port 5432"],
          ["DDL event trigger", "installed"],
          ["Scout", "watching"],
        ].map(([label, status], i) => (
          <Reveal key={label} tick={tick} at={5 + i}>
            <Card className="flex items-center justify-between">
              <span className="font-mono text-[11px] text-white/55">{label}</span>
              <Pill kind="OK">{status}</Pill>
            </Card>
          </Reveal>
        ))}
      </div>
    </div>
  );
}

function Migration({ tick }: { tick: number }) {
  return (
    <Window title="migrations/003_cleanup.sql">
      <div className="min-h-[200px]">
        <Reveal tick={tick} at={0} className="text-white/30">-- cleanup: remove unused indexes</Reveal>
        <div className="min-h-[1.9em]">
          {tick >= 1 && <Typed text="DROP INDEX CONCURRENTLY idx_sessions_token;" className="text-[#e85858]" />}
        </div>
        <Reveal tick={tick} at={3} className="text-white/30">-- and tidy the users table</Reveal>
        <div className="min-h-[1.9em]">
          {tick >= 4 && <Typed text="ALTER TABLE users DROP COLUMN legacy_email;" className="text-[#e85858]" />}
        </div>
        <Reveal tick={tick} at={6} className="text-white/30">COMMIT;</Reveal>
      </div>
    </Window>
  );
}

function Detect({ tick }: { tick: number }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5">
      <Window title="scout · prod-postgres">
        <Reveal tick={tick} at={0}><span className="text-white/25">[03:47:22]</span> <span className="text-[#00e87a]">pg_notify</span> DDL_EVENT received</Reveal>
        <Reveal tick={tick} at={1}><span className="text-white/25">[03:47:22]</span> snapshot before <span className="text-[#00e87a]">✓</span></Reveal>
        <Reveal tick={tick} at={2}><span className="text-white/25">[03:47:22]</span> snapshot after <span className="text-[#00e87a]">✓</span></Reveal>
        <Reveal tick={tick} at={3}><span className="text-white/25">[03:47:23]</span> diff → <span className="text-[#c8bfff]">2 changes</span></Reveal>
        <Reveal tick={tick} at={4}><span className="text-white/25">[03:47:23]</span> heartbeat <span className="text-[#00e87a]">✓</span></Reveal>
      </Window>
      <Window title="diff · structure only, no row data">
        <Reveal tick={tick} at={2}><span className="text-[#e83232]">- INDEX</span>  idx_sessions_token</Reveal>
        <Reveal tick={tick} at={3}><span className="text-[#e83232]">- COLUMN</span> users.legacy_email <span className="text-white/25">text</span></Reveal>
        <Reveal tick={tick} at={4} className="text-white/25">detected in under a second</Reveal>
      </Window>
    </div>
  );
}

function Analyze({ tick }: { tick: number }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5">
      <div className="flex flex-col gap-2.5">
        <Reveal tick={tick} at={0}>
          <Card className="flex items-center justify-between">
            <span className="font-mono text-[11px] text-white/70">users.legacy_email dropped</span>
            <Pill kind="HIGH">HIGH</Pill>
          </Card>
        </Reveal>
        <Reveal tick={tick} at={1}>
          <Card className="flex items-center justify-between">
            <span className="font-mono text-[11px] text-white/70">idx_sessions_token dropped</span>
            <Pill kind="MEDIUM">MEDIUM</Pill>
          </Card>
        </Reveal>
      </div>
      <Card className="py-4">
        <p className="font-mono text-[10px] text-white/25 mb-1.5">IMPACT</p>
        <div className="text-[13px] text-white/55 leading-[1.6] min-h-[84px]">
          {tick >= 2 && (
            <Typed text="The legacy_email column was dropped from users. 2 queries in api-gateway still select it and will start failing." />
          )}
        </div>
        <p className="font-mono text-[10px] text-white/25 mt-3 mb-1">AFFECTED</p>
        <Reveal tick={tick} at={5} className="font-mono text-[11px]"><span className="text-[#c8bfff]">api-gateway</span>/auth.ts:84 <span className="text-white/30">SELECT legacy_email</span></Reveal>
        <Reveal tick={tick} at={6} className="font-mono text-[11px]"><span className="text-[#c8bfff]">api-gateway</span>/billing.ts:41 <span className="text-white/30">WHERE legacy_email</span></Reveal>
        <p className="font-mono text-[10px] text-white/25 mt-3 mb-1.5">NEXT ACTION</p>
        <Reveal tick={tick} at={7}><Pill kind="CRITICAL">Do not deploy until verified</Pill></Reveal>
      </Card>
    </div>
  );
}

function Alert({ tick }: { tick: number }) {
  const channels = [
    ["Custom webhook", "HMAC signed"],
    ["Slack", "HIGH + CRITICAL"],
    ["PagerDuty", "CRITICAL only"],
    ["Email", "sent"],
  ];
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5">
      <div className="flex flex-col gap-2.5">
        {channels.map(([name, note], i) => (
          <Card
            key={name}
            className={`flex items-center gap-3 transition-all duration-500 ${
              tick >= i ? "opacity-100 !border-[#00e87a]/20" : "opacity-35"
            }`}
          >
            <span className="font-mono text-[11px] text-white/25 w-4">{i + 1}</span>
            <span className="text-[14px] text-white/80">{name}</span>
            <span className={`ml-auto font-mono text-[10px] ${tick >= i ? "text-[#00e87a]" : "text-white/25"}`}>{note}</span>
          </Card>
        ))}
        <p className="text-[12px] text-white/35">If one channel is down, the others still go out.</p>
      </div>
      <Reveal tick={tick} at={1}>
        <div className="bg-[#1a1d21] border border-white/[0.08] rounded-xl overflow-hidden">
          <div className="px-3 py-2 border-b border-white/[0.06] font-mono text-[9px] text-white/25 uppercase tracking-[0.4px]">
            Slack · #db-alerts
          </div>
          <div className="px-3 py-3 border-l-4 border-[#e85858]">
            <p className="text-[12px] font-semibold text-white mb-1">⚠ HIGH Risk — Schema Change Detected</p>
            <p className="text-[11px] text-white/45 mb-2">prod-postgres · users · column dropped</p>
            <p className="text-[12px] text-white/60 leading-[1.5] mb-2">
              <span className="text-[#e85858] font-semibold">Do not deploy.</span>{" "}
              2 queries in api-gateway still select users.legacy_email.
            </p>
            <span className="inline-block font-mono text-[9px] text-[#00e87a] bg-[rgba(0,232,122,0.08)] border border-[rgba(0,232,122,0.2)] px-2 py-0.5 rounded">
              View in Dashboard →
            </span>
          </div>
        </div>
      </Reveal>
    </div>
  );
}

function BeforeMerge({ tick }: { tick: number }) {
  return (
    <div className="flex flex-col gap-2.5">
      <Card className="flex items-center justify-between">
        <div>
          <p className="text-[14px] font-medium text-white">Cleanup unused indexes and legacy columns</p>
          <p className="font-mono text-[10px] text-white/25">#128 · migrations/003_cleanup.sql</p>
        </div>
        <span className="font-mono text-[10px] text-[#4a9eff] border border-[#4a9eff]/35 bg-[#4a9eff]/[0.08] px-2.5 py-0.5 rounded-full">
          coming soon
        </span>
      </Card>
      <Reveal tick={tick} at={0}>
        <Card className="flex items-center gap-3">
          <span className="w-[18px] h-[18px] rounded-full bg-[#00e87a] text-black text-[11px] font-bold grid place-items-center">✓</span>
          <div>
            <p className="text-[13px] font-medium text-white">Tests</p>
            <p className="text-[12px] text-white/45">90 passed</p>
          </div>
        </Card>
      </Reveal>
      <Reveal tick={tick} at={1}>
        <Card className="flex items-start gap-3 !border-[#e83232]/35 !bg-[#e83232]/[0.05]">
          <span className="w-[18px] h-[18px] mt-0.5 rounded-full bg-[#e83232] text-white text-[11px] font-bold grid place-items-center flex-none">✕</span>
          <div className="flex-1">
            <div className="flex items-center justify-between">
              <p className="text-[13px] font-medium text-white">SchemaZero · schema check</p>
              <Pill kind="HIGH">HIGH</Pill>
            </div>
            <p className="text-[12px] text-white/50 mt-1">
              migrations/003_cleanup.sql:4 drops <span className="font-mono text-[#c8bfff]">users.legacy_email</span>
            </p>
            <Reveal tick={tick} at={2} className="font-mono text-[11px] mt-1.5"><span className="text-[#e83232]">✕</span> <span className="text-[#c8bfff]">api-gateway</span>/auth.ts:84 still selects it</Reveal>
            <Reveal tick={tick} at={3} className="font-mono text-[11px]"><span className="text-[#e83232]">✕</span> <span className="text-[#c8bfff]">api-gateway</span>/billing.ts:41 still filters on it</Reveal>
          </div>
        </Card>
      </Reveal>
      <Reveal tick={tick} at={4}>
        <div className="px-4 py-2.5 rounded-lg border border-[#e83232]/35 text-[#e83232] text-[13px] font-semibold bg-[#141414]">
          🚫 Merging is blocked — fix the failing check
        </div>
      </Reveal>
    </div>
  );
}

function Dashboard({ tick }: { tick: number }) {
  const feed: [keyof typeof RISK_STYLE, string, string][] = [
    ["HIGH", "users.legacy_email dropped", "just now"],
    ["MEDIUM", "idx_sessions_token dropped", "just now"],
    ["LOW", "orders.note added (nullable)", "2h ago"],
    ["LOW", "idx_orders_created created", "yesterday"],
  ];
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="flex gap-2">
          <Pill kind="OK">prod-postgres · watching</Pill>
          <Pill kind="OK">staging · watching</Pill>
        </div>
        <span className="font-mono text-[10px] text-white/25">trial · 11 days left</span>
      </div>
      <div className="flex flex-col gap-2.5">
        {feed.map(([risk, label, when], i) => (
          <Reveal key={label} tick={tick} at={i}>
            <Card className="flex items-center gap-3">
              <Pill kind={risk}>{risk}</Pill>
              <span className="text-[13px] text-white/80">{label}</span>
              <span className="ml-auto font-mono text-[10px] text-white/25">{when}</span>
            </Card>
          </Reveal>
        ))}
      </div>
    </div>
  );
}

const CAPTIONS = [
  "Obi walks you through connecting a database. Paste a connection string, it checks it works, Scout starts watching.",
  "An engineer writes a cleanup migration. One line looks harmless.",
  "Scout catches the change the moment it runs, with a before/after snapshot. No row data is ever read.",
  "Agent Zero scores the risk and traces what depends on it, in plain English.",
  "Alerts fire in order, so the right people know before anyone ships.",
  "The same check on the pull request shows the error before the merge, not after.",
  "Everything lands in the dashboard. New changes slide in live.",
];

const SCENE_VIEWS = [Connect, Migration, Detect, Analyze, Alert, BeforeMerge, Dashboard];

// ── main ───────────────────────────────────────────────────────────────────

export default function LiveDemo() {
  const [scene, setScene] = useState(0);
  const [tick, setTick] = useState(0);
  const [playing, setPlaying] = useState(true);

  // step counter inside the current scene
  useEffect(() => {
    const t = setInterval(() => setTick((n) => n + 1), STEP_MS);
    return () => clearInterval(t);
  }, [scene]);

  // auto-advance
  useEffect(() => {
    if (!playing) return;
    const t = setTimeout(() => go((scene + 1) % SCENES.length), SCENE_MS);
    return () => clearTimeout(t);
  }, [scene, playing]);

  function go(i: number) {
    setTick(0);
    setScene(i);
  }

  const View = SCENE_VIEWS[scene];

  return (
    <section id="demo" className="scroll-mt-16 bg-[#0a0a0a] border-t border-white/[0.06] px-5 sm:px-10 py-20">
      <div className="max-w-[1100px] mx-auto">

        <div className="mb-8">
          <p className="font-mono text-[11px] text-white/22 uppercase tracking-[0.8px] mb-3">
            Live demo
          </p>
          <h2 className="text-3xl font-semibold text-white tracking-[-1px] leading-[1.15] mb-4">
            Watch a bad migration get caught.<br />
            <span className="text-[#00e87a]">Before it ships.</span>
          </h2>
          <p className="text-base text-white/45 max-w-[560px] leading-[1.65]">
            One walkthrough of everything SchemaZero does, from connecting a database to the
            alert landing in Slack. Click any step to jump to it.
          </p>
        </div>

        <div className="flex flex-wrap gap-2 mb-3">
          {SCENES.map((label, i) => (
            <button
              key={label}
              onClick={() => go(i)}
              className={`font-mono text-[11px] px-3 py-1.5 rounded-full border transition-colors ${
                i === scene
                  ? "bg-[rgba(0,232,122,0.08)] text-[#00e87a] border-[rgba(0,232,122,0.2)]"
                  : i < scene
                  ? "text-[#00e87a] border-[rgba(0,232,122,0.2)]"
                  : "text-white/45 border-white/[0.1] hover:text-white"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="h-[2px] bg-white/[0.06] rounded overflow-hidden mb-4">
          <div
            className="h-full bg-[#00e87a] transition-all duration-500"
            style={{ width: `${((scene + 1) / SCENES.length) * 100}%` }}
          />
        </div>

        <div className="bg-[#111111] border border-white/[0.06] rounded-2xl p-5 sm:p-6 min-h-[430px]">
          <p className="text-[13px] text-white/45 mb-4">{CAPTIONS[scene]}</p>
          <View key={scene} tick={tick} />
        </div>

        <div className="flex gap-2.5 mt-4">
          <button
            onClick={() => setPlaying((p) => !p)}
            className="px-5 py-2 bg-[#00e87a] text-black text-sm font-semibold rounded-lg hover:opacity-85 transition-opacity"
          >
            {playing ? "Pause" : "Play"}
          </button>
          <button
            onClick={() => {
              setPlaying(true);
              go(0);
            }}
            className="px-5 py-2 border border-white/[0.1] text-white text-sm font-semibold rounded-lg hover:border-white/22 transition-colors"
          >
            Restart
          </button>
        </div>

      </div>
    </section>
  );
}
