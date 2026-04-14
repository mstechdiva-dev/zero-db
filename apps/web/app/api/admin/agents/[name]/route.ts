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

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ name: string }> }
) {
  const email = await verifyAdmin(request);
  if (!email) return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  if (!RAILWAY_API_URL) return NextResponse.json({ error: "RAILWAY_API_URL not set" }, { status: 500 });

  const { name } = await params;
  const res = await fetch(`${RAILWAY_API_URL}/admin/agents/${name}`, {
    headers: { "x-admin-secret": ADMIN_SECRET },
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ name: string }> }
) {
  const email = await verifyAdmin(request);
  if (!email) return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  if (!RAILWAY_API_URL) return NextResponse.json({ error: "RAILWAY_API_URL not set" }, { status: 500 });

  const { name } = await params;
  const body = await request.json();

  const res = await fetch(`${RAILWAY_API_URL}/admin/agents/${name}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      "x-admin-secret": ADMIN_SECRET,
    },
    body: JSON.stringify({ ...body, saved_by: email }),
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ name: string }> }
) {
  // POST /api/admin/agents/[name]?revert=<version_id>
  const email = await verifyAdmin(request);
  if (!email) return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  if (!RAILWAY_API_URL) return NextResponse.json({ error: "RAILWAY_API_URL not set" }, { status: 500 });

  const { name } = await params;
  const versionId = request.nextUrl.searchParams.get("revert");
  if (!versionId) return NextResponse.json({ error: "Missing revert version id" }, { status: 400 });

  const res = await fetch(
    `${RAILWAY_API_URL}/admin/agents/${name}/revert/${versionId}?saved_by=${encodeURIComponent(email)}`,
    {
      method: "POST",
      headers: { "x-admin-secret": ADMIN_SECRET },
    }
  );
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
