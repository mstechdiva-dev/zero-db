# Billing (Stripe)

## Status
Built. Billing runs on Stripe. Setup steps are in `SETUP.md` (Vercel section, step 4).

## How it works

| File | What it does |
|---|---|
| `apps/web/lib/stripe.ts` | Stripe client, plus the subscription states that count as paying or ended |
| `apps/web/app/api/checkout/route.ts` | Signed-in users: starts a Stripe Checkout subscription for the Solo plan and returns its URL. Refuses (409) if the org already has a subscription. |
| `apps/web/app/api/billing/portal/route.ts` | Signed-in users: returns the URL of Stripe's customer portal (change card, invoices, cancel) |
| `apps/web/app/api/webhook/stripe/route.ts` | Stripe's events. The only place the plan changes. Verifies the signature first. |
| `apps/web/app/dashboard/settings/page.tsx` | Upgrade button, Manage subscription button, success and error messages |
| `supabase/migrations/007_stripe.sql` | `organizations.stripe_customer_id` and `stripe_subscription_id` |

## Plan changes (webhook)

| Stripe event | What happens |
|---|---|
| `checkout.session.completed` (subscription, paid) | Org goes to `solo`, `trial_converted = true`, customer and subscription ids saved |
| `customer.subscription.updated`, status `active` or `trialing` | Org goes to `solo` (covers resubscribing) |
| `customer.subscription.updated`, status `canceled`, `unpaid` or `incomplete_expired`, and `customer.subscription.deleted` | Org goes back to an expired trial so the dashboard asks them to upgrade. Only applies if it's the org's current subscription, so an old cancellation can't undo a new one. |
| `past_due`, `incomplete`, `paused` | No change. Stripe retries the payment. |
| Anything else | Acknowledged and ignored |

The org is found from `client_reference_id` at checkout, and from `subscription_data.metadata.org_id` on later events (falling back to the stored subscription id). A database error returns 500 so Stripe retries the event.

## Settings

```
STRIPE_SECRET_KEY=        # sk_test_… or sk_live_…
STRIPE_PRICE_ID_SOLO=     # price_…
STRIPE_WEBHOOK_SECRET=    # whsec_…
```

If any is missing, checkout, the portal and the webhook answer 503 "Billing isn't set up yet" and nothing else is affected.

`STRIPE_API_BASE_URL` exists only so tests can point at a fake Stripe. Never set it for real.

## Trying it locally

With the [Stripe CLI](https://stripe.com/docs/stripe-cli):

```bash
stripe listen --forward-to localhost:3000/api/webhook/stripe   # prints a whsec_… for STRIPE_WEBHOOK_SECRET
```

Then upgrade from Settings with the test card `4242 4242 4242 4242`.

## Limits

- Solo is the only self-serve plan. Teams is a waitlist and Enterprise is by email, so both change by hand.
- The 14-day free trial needs no card and is tracked in SchemaZero, not Stripe.
- Nothing here takes a real payment until you switch to live keys and a live price.
