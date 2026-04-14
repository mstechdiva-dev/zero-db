import { NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";
import { createClient } from "@supabase/supabase-js";
import { createCheckoutUrl } from "@/lib/lemonsqueezy";

function serviceDb() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false } }
  );
}

export async function POST(request: NextRequest) {
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { cookies: { getAll: () => request.cookies.getAll(), setAll: () => {} } }
  );

  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const db = serviceDb();
  const { data: userData } = await db
    .from("users")
    .select("org_id")
    .eq("auth_user_id", user.id)
    .single();

  if (!userData) return NextResponse.json({ error: "User not found" }, { status: 404 });

  const checkoutUrl = await createCheckoutUrl(user.email!, userData.org_id);
  return NextResponse.json({ url: checkoutUrl });
}
