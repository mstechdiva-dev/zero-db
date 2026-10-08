const POINTS = [
  {
    icon: "🔒",
    title: "Structure only, never your rows",
    description:
      "SchemaZero reads information_schema and system catalogs. It never reads your table data or application rows. For instant Postgres alerts it adds one small event trigger, and removes it when you disconnect the database.",
  },
  {
    icon: "🔐",
    title: "Credentials encrypted at rest",
    description:
      "Connection strings are encrypted with AES-256 and stored separately from application data. Decrypted only when Scout needs to connect, never logged.",
  },
  {
    icon: "✅",
    title: "Plans enforced on our servers",
    description:
      "Your plan and trial are checked on our servers before anything runs for your account, and they can't be changed from the browser. When a trial ends, monitoring and alerts stop until you upgrade.",
  },
  {
    icon: "🛡️",
    title: "Planned: SOC 2 and enterprise networking",
    description:
      "Not available yet. On the roadmap: a SOC 2 audit, VPC peering and SSO / SAML for Enterprise.",
  },
];

export default function Security() {
  return (
    <div className="py-20">
      <p className="font-mono text-[10px] uppercase tracking-[1.5px] text-[#00e87a] mb-3.5">
        Security
      </p>
      <h2 className="text-[36px] font-semibold text-white leading-[1.15] tracking-[-1.2px] mb-3.5">
        Structure only, by design
      </h2>
      <p className="text-base text-white/45 max-w-[560px] leading-[1.65] mb-14">
        SchemaZero reads schema metadata only, never your row-level data. On Postgres it adds a
        single event trigger so it can alert you instantly, and removes it when you disconnect.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {POINTS.map((point) => (
          <div
            key={point.title}
            className="bg-[#111] border border-white/[0.06] rounded-xl p-7 hover:border-[rgba(0,232,122,0.2)] transition-colors"
          >
            <div className="text-[22px] mb-3.5"><span aria-hidden="true">{point.icon}</span></div>
            <h3 className="text-[15px] font-semibold text-white mb-2">{point.title}</h3>
            <p className="text-[13px] text-white/45 leading-[1.65]">{point.description}</p>
          </div>
        ))}
      </div>

      <div className="mt-10 border border-[rgba(0,232,122,0.2)] bg-[rgba(0,232,122,0.08)] rounded-xl px-8 py-7 text-[15px] text-[#00e87a] italic leading-[1.6] text-center tracking-[-0.1px]">
        "SchemaZero never sees your data. It only sees your structure."
      </div>
    </div>
  );
}
