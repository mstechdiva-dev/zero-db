const STEPS = [
  {
    number: "01",
    lit: true,
    title: "Connect any database",
    description:
      "Paste a read-only connection string. SchemaZero reads your entire schema automatically — every table, column, index, and constraint. Nothing to declare, nothing to configure. It just knows.",
    codeBlock: (
      <div className="bg-[#0d0d0d] border border-white/[0.06] rounded-lg px-4 py-3 font-mono text-[11px] leading-[1.8] text-white/45 mt-1">
        <span className="text-[#00e87a]">GRANT</span> SELECT{" "}
        <span className="text-white/22">ON ALL TABLES IN SCHEMA</span> public{" "}
        <span className="text-white/22">TO</span> schemazero_reader;
      </div>
    ),
    note: (
      <div className="text-[13px] text-white/22 bg-[#111] border border-white/[0.06] rounded-lg px-4 py-3 leading-[1.55] mt-3">
        <strong className="text-white/45">Postgres / Supabase / Neon / CockroachDB:</strong>{" "}
        real-time via pg_notify &nbsp;·&nbsp;{" "}
        <strong className="text-white/45">MySQL:</strong> polling every 60s &nbsp;·&nbsp;{" "}
        <strong className="text-white/45">MongoDB:</strong> change streams &nbsp;·&nbsp;{" "}
        <strong className="text-white/45">Redis:</strong> keyspace notifications &nbsp;·&nbsp;{" "}
        <span className="opacity-50">SQL Server / Snowflake: coming soon</span>
      </div>
    ),
  },
  {
    number: "02",
    lit: true,
    title: "Scout watches continuously",
    description:
      "Scout runs always-on in the background. The moment a DDL event lands — migration script, manual ALTER TABLE, Supabase Studio, anything — Scout captures the before and after. Your team doesn't have to be watching.",
    codeBlock: null,
    note: null,
  },
  {
    number: "03",
    lit: true,
    title: "Agent Zero explains what it means",
    description:
      "This is where SchemaZero is different. Agent Zero doesn't just log the event — it reasons about it. What changed. What it touches. What your team needs to review before deploying. Risk scored, explained in plain English, no jargon.",
    codeBlock: (
      <div className="bg-[#0d0d0d] border border-white/[0.06] rounded-lg px-4 py-3 font-mono text-[11px] leading-[1.8] text-white/45 mt-1">
        <span className="text-[#e83232]">HIGH </span> idx_sessions_token dropped —{" "}
        <span className="text-white/22">2 queries in</span> api-gateway{" "}
        <span className="text-white/22">will full-scan. Review before deploying.</span>
        <br />
        <span className="text-[#00e87a]">LOW  </span> verified_at added nullable —{" "}
        <span className="text-white/22">additive change, safe to deploy</span>
        <br />
        <span className="text-[#ffb200]">MED  </span> status widened varchar(20)→(50) —{" "}
        <span className="text-white/22">check enum serializers in</span> orders-service
      </div>
    ),
    note: null,
  },
  {
    number: "04",
    lit: false,
    title: "Your team gets answers, not just alerts",
    description:
      "The notification your team receives isn't a ping — it's a briefing. What changed, what's at risk, and what to check. Slack, PagerDuty, email, or your own webhook. Enough context to make the call without opening a single log file.",
    codeBlock: null,
    note: null,
  },
];

const AGENTS = [
  {
    icon: "👁️",
    name: "Scout",
    runs: "Always-on background watcher",
    description:
      "Connects to your database and watches for schema changes using the right method for each engine. Updates a heartbeat every 30 seconds.",
  },
  {
    icon: "⚡",
    name: "Agent Zero",
    runs: "Event-triggered impact analyzer",
    description:
      "Triggered by Scout on every change. Analyzes impact, scores risk, fires alerts to Slack and PagerDuty, and writes plain-English summaries.",
  },
  {
    icon: "🧭",
    name: "Onboarding Agent",
    runs: "Database connection wizard",
    description:
      "Guides new users through connecting their first database. Validates the connection, confirms Scout is watching, and hands off on completion.",
  },
  {
    icon: "💬",
    name: "Support Agent",
    runs: "Landing page + in-app support",
    description:
      "Answers questions about SchemaZero, explains risk levels, helps configure alerts, and escalates issues that need a human.",
  },
  {
    icon: "📋",
    name: "Sales Agent",
    runs: "Teams + Enterprise qualifier",
    description:
      "Qualifies inbound Teams and Enterprise interest, collects context on team size and use case, and routes warm leads to the founder.",
  },
];

export default function HowItWorks() {
  return (
    <div className="py-20">
      <p className="font-mono text-[10px] uppercase tracking-[1.5px] text-[#00e87a] mb-3.5">
        How it works
      </p>
      <h2 className="text-[36px] font-semibold text-white leading-[1.15] tracking-[-1.2px] mb-3.5">
        From schema change to<br />clear answer in seconds
      </h2>
      <p className="text-base text-white/45 max-w-[560px] leading-[1.65] mb-14">
        Most tools stop at detection. SchemaZero goes further — it explains what changed,
        connects the dots to what it affects, and tells your team exactly what to review.
        No digging. No guessing.
      </p>

      {/* Steps */}
      <div className="flex flex-col">
        {STEPS.map((step, i) => (
          <div
            key={step.number}
            className={`grid gap-8 py-9 ${i < STEPS.length - 1 ? "border-b border-white/[0.06]" : ""}`}
            style={{ gridTemplateColumns: "80px 1fr" }}
          >
            <div
              className={`font-mono text-[30px] font-bold pt-1 ${
                step.lit ? "text-[#00e87a]" : "text-white/22"
              }`}
            >
              {step.number}
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white mb-2 tracking-[-0.3px]">
                {step.title}
              </h3>
              <p className="text-[15px] text-white/45 leading-[1.65] mb-4">
                {step.description}
              </p>
              {step.codeBlock}
              {step.note}
            </div>
          </div>
        ))}
      </div>

      {/* Agents */}
      <div className="mt-16">
        <p className="font-mono text-[10px] uppercase tracking-[1.5px] text-[#00e87a] mb-3.5">
          Agents
        </p>
        <h3 className="text-[28px] font-semibold text-white leading-[1.15] tracking-[-1.2px] mb-3">
          Five agents. One continuous loop.
        </h3>
        <p className="text-base text-white/45 max-w-[560px] leading-[1.65] mb-8">
          Each agent has a single job and does it well. Together they cover detection,
          analysis, onboarding, support, and sales — without you managing any of it.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {AGENTS.map((agent) => (
            <div
              key={agent.name}
              className="bg-[#111] border border-white/[0.06] rounded-xl p-6 hover:border-[rgba(0,232,122,0.2)] transition-colors"
            >
              <div className="text-[22px] mb-3"><span aria-hidden="true">{agent.icon}</span></div>
              <div className="text-[15px] font-semibold text-white mb-1">{agent.name}</div>
              <div className="font-mono text-[9px] uppercase tracking-[0.5px] text-white/22 mb-2.5">
                {agent.runs}
              </div>
              <p className="text-[13px] text-white/45 leading-[1.6]">{agent.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
