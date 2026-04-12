const DEMO_EVENTS = [
  {
    id: "1",
    type: "DROPPED",
    engine: "postgresql",
    object: "users.email_verified",
    risk: "HIGH",
    time: "just now",
    summary: "Column dropped from high-traffic table. 12 queries affected.",
  },
  {
    id: "2",
    type: "MODIFIED",
    engine: "supabase",
    object: "orders.status",
    risk: "MEDIUM",
    time: "2m ago",
    summary: "Column type changed from varchar(50) to text. Check constraints.",
  },
  {
    id: "3",
    type: "ADDED",
    engine: "postgresql",
    object: "products.metadata",
    risk: "LOW",
    time: "5m ago",
    summary: "Nullable JSONB column added. No breaking changes detected.",
  },
];

const RISK_COLORS: Record<string, string> = {
  LOW: "text-green-400 bg-green-400/10 border-green-400/20",
  MEDIUM: "text-yellow-400 bg-yellow-400/10 border-yellow-400/20",
  HIGH: "text-orange-400 bg-orange-400/10 border-orange-400/20",
  CRITICAL: "text-red-400 bg-red-400/10 border-red-400/20",
};

const TYPE_COLORS: Record<string, string> = {
  ADDED: "text-[#00e87a] bg-[#00e87a]/10",
  MODIFIED: "text-yellow-400 bg-yellow-400/10",
  DROPPED: "text-red-400 bg-red-400/10",
};

export default function Hero() {
  return (
    <div className="pt-20 pb-12">
      <div className="max-w-3xl">
        <h1 className="text-5xl font-bold text-white leading-tight">
          Schema changes happen.{" "}
          <span className="text-[#00e87a]">Know what they mean.</span>
        </h1>
        <p className="mt-6 text-xl text-gray-400">
          SchemaZero watches your database schema. The moment something changes,
          it analyzes impact, scores risk, and notifies your team — before
          anything breaks.
        </p>
        <p className="mt-3 text-sm text-gray-600 font-mono">
          SchemaZero never sees your data. It only sees your structure.
        </p>
        <div className="mt-10 flex gap-4">
          <a
            href="/auth/signup"
            className="px-6 py-3 bg-[#00e87a] text-black font-semibold rounded-lg hover:bg-[#00c96a] transition-colors"
          >
            Start free trial
          </a>
          <a
            href="#"
            className="px-6 py-3 border border-gray-700 text-white font-semibold rounded-lg hover:border-gray-500 transition-colors"
          >
            View docs
          </a>
        </div>
      </div>

      <div className="mt-16">
        <p className="text-xs text-gray-600 font-mono uppercase tracking-widest mb-4">
          Live demo — simulated events
        </p>
        <div className="space-y-3">
          {DEMO_EVENTS.map((event) => (
            <div
              key={event.id}
              className="bg-[#111] border border-gray-800 rounded-xl p-5 flex items-start gap-4"
            >
              <span
                className={`px-2 py-0.5 text-xs font-mono font-bold rounded ${TYPE_COLORS[event.type]}`}
              >
                {event.type}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-white font-mono text-sm">
                    {event.object}
                  </span>
                  <span className="text-gray-600 text-xs">{event.engine}</span>
                </div>
                <p className="text-gray-400 text-sm mt-1">{event.summary}</p>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <span
                  className={`px-2 py-0.5 text-xs font-bold rounded border ${RISK_COLORS[event.risk]}`}
                >
                  {event.risk}
                </span>
                <span className="text-gray-600 text-xs">{event.time}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
