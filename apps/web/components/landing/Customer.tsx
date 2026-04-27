const USE_CASES = [
  {
    role: "Backend Engineer",
    scenario: "Runs a migration before standup. SchemaZero fires a Slack briefing: which queries are affected, what the risk level is, and whether it's safe to deploy — before they touch production.",
    tag: "Daily user",
  },
  {
    role: "Engineering Manager",
    scenario: "Gets a PagerDuty alert for every HIGH or CRITICAL schema change. Knows within seconds whether to hold a deploy, not after a 2am incident.",
    tag: "Buyer",
  },
  {
    role: "Platform / DBA",
    scenario: "Owns 8 databases across three engines. One dashboard. Every DDL event caught, scored, and explained — without writing a single monitor or query.",
    tag: "Power user",
  },
];

export default function Customer() {
  return (
    <section className="bg-[#0a0a0a] border-t border-white/[0.06] px-10 py-20">
      <div className="max-w-[960px] mx-auto">

        <div className="mb-12">
          <p className="font-mono text-[11px] text-white/22 uppercase tracking-[0.8px] mb-3">
            Who it's for
          </p>
          <h2 className="text-3xl font-semibold text-white tracking-[-1px] leading-[1.15] mb-4">
            Engineering teams that ship<br />
            <span className="text-[#00e87a]">fast and can't afford surprises.</span>
          </h2>
          <p className="text-base text-white/45 max-w-[520px] leading-[1.65]">
            The buyer is an engineering manager or CTO at a startup or scale-up running
            5–200 engineers. The user is the backend engineer or platform engineer who
            touches the database. They pay because one prevented incident costs more than
            a year of SchemaZero.
          </p>
        </div>

        {/* Use case cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-12">
          {USE_CASES.map((u) => (
            <div
              key={u.role}
              className="bg-[#111] border border-white/[0.06] rounded-xl p-6 hover:border-[rgba(0,232,122,0.15)] transition-colors"
            >
              <div className="flex items-center justify-between mb-4">
                <span className="text-white font-medium text-[14px]">{u.role}</span>
                <span className="font-mono text-[9px] text-[#00e87a] bg-[rgba(0,232,122,0.08)] border border-[rgba(0,232,122,0.2)] px-2 py-0.5 rounded-full">
                  {u.tag}
                </span>
              </div>
              <p className="text-[13px] text-white/40 leading-[1.65]">{u.scenario}</p>
            </div>
          ))}
        </div>

        {/* Why they pay */}
        <div className="bg-[#111] border border-white/[0.06] rounded-2xl p-7 grid grid-cols-1 sm:grid-cols-3 gap-6">
          {[
            {
              label: "Why they try it",
              copy: "They've had at least one schema-related production incident. They remember the postmortem.",
            },
            {
              label: "Why they keep it",
              copy: "The product catches things they wouldn't have caught. The first time that happens, it pays for itself.",
            },
            {
              label: "Why they upgrade",
              copy: "The team grows. More engineers touching the database means more risk. They move from Solo to Teams.",
            },
          ].map((item) => (
            <div key={item.label}>
              <p className="font-mono text-[11px] text-[#00e87a] mb-2">{item.label}</p>
              <p className="text-[13px] text-white/45 leading-[1.65]">{item.copy}</p>
            </div>
          ))}
        </div>

      </div>
    </section>
  );
}
