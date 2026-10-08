import { NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";

// Sends the connection form to the backend, which tests the connection and
// stores it encrypted. The connection string never goes through the chat.
export async function POST(request: NextRequest) {
  const backend = process.env.RAILWAY_API_URL;
  if (!backend) {
    return NextResponse.json(
      { error: "The backend isn't configured yet (RAILWAY_API_URL)." },
      { status: 500 }
    );
  }

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { cookies: { getAll: () => request.cookies.getAll(), setAll: () => {} } }
  );
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) {
    return NextResponse.json({ error: "Please sign in again." }, { status: 401 });
  }

  let body: { engine?: unknown; display_name?: unknown; connection_string?: unknown };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid request." }, { status: 400 });
  }

  let res: Response;
  try {
    res = await fetch(`${backend}/databases/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({
        engine: body.engine,
        display_name: body.display_name,
        connection_string: body.connection_string,
      }),
    });
  } catch {
    return NextResponse.json(
      { error: "Couldn't reach the SchemaZero backend. Try again in a minute." },
      { status: 502 }
    );
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof data.detail === "string" ? data.detail : "Couldn't save that database.";
    return NextResponse.json({ error: detail }, { status: res.status });
  }
  // Only what the page needs. Never echo anything about the connection string.
  return NextResponse.json({ id: data.id, display_name: data.display_name, engine: data.engine });
}
