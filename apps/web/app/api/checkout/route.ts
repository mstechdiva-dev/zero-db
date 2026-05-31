import { NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";
import { createClient } from "@supabase/supabase-js";
import { getStripe } from "@/lib/stripe";

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

  const stripe = getStripe();
  const session = await stripe.checkout.sessions.create({
    mode: "subscription",
    payment_method_types: ["card"],
    customer_email: user.email,
    line_items: [{ price: process.env.STRIPE_SOLO_PRICE_ID!, quantity: 1 }],
    success_url: `${process.env.DASHBOARD_URL}/settings?upgraded=1`,
    cancel_url: `${process.env.DASHBOARD_URL}/settings`,
    metadata: { org_id: userData.org_id },
  });

  return NextResponse.json({ url: session.url });
}
