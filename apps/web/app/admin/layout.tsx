import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { ReactNode } from "react";

function adminEmails(): string[] {
  return (process.env.ADMIN_EMAIL ?? "")
    .split(",")
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean);
}

export default async function AdminLayout({ children }: { children: ReactNode }) {
  const cookieStore = await cookies();

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => cookieStore.getAll(),
        setAll: () => {},
      },
    }
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  // Double-check — middleware is the primary guard, but defend in depth
  if (!user || !adminEmails().includes(user.email?.toLowerCase() ?? "")) {
    redirect("/auth/login");
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white">
      {/* Admin navigation bar */}
      <nav className="border-b border-gray-800 px-6 py-3 flex items-center gap-6 sticky top-0 z-10 bg-[#0a0a0a]">
        <span className="text-[#00e87a] font-bold text-xs tracking-widest uppercase">
          SchemaZero Admin
        </span>

        <div className="flex items-center gap-1">
          <NavLink href="/admin">Overview</NavLink>
          <NavLink href="/admin/leads">Leads</NavLink>
        </div>

        <div className="ml-auto flex items-center gap-4">
          <span className="text-gray-600 text-xs hidden sm:block">{user.email}</span>
          <Link
            href="/dashboard"
            className="text-gray-500 hover:text-white text-xs transition-colors"
          >
            ← Dashboard
          </Link>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>
    </div>
  );
}

function NavLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className="text-gray-400 hover:text-white text-sm px-3 py-1.5 rounded hover:bg-white/5 transition-colors"
    >
      {children}
    </Link>
  );
}
