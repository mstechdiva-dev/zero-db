export default function Value() {
  return (
    <section className="bg-[#0a0a0a] border-t border-white/[0.06] px-10 py-20">
      <div className="max-w-[960px] mx-auto">

        {/* Header */}
        <div className="mb-14">
          <p className="font-mono text-[11px] text-white/22 uppercase tracking-[0.8px] mb-3">
            Business value
          </p>
          <h2 className="text-3xl font-semibold text-white tracking-[-1px] leading-[1.15] mb-4">
            One bad schema change.<br />
            <span className="text-[#00e87a]">Hours of cleanup.</span>
          </h2>
          <p className="text-base text-white/45 max-w-[520px] leading-[1.65]">
            Schema incidents are silent until they aren't. Engineers spend 2–4 hours
            diagnosing what changed, what broke, and whether it's safe to roll back.
            SchemaZero closes that gap in seconds.
          </p>
        </div>

        {/* Before / After */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-14">
          {/* Before */}
          <div className="bg-[#111] border border-white/[0.06] rounded-2xl p-7">
            <p className="font-mono text-[10px] text-[#e85858] uppercase tracking-[0.8px] mb-5">
              Without SchemaZero
            </p>
            <ul className="space-y-4">
              {[
                "Schema changes silently in production",
                "Engineer gets paged — queries are slow",
                "Dig through migration history and git blame",
                "Manually trace which queries touch that table",
                "Best-guess decision: deploy or roll back?",
                "2–4 hours later, the call gets made",
              ].map((item) => (
                <li key={item} className="flex items-start gap-3 text-[13px] text-white/40 leading-[1.5]">
                  <span className="mt-[3px] w-4 h-4 flex-shrink-0 rounded-full bg-[rgba(232,88,88,0.12)] border border-[rgba(232,88,88,0.2)] flex items-center justify-center">
                    <span className="w-1.5 h-[2px] bg-[#e85858] rounded-full" />
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* After */}
          <div className="bg-[#111] border border-[rgba(0,232,122,0.15)] rounded-2xl p-7">
            <p className="font-mono text-[10px] text-[#00e87a] uppercase tracking-[0.8px] mb-5">
              With SchemaZero
            </p>
            <ul className="space-y-4">
              {[
                "Scout catches every DDL event as it happens",
                "Agent Zero analyzes impact in seconds",
                "Risk scored: LOW, MEDIUM, HIGH, CRITICAL",
                "Plain-English briefing lands in Slack or PagerDuty",
                "Team sees exactly what changed and what to check",
                "Decision made in minutes, not hours",
              ].map((item) => (
                <li key={item} className="flex items-start gap-3 text-[13px] text-white/65 leading-[1.5]">
                  <span className="mt-[3px] w-4 h-4 flex-shrink-0 rounded-full bg-[rgba(0,232,122,0.1)] border border-[rgba(0,232,122,0.25)] flex items-center justify-center">
                    <span className="w-1.5 h-1.5 bg-[#00e87a] rounded-full" />
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Stat strip */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-14">
          {[
            {
              before: "2–4 hrs",
              after: "< 60 sec",
              label: "Time to understand a schema change",
            },
            {
              before: "Log diving",
              after: "Plain English",
              label: "How your team gets the answer",
            },
            {
              before: "~1 hr engineer time",
              after: "$19 / mo",
              label: "Cost of SchemaZero Solo",
            },
          ].map((stat) => (
            <div
              key={stat.label}
              className="bg-[#111] border border-white/[0.06] rounded-xl p-5 hover:border-[rgba(0,232,122,0.15)] transition-colors"
            >
              <div className="flex items-center gap-2 mb-3">
                <span className="font-mono text-sm text-white/25 line-through">{stat.before}</span>
                <span className="text-white/20 text-xs">→</span>
                <span className="font-mono text-sm text-[#00e87a] font-semibold">{stat.after}</span>
              </div>
              <p className="text-[12px] text-white/40 leading-[1.5]">{stat.label}</p>
            </div>
          ))}
        </div>

        {/* Pull quote */}
        <div className="bg-[#111] border border-white/[0.06] rounded-2xl p-8 flex flex-col sm:flex-row items-start sm:items-center gap-6">
          <div className="flex-1">
            <p className="text-[15px] text-white/75 leading-[1.6] mb-2">
              "One prevented incident pays for{" "}
              <span className="text-white font-medium">months</span> of SchemaZero.
              The question isn't whether schema changes will cause problems —
              it's whether you'll know about them first."
            </p>
            <p className="font-mono text-[11px] text-white/25">SchemaZero · built for engineering teams</p>
          </div>
          <a
            href="/auth/signup"
            className="flex-shrink-0 px-6 py-3 bg-[#00e87a] text-black text-sm font-semibold rounded-lg hover:opacity-85 transition-opacity whitespace-nowrap"
          >
            Start free trial
          </a>
        </div>

      </div>
    </section>
  );
}
