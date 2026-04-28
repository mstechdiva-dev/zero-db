"use client";

import type { Tab } from "@/lib/types";

const TABS: { id: Tab; label: string }[] = [
  { id: "demo", label: "Live Demo" },
  { id: "how", label: "How it works" },
  { id: "security", label: "Security" },
  { id: "pricing", label: "Pricing" },
];

interface NavProps {
  activeTab: Tab;
  onTabChange: (tab: Tab) => void;
}

export default function Nav({ activeTab, onTabChange }: NavProps) {
  return (
    <nav className="sticky top-0 z-50 bg-[#0a0a0a]/90 backdrop-blur border-b border-gray-900">
      <div className="max-w-7xl mx-auto px-5 sm:px-6 flex items-center justify-between h-16">
        <span className="text-white font-bold text-lg tracking-tight flex-shrink-0">
          Schema<span className="text-[#00e87a]">Zero</span>
        </span>

        <div className="hidden md:flex gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`px-4 py-2 text-sm rounded-lg transition-colors font-medium ${
                activeTab === tab.id
                  ? "bg-[#00e87a]/10 text-[#00e87a]"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <a
            href="/auth/login"
            className="hidden sm:block text-sm text-gray-400 hover:text-white transition-colors"
          >
            Sign in
          </a>
          <a
            href="#waitlist"
            className="px-4 py-2 bg-[#00e87a] text-black text-sm font-semibold rounded-lg hover:opacity-85 transition-opacity whitespace-nowrap"
          >
            Join waitlist
          </a>
        </div>
      </div>

      {/* Mobile tab strip */}
      <div className="md:hidden flex overflow-x-auto border-t border-white/[0.06] px-3 py-1 gap-1 no-scrollbar">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`flex-shrink-0 px-3 py-1.5 text-xs rounded-lg transition-colors font-medium ${
              activeTab === tab.id
                ? "bg-[#00e87a]/10 text-[#00e87a]"
                : "text-gray-400 hover:text-white"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </nav>
  );
}
