import { NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";

const RAILWAY_API_URL = process.env.RAILWAY_API_URL;

export async function POST(request: NextRequest) {
  if (!RAILWAY_API_URL) {
    return NextResponse.json(
      { error: "RAILWAY_API_URL is not configured" },
      { status: 500 }
    );
  }

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

  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json();

  const response = await fetch(`${RAILWAY_API_URL}/agent/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.access_token}`,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const error = await response.text();
    return NextResponse.json({ error }, { status: response.status });
  }

  const data = await response.json();
  return NextResponse.json(data);
}
