import { NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";
import { getStripe, serviceDb, stripeConfigured } from "@/lib/stripe";

// Opens Stripe's customer portal (change card, cancel, invoices).
export async function POST(request: NextRequest) {
  if (!stripeConfigured()) {
    return NextResponse.json({ error: "Billing isn't set up yet." }, { status: 503 });
  }

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

  const { data: org } = await db
    .from("organizations")
    .select("stripe_customer_id")
    .eq("id", userData.org_id)
    .single();
  if (!org?.stripe_customer_id) {
    return NextResponse.json({ error: "There's no billing account to manage yet." }, { status: 400 });
  }

  try {
    const session = await getStripe().billingPortal.sessions.create({
      customer: org.stripe_customer_id,
      return_url: `${request.nextUrl.origin}/dashboard/settings`,
    });
    return NextResponse.json({ url: session.url });
  } catch (err) {
    console.error("Stripe portal failed:", err instanceof Error ? err.message : err);
    return NextResponse.json(
      { error: "Couldn't open billing. Please try again." },
      { status: 502 }
    );
  }
}
