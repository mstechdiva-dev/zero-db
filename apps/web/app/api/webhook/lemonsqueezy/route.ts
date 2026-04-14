import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";
import { verifyWebhookSignature } from "@/lib/lemonsqueezy";

function serviceDb() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false } }
  );
}

export async function POST(request: NextRequest) {
  const rawBody = await request.text();
  const signature = request.headers.get("x-signature") ?? "";

  if (!verifyWebhookSignature(rawBody, signature)) {
    return NextResponse.json({ error: "Invalid signature" }, { status: 401 });
  }

  const event = JSON.parse(rawBody);
  const eventName: string = event.meta?.event_name ?? "";
  const orgId: string = event.meta?.custom_data?.org_id ?? "";

  if (!orgId) return NextResponse.json({ received: true });

  const db = serviceDb();

  if (eventName === "order_created") {
    // Solo plan purchased — activate subscription
    const customerId = String(event.data?.attributes?.customer_id ?? "");
    await db.from("organizations").update({
      plan: "solo",
      trial_converted: true,
      lemonsqueezy_customer_id: customerId,
    }).eq("id", orgId);
  }

  if (eventName === "subscription_created") {
    const subscriptionId = String(event.data?.id ?? "");
    const portalUrl: string = event.data?.attributes?.urls?.customer_portal ?? "";
    await db.from("organizations").update({
      lemonsqueezy_subscription_id: subscriptionId,
      lemonsqueezy_customer_portal_url: portalUrl || null,
    }).eq("id", orgId);
  }

  if (eventName === "subscription_cancelled") {
    // Revert to expired trial so middleware redirects them to upgrade
    await db.from("organizations").update({
      plan: "trial",
      trial_converted: false,
      trial_ends_at: new Date().toISOString(),
      lemonsqueezy_subscription_id: null,
      lemonsqueezy_customer_portal_url: null,
    }).eq("id", orgId);
  }

  return NextResponse.json({ received: true });
}
