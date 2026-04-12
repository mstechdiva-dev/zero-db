import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";
import { verifyWebhookSignature } from "@/lib/lemonsqueezy";

// Use service role key — this route runs server-side and needs write access
const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

const WEBHOOK_SECRET = process.env.LEMONSQUEEZY_WEBHOOK_SECRET ?? "";

export async function POST(request: NextRequest) {
  const signature = request.headers.get("X-Signature") ?? "";
  const rawBody = await request.text();

  // Verify HMAC signature
  if (WEBHOOK_SECRET) {
    const valid = await verifyWebhookSignature(rawBody, signature, WEBHOOK_SECRET);
    if (!valid) {
      return NextResponse.json({ error: "Invalid signature" }, { status: 401 });
    }
  }

  let payload: Record<string, unknown>;
  try {
    payload = JSON.parse(rawBody);
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const eventName = payload.meta && typeof payload.meta === "object"
    ? (payload.meta as Record<string, unknown>).event_name
    : null;

  const data = payload.data as Record<string, unknown> | undefined;
  const attributes = data?.attributes as Record<string, unknown> | undefined;
  const customData = (payload.meta as Record<string, unknown>)?.custom_data as
    | Record<string, unknown>
    | undefined;

  const orgId = customData?.org_id as string | undefined;

  try {
    switch (eventName) {
      case "order_created": {
        // Trial user completed checkout → upgrade to Solo plan
        if (!orgId) break;

        const customerId = attributes?.customer_id as string | undefined;
        const subscriptionId = attributes?.subscription_id as string | undefined;

        await supabaseAdmin
          .from("organizations")
          .update({
            plan: "solo",
            trial_converted: true,
            lemonsqueezy_customer_id: customerId ?? null,
            lemonsqueezy_subscription_id: subscriptionId ?? null,
          })
          .eq("id", orgId);

        break;
      }

      case "subscription_cancelled": {
        // Subscription cancelled → revert to trial, set trial_ends_at to now
        if (!orgId) break;

        await supabaseAdmin
          .from("organizations")
          .update({
            plan: "trial",
            trial_ends_at: new Date().toISOString(),
          })
          .eq("id", orgId);

        break;
      }

      case "subscription_resumed": {
        // Subscription resumed after cancellation → restore Solo plan
        if (!orgId) break;

        await supabaseAdmin
          .from("organizations")
          .update({ plan: "solo" })
          .eq("id", orgId);

        break;
      }

      default:
        // Unhandled event — acknowledge receipt without error
        break;
    }
  } catch (err) {
    console.error("Lemon Squeezy webhook handler error:", err);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }

  return NextResponse.json({ received: true });
}
