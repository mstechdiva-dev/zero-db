import { NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";

const RAILWAY_API_URL = process.env.RAILWAY_API_URL;
const ADMIN_SECRET = process.env.ADMIN_SECRET ?? "";

function adminEmails(): string[] {
  return (process.env.ADMIN_EMAIL ?? "")
    .split(",")
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean);
}

async function verifyAdmin(request: NextRequest): Promise<string | null> {
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: () => {},
      },
    }
  );
  const { data: { user } } = await supabase.auth.getUser();
  if (!user?.email) return null;
  if (!adminEmails().includes(user.email.toLowerCase())) return null;
  return user.email;
}

export async function GET(request: NextRequest) {
  const email = await verifyAdmin(request);
  if (!email) return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  if (!RAILWAY_API_URL) return NextResponse.json({ error: "RAILWAY_API_URL not set" }, { status: 500 });

  const res = await fetch(`${RAILWAY_API_URL}/admin/agents`, {
    headers: { "x-admin-secret": ADMIN_SECRET },
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
