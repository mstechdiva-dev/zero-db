export default function SettingsPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-gray-400 mt-1">
          Manage alerts and team members
        </p>
      </div>

      <section className="bg-[#111] border border-gray-800 rounded-xl p-6 space-y-6">
        <h2 className="text-lg font-semibold text-white">Alert Configuration</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">
              Slack Webhook URL
            </label>
            <input
              type="url"
              placeholder="https://hooks.slack.com/..."
              className="w-full px-4 py-3 bg-[#0a0a0a] border border-gray-800 rounded-lg text-white placeholder-gray-600 focus:outline-none focus:border-[#00e87a] transition-colors"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">
              PagerDuty Integration Key
            </label>
            <input
              type="password"
              placeholder="••••••••••••••••"
              className="w-full px-4 py-3 bg-[#0a0a0a] border border-gray-800 rounded-lg text-white placeholder-gray-600 focus:outline-none focus:border-[#00e87a] transition-colors"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">
              Alert on risk levels
            </label>
            <div className="flex gap-3">
              {["low", "medium", "high", "critical"].map((level) => (
                <label key={level} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    defaultChecked={level === "high" || level === "critical"}
                    className="accent-[#00e87a]"
                  />
                  <span className="text-sm text-gray-300 capitalize">{level}</span>
                </label>
              ))}
            </div>
          </div>
          <button className="px-4 py-2 bg-[#00e87a] text-black font-semibold rounded-lg hover:bg-[#00c96a] transition-colors text-sm">
            Save alert config
          </button>
        </div>
      </section>

    </div>
  );
}
