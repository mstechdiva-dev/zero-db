import DatabaseCard from "@/components/dashboard/DatabaseCard";

export default function DatabasesPage() {
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Connected Databases</h1>
          <p className="text-gray-400 mt-1">Manage your Scout-monitored databases</p>
        </div>
        <a
          href="/onboarding"
          className="px-4 py-2 bg-[#00e87a] text-black font-semibold rounded-lg hover:bg-[#00c96a] transition-colors text-sm"
        >
          Add database
        </a>
      </div>
      <DatabaseCard />
    </div>
  );
}
