import { NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";
import { getStripe, serviceDb, stripeConfigured } from "@/lib/stripe";

// Starts a Stripe Checkout subscription for the Solo plan and returns its URL.
export async function POST(request: NextRequest) {
  const priceId = process.env.STRIPE_PRICE_ID_SOLO;
  if (!stripeConfigured() || !priceId) {
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
    .select("plan, stripe_customer_id, stripe_subscription_id")
    .eq("id", userData.org_id)
    .single();
  if (org?.plan === "solo" && org.stripe_subscription_id) {
    return NextResponse.json({ error: "You're already subscribed." }, { status: 409 });
  }

  const origin = request.nextUrl.origin;
  try {
    const session = await getStripe().checkout.sessions.create({
      mode: "subscription",
      line_items: [{ price: priceId, quantity: 1 }],
      client_reference_id: userData.org_id,
      ...(org?.stripe_customer_id
        ? { customer: org.stripe_customer_id }
        : { customer_email: user.email ?? undefined }),
      // Lets the webhook find the org on later subscription events.
      subscription_data: { metadata: { org_id: userData.org_id } },
      success_url: `${origin}/dashboard/settings?billing=success`,
      cancel_url: `${origin}/dashboard/settings?billing=cancelled`,
    }, {
      // Requests for the same org within the same 5 minutes get the same session back from
      // Stripe, so two clicks (or two tabs) at once can't start two subscriptions.
      idempotencyKey: `checkout-${userData.org_id}-${Math.floor(Date.now() / 300_000)}`,
    });
    return NextResponse.json({ url: session.url });
  } catch (err) {
    console.error("Stripe checkout failed:", err instanceof Error ? err.message : err);
    return NextResponse.json(
      { error: "Couldn't start checkout. Please try again." },
      { status: 502 }
    );
  }
}
