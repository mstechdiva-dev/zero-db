"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Change Feed" },
  { href: "/dashboard/databases", label: "Databases" },
  { href: "/dashboard/settings", label: "Settings" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 shrink-0 border-r border-gray-900 flex flex-col py-6 px-4">
      <Link href="/" className="text-white font-bold text-lg tracking-tight mb-8 px-2">
        Schema<span className="text-[#00e87a]">Zero</span>
      </Link>
      <nav className="space-y-1">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`block px-3 py-2 rounded-lg text-sm transition-colors ${
              pathname === item.href
                ? "bg-[#00e87a]/10 text-[#00e87a] font-medium"
                : "text-gray-400 hover:text-white hover:bg-gray-900"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
