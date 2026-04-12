import RiskBadge from "./RiskBadge";

export interface ChangeEvent {
  id: string;
  change_type: string;
  object_type: string;
  object_name: string;
  schema_name?: string;
  risk_level?: string;
  detected_at: string;
  database_id: string;
}

interface ChangeCardProps {
  event: ChangeEvent;
  onClick?: () => void;
}

const TYPE_COLORS: Record<string, string> = {
  added: "text-[#00e87a] bg-[#00e87a]/10",
  dropped: "text-red-400 bg-red-400/10",
  modified: "text-yellow-400 bg-yellow-400/10",
};

function labelForChangeType(changeType: string): string {
  if (changeType.includes("added")) return "ADDED";
  if (changeType.includes("dropped")) return "DROPPED";
  return "MODIFIED";
}

function colorForChangeType(changeType: string): string {
  if (changeType.includes("added")) return TYPE_COLORS.added;
  if (changeType.includes("dropped")) return TYPE_COLORS.dropped;
  return TYPE_COLORS.modified;
}

export default function ChangeCard({ event, onClick }: ChangeCardProps) {
  const label = labelForChangeType(event.change_type);
  const color = colorForChangeType(event.change_type);
  const objectPath = event.schema_name
    ? `${event.schema_name}.${event.object_name}`
    : event.object_name;

  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-[#111] border border-gray-800 rounded-xl p-5 flex items-start gap-4 hover:border-gray-600 transition-colors"
    >
      <span className={`px-2 py-0.5 text-xs font-mono font-bold rounded ${color} shrink-0`}>
        {label}
      </span>
      <div className="flex-1 min-w-0">
        <span className="text-white font-mono text-sm">{objectPath}</span>
        <p className="text-gray-500 text-xs mt-1 capitalize">
          {event.change_type.replace(/_/g, " ")}
        </p>
      </div>
      <div className="flex items-center gap-3 shrink-0">
        {event.risk_level && <RiskBadge level={event.risk_level} />}
        <span className="text-gray-600 text-xs">
          {new Date(event.detected_at).toLocaleTimeString()}
        </span>
      </div>
    </button>
  );
}
