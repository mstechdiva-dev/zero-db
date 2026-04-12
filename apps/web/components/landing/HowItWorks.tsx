const STEPS = [
  {
    number: "01",
    title: "Connect your database",
    description:
      "Paste a read-only connection string. SchemaZero never writes to your database. Supports PostgreSQL, MySQL, MongoDB, Redis, and more.",
  },
  {
    number: "02",
    title: "Scout watches for changes",
    description:
      "Our always-on Scout agent monitors your schema using pg_notify, change streams, or polling — depending on your engine.",
  },
  {
    number: "03",
    title: "Zero analyzes impact",
    description:
      "The moment a change is detected, Zero uses Claude AI to trace affected queries, services, and indexes — and scores risk.",
  },
  {
    number: "04",
    title: "Your team gets notified",
    description:
      "HIGH and CRITICAL changes fire Slack alerts. CRITICAL changes page your on-call via PagerDuty. Email for everything else.",
  },
];

export default function HowItWorks() {
  return (
    <div className="pt-16 pb-12">
      <h2 className="text-3xl font-bold text-white mb-12">How it works</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {STEPS.map((step) => (
          <div
            key={step.number}
            className="bg-[#111] border border-gray-800 rounded-xl p-6"
          >
            <span className="text-[#00e87a] font-mono text-sm font-bold">
              {step.number}
            </span>
            <h3 className="text-white font-semibold text-lg mt-2">
              {step.title}
            </h3>
            <p className="text-gray-400 mt-2 text-sm leading-relaxed">
              {step.description}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-12 bg-[#111] border border-gray-800 rounded-xl p-6">
        <h3 className="text-white font-semibold mb-4">Supported engines</h3>
        <div className="flex flex-wrap gap-2">
          {[
            "PostgreSQL",
            "Supabase",
            "Neon",
            "CockroachDB",
            "MySQL",
            "MariaDB",
            "MongoDB",
            "Redis",
            "SQL Server",
            "SQLite",
            "Oracle",
            "Snowflake",
            "DynamoDB",
          ].map((engine) => (
            <span
              key={engine}
              className="px-3 py-1 bg-gray-900 border border-gray-800 rounded-full text-gray-300 text-sm"
            >
              {engine}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
