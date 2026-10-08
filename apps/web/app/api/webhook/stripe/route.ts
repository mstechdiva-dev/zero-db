import { NextRequest, NextResponse } from "next/server";
import type Stripe from "stripe";
import { ENDED_STATUSES, PAYING_STATUSES, getStripe, idOf, serviceDb } from "@/lib/stripe";

// Stripe tells us when someone pays, changes plan or cancels. This is the only
// place the plan changes, so it checks the signature before doing anything.
export async function POST(request: NextRequest) {
  const secret = process.env.STRIPE_WEBHOOK_SECRET;
  if (!secret || !process.env.STRIPE_SECRET_KEY) {
    return NextResponse.json({ error: "Billing isn't set up yet." }, { status: 503 });
  }

  const signature = request.headers.get("stripe-signature") ?? "";
  const rawBody = await request.text();

  let event: Stripe.Event;
  try {
    event = getStripe().webhooks.constructEvent(rawBody, signature, secret);
  } catch {
    return NextResponse.json({ error: "Invalid signature" }, { status: 400 });
  }

  const db = serviceDb();
  let error: { message: string } | null = null;

  if (event.type === "checkout.session.completed") {
    const session = event.data.object as Stripe.Checkout.Session;
    const orgId = session.client_reference_id;
    if (orgId && session.mode === "subscription" && session.payment_status !== "unpaid") {
      ({ error } = await db
        .from("organizations")
        .update({
          plan: "solo",
          trial_converted: true,
          stripe_customer_id: idOf(session.customer),
          stripe_subscription_id: idOf(session.subscription),
        })
        .eq("id", orgId));
    }
  }

  if (
    event.type === "customer.subscription.updated" ||
    event.type === "customer.subscription.deleted"
  ) {
    const sub = event.data.object as Stripe.Subscription;
    const ended = event.type === "customer.subscription.deleted" || ENDED_STATUSES.includes(sub.status);
    const paying = event.type === "customer.subscription.updated" && PAYING_STATUSES.includes(sub.status);

    let orgId: string | null = sub.metadata?.org_id ?? null;
    if (!orgId) {
      const { data } = await db
        .from("organizations")
        .select("id")
        .eq("stripe_subscription_id", sub.id)
        .maybeSingle();
      orgId = data?.id ?? null;
    }

    if (orgId && paying) {
      ({ error } = await db
        .from("organizations")
        .update({
          plan: "solo",
          trial_converted: true,
          stripe_customer_id: idOf(sub.customer),
          stripe_subscription_id: sub.id,
        })
        .eq("id", orgId));
    } else if (orgId && ended) {
      // Back to an expired trial so they're asked to upgrade. Only if this is
      // still their current subscription, so an old cancellation can't undo a new one.
      ({ error } = await db
        .from("organizations")
        .update({
          plan: "trial",
          trial_converted: false,
          trial_ends_at: new Date().toISOString(),
          stripe_subscription_id: null,
        })
        .eq("id", orgId)
        .eq("stripe_subscription_id", sub.id));
    }
  }

  // A 500 makes Stripe retry later; everything else we don't handle is just acknowledged.
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ received: true });
}
