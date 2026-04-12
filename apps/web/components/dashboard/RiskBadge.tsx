const STYLES: Record<string, string> = {
  low: "text-green-400 bg-green-400/10 border-green-400/20",
  medium: "text-yellow-400 bg-yellow-400/10 border-yellow-400/20",
  high: "text-orange-400 bg-orange-400/10 border-orange-400/20",
  critical: "text-red-400 bg-red-400/10 border-red-400/20",
};

interface RiskBadgeProps {
  level: string;
}

export default function RiskBadge({ level }: RiskBadgeProps) {
  const style = STYLES[level.toLowerCase()] ?? STYLES.low;
  return (
    <span
      className={`px-2 py-0.5 text-xs font-bold rounded border font-mono uppercase ${style}`}
    >
      {level}
    </span>
  );
}
