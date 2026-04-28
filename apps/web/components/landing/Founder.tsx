const CREDENTIALS = [
  "Microsoft · 6 yrs",
  "Deloitte",
  "DoD Healthcare",
  "Wiley Publishing",
  "Microsoft Build Speaker",
];

export default function Founder() {
  return (
    <section className="bg-[#0a0a0a] border-t border-white/[0.06] px-5 sm:px-10 py-20">
      <div className="max-w-[960px] mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-12 items-start">

          {/* Left */}
          <div>
            <p className="font-mono text-[11px] text-white/22 uppercase tracking-[0.8px] mb-3">
              Founder
            </p>
            <h2 className="text-2xl font-semibold text-white tracking-[-0.8px] leading-[1.2] mb-5">
              Built by someone who's been in the incident.
            </h2>
            <div className="flex flex-wrap gap-2">
              {CREDENTIALS.map((c) => (
                <span
                  key={c}
                  className="bg-[#111] border border-white/[0.06] text-white/35 font-mono text-[11px] px-2.5 py-1 rounded-md"
                >
                  {c}
                </span>
              ))}
            </div>
          </div>

          {/* Right */}
          <div className="space-y-5">
            <p className="text-[15px] text-white/55 leading-[1.75]">
              I spent a decade architecting enterprise database systems for Fortune 500
              companies and government healthcare. That included leading{" "}
              <span className="text-white/85">
                100+ planned migrations in the travel industry with zero downtime
              </span>{" "}
              — where a schema change gone wrong doesn't just break an app, it grounds
              flights. I know exactly what that costs — in hours, in trust, and in revenue.
            </p>
            <p className="text-[15px] text-white/55 leading-[1.75]">
              SchemaZero is built on that experience. Every database engine it supports —
              Postgres, MySQL, MongoDB, Redis, CockroachDB — is one I've run in production.
              The risk scoring, the impact analysis, the alert routing: that's not designed
              from a spec. It's designed from incidents.
            </p>
            <p className="text-[15px] text-white/55 leading-[1.75]">
              The timing is right: the database stack is more fragmented than ever, teams
              are running five engines where they used to run one, and AI-assisted
              development means a solo builder can ship what used to take an engineering
              team. The schema change problem is getting harder.
              SchemaZero is the answer I wish had existed.
            </p>

            {/* Credibility strip */}
            <div className="pt-2 flex flex-wrap gap-x-6 gap-y-2">
              {[
                "Co-authored Professional Hadoop · Wiley Publishing",
                "100+ migrations · travel industry · zero downtime",
                "Fortune 500 & DoD clients",
                "Founder · The Basics Central 501(c)(3)",
              ].map((item) => (
                <span key={item} className="text-[12px] text-white/25 font-mono">
                  · {item}
                </span>
              ))}
            </div>
          </div>

        </div>
      </div>
    </section>
  );
}
