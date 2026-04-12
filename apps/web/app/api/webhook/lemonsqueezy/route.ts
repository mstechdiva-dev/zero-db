import { NextRequest, NextResponse } from "next/server";
import { verifyLemonSqueezyWebhook } from "@/lib/lemonsqueezy";
import { createClient } from "@supabase/supabase-js";

export async function POST(request: NextRequest) {
  const body = await request.text();
  const signature = request.headers.get("x-signature");

  if (!signature) {
    return NextResponse.json({ error: "Missing x-signature header" }, { status: 400 });
  }

  const webhookSecret = process.env.LEMONSQUEEZY_WEBHOOK_SECRET;
  if (!webhookSecret) {
    return NextResponse.json({ error: "Webhook secret not configured" }, { status: 500 });
  }

  const isValid = verifyLemonSqueezyWebhook(body, signature, webhookSecret);
  if (!isValid) {
    return NextResponse.json({ error: "Invalid webhook signature" }, { status: 400 });
  }

  const supabaseAdmin = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let payload: any;
  try {
    payload = JSON.parse(body);
  } catch {
    return NextResponse.json({ error: "Invalid JSON payload" }, { status: 400 });
  }

  const eventName: string = payload?.meta?.event_name ?? "";
  // org_id is passed as custom_data when creating the checkout URL
  const orgId: string | undefined = payload?.meta?.custom_data?.org_id;
  const data = payload?.data?.attributes ?? {};

  switch (eventName) {
    case "subscription_created":
    case "order_created": {
      if (orgId) {
        await supabaseAdmin
          .from("organizations")
          .update({
            plan: "solo",
            trial_converted: true,
            lemon_customer_id: String(data.customer_id ?? ""),
            lemon_subscription_id: String(data.id ?? ""),
          })
          .eq("id", orgId);
      }
      break;
    }

    case "subscription_cancelled":
    case "subscription_expired": {
      const customerId = data.customer_id ? String(data.customer_id) : null;
      if (customerId) {
        await supabaseAdmin
          .from("organizations")
          .update({
            plan: "trial",
            lemon_subscription_id: null,
          })
          .eq("lemon_customer_id", customerId);
      }
      break;
    }

    default:
      break;
  }

  return NextResponse.json({ received: true });
}
