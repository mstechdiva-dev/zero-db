import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

export async function POST(request: NextRequest) {
  let body: { email?: unknown };

  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const { email } = body;

  if (!email || typeof email !== "string" || !email.includes("@")) {
    return NextResponse.json({ error: "Invalid email" }, { status: 400 });
  }

  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false } }
  );

  const { error } = await supabase
    .from("waitlist")
    .upsert({ email: email.toLowerCase().trim() }, { onConflict: "email" });

  if (error) {
    console.error("Waitlist insert error:", error);
    return NextResponse.json({ ok: false }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}
