const POINTS = [
  {
    icon: "🔒",
    title: "Read-only credentials",
    description:
      "Minimum required permissions only. SchemaZero accesses information_schema and system catalogs — never your table data, never your application rows.",
  },
  {
    icon: "🔐",
    title: "Credentials encrypted at rest",
    description:
      "Connection strings are encrypted with AES-256 and stored separately from application data. Decrypted only when Scout needs to connect — never logged.",
  },
  {
    icon: "🛡️",
    title: "SOC 2 Type II in progress",
    description:
      "We're completing our SOC 2 Type II audit. Reports are available for Enterprise prospects on request.",
  },
  {
    icon: "🌐",
    title: "VPC peering on Enterprise",
    description:
      "Enterprise plans support direct VPC peering so your connection string never leaves your network perimeter. SSO / SAML included.",
  },
];

export default function Security() {
  return (
    <div className="py-20">
      <p className="font-mono text-[10px] uppercase tracking-[1.5px] text-[#00e87a] mb-3.5">
        Security
      </p>
      <h2 className="text-[36px] font-semibold text-white leading-[1.15] tracking-[-1.2px] mb-3.5">
        Read-only by design
      </h2>
      <p className="text-base text-white/45 max-w-[560px] leading-[1.65] mb-14">
        SchemaZero never writes to your database. It reads schema metadata only — never
        your row-level data, never your application secrets.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {POINTS.map((point) => (
          <div
            key={point.title}
            className="bg-[#111] border border-white/[0.06] rounded-xl p-7 hover:border-[rgba(0,232,122,0.2)] transition-colors"
          >
            <div className="text-[22px] mb-3.5">{point.icon}</div>
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
