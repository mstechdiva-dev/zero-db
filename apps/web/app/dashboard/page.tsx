import ChangeFeed from "@/components/dashboard/ChangeFeed";
import ScoutStatus from "@/components/dashboard/ScoutStatus";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Live Change Feed</h1>
        <p className="text-gray-400 mt-1">
          Real-time schema changes detected by Scout
        </p>
      </div>
      <ScoutStatus />
      <ChangeFeed />
    </div>
  );
}
