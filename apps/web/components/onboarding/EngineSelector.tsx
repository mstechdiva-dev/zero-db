const ENGINES = [
  { id: "postgresql", label: "PostgreSQL" },
  { id: "supabase", label: "Supabase" },
  { id: "neon", label: "Neon" },
  { id: "cockroachdb", label: "CockroachDB" },
  { id: "mysql", label: "MySQL" },
  { id: "mariadb", label: "MariaDB" },
  { id: "mongodb", label: "MongoDB" },
  { id: "redis", label: "Redis" },
  { id: "sqlserver", label: "SQL Server" },
  { id: "sqlite", label: "SQLite" },
  { id: "oracle", label: "Oracle" },
  { id: "snowflake", label: "Snowflake" },
  { id: "dynamodb", label: "DynamoDB" },
];

interface EngineSelectorProps {
  selected: string | null;
  onSelect: (engine: string) => void;
}

export default function EngineSelector({ selected, onSelect }: EngineSelectorProps) {
  return (
    <div className="grid grid-cols-3 gap-3">
      {ENGINES.map((engine) => (
        <button
          key={engine.id}
          onClick={() => onSelect(engine.id)}
          className={`px-4 py-3 border rounded-lg text-sm font-medium transition-colors ${
            selected === engine.id
              ? "border-[#00e87a] text-[#00e87a] bg-[#00e87a]/10"
              : "border-gray-800 text-gray-400 hover:border-gray-600 hover:text-white"
          }`}
        >
          {engine.label}
        </button>
      ))}
    </div>
  );
}
