const STAGES = [
  {
    label: "Wedge",
    title: "Schema change monitoring",
    copy: "Every engineering team running a database has this problem. We start with the teams that feel it most: startups on Postgres, Supabase, and Neon shipping fast with small teams and no dedicated DBA.",
    tag: "Now",
    tagColor: "text-[#00e87a] bg-[rgba(0,232,122,0.08)] border-[rgba(0,232,122,0.2)]",
  },
  {
    label: "Expansion",
    title: "Database observability",
    copy: "Schema changes are one signal. Query performance, index health, connection saturation, and migration risk are adjacent problems the same buyer already has. SchemaZero becomes the database layer of their observability stack.",
    tag: "Next",
    tagColor: "text-[#ffb200] bg-[rgba(255,178,0,0.08)] border-[rgba(255,178,0,0.2)]",
  },
  {
    label: "Platform",
    title: "Data reliability platform",
    copy: "Enterprise teams running multi-cloud, multi-engine stacks need a single pane of glass for database risk. SOC 2, HIPAA, and DoD compliance requirements make schema audit trails a procurement requirement — not just a convenience.",
    tag: "Vision",
    tagColor: "text-white/35 bg-white/[0.04] border-white/[0.08]",
  },
];

export default function Market() {
  return (
    <section className="bg-[#0a0a0a] border-t border-white/[0.06] px-5 sm:px-10 py-20">
      <div className="max-w-[960px] mx-auto">

        <div className="mb-12">
          <p className="font-mono text-[11px] text-white/22 uppercase tracking-[0.8px] mb-3">
            Market
          </p>
          <h2 className="text-3xl font-semibold text-white tracking-[-1px] leading-[1.15] mb-4">
            Every team with a database<br />
            <span className="text-[#00e87a]">has this problem.</span>
          </h2>
          <p className="text-base text-white/45 max-w-[520px] leading-[1.65]">
            The database tooling market is a $10B+ space growing alongside cloud infrastructure.
            SchemaZero enters through a specific, painful wedge — schema change risk — and
            expands from there.
          </p>
        </div>

        {/* Market size strip */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-12">
          {[
            { stat: "$10B+", label: "Database tooling market (2024)", sub: "Growing ~14% YoY" },
            { stat: "~4M", label: "Engineering teams running Postgres globally", sub: "Core initial audience" },
            { stat: "5–200", label: "Engineer headcount of target buyer", sub: "Too fast for manual review" },
          ].map((item) => (
            <div
              key={item.stat}
              className="bg-[#111] border border-white/[0.06] rounded-xl p-5"
            >
              <p className="text-[28px] font-semibold text-white tracking-[-1px] mb-1">{item.stat}</p>
              <p className="text-[12px] text-white/45 leading-[1.5] mb-1">{item.label}</p>
              <p className="font-mono text-[10px] text-white/22">{item.sub}</p>
            </div>
          ))}
        </div>

        {/* Expansion path */}
        <div className="space-y-3">
          {STAGES.map((stage, i) => (
            <div
              key={stage.label}
              className="bg-[#111] border border-white/[0.06] rounded-xl p-6 grid grid-cols-1 sm:grid-cols-[100px_1fr] gap-4 items-start hover:border-[rgba(0,232,122,0.1)] transition-colors"
            >
              <div className="flex flex-col gap-2">
                <span className="font-mono text-[10px] text-white/22 uppercase tracking-[0.6px]">
                  0{i + 1}
                </span>
                <span
                  className={`font-mono text-[9px] font-bold px-2 py-0.5 rounded-full border w-fit ${stage.tagColor}`}
                >
                  {stage.tag}
                </span>
              </div>
              <div>
                <p className="text-white font-medium text-[14px] mb-2">{stage.title}</p>
                <p className="text-[13px] text-white/40 leading-[1.65]">{stage.copy}</p>
              </div>
            </div>
          ))}
        </div>

      </div>
    </section>
  );
}
