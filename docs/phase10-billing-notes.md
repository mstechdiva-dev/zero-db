# Phase 10 — Billing (Lemon Squeezy)

## Status
NOT YET BUILT. Billing is intentionally deferred to Phase 10.

## Recovered billing code

A full working implementation of Lemon Squeezy billing was written during the
Phase 2–6 build session and then removed because it was premature.

**It is preserved in git and can be restored.** Do not rewrite it from scratch.

### How to recover it

Run:
```bash
git show 314e1b5:apps/web/lib/lemonsqueezy.ts
git show 314e1b5:apps/web/app/api/webhook/lemonsqueezy/route.ts
git show 314e1b5:apps/web/app/api/billing/checkout/route.ts
git show 314e1b5:apps/web/app/api/billing/portal/route.ts
```

Or restore all four files at once:
```bash
git checkout 314e1b5 -- \
  apps/web/lib/lemonsqueezy.ts \
  apps/web/app/api/webhook/lemonsqueezy/route.ts \
  apps/web/app/api/billing/checkout/route.ts \
  apps/web/app/api/billing/portal/route.ts
```

### What was built

| File | What it does |
|---|---|
| `lib/lemonsqueezy.ts` | Checkout session creation, customer portal URL, HMAC webhook signature verification |
| `app/api/webhook/lemonsqueezy/route.ts` | Handles `order_created` (→ upgrade org to `solo`) and `subscription_cancelled` (→ revert to `trial`) |
| `app/api/billing/checkout/route.ts` | POST endpoint — creates a Solo plan checkout session for the authenticated user's org |
| `app/api/billing/portal/route.ts` | POST endpoint — returns the Lemon Squeezy customer portal URL |

### Settings page billing section

The settings page (`apps/web/app/dashboard/settings/page.tsx`) also needs a billing
section added in Phase 10. The full implementation (trial/solo/teams/enterprise states,
upgrade CTA, manage subscription button) was also in commit `314e1b5`:

```bash
git show 314e1b5:apps/web/app/dashboard/settings/page.tsx
```

### Environment variables to add in Phase 10

```
LEMONSQUEEZY_API_KEY=
LEMONSQUEEZY_WEBHOOK_SECRET=
NEXT_PUBLIC_LEMONSQUEEZY_STORE_ID=
LEMONSQUEEZY_SOLO_VARIANT_ID=
NEXT_PUBLIC_APP_URL=https://app.schemazero.com
```

### What Phase 10 still needs beyond the restored code

Per `build.md` Phase 10:
- Wire Lemon Squeezy customer creation on org creation (signup flow)
- Store `lemonsqueezy_customer_id` and `lemonsqueezy_subscription_id` on `organizations` table
- Add billing section to settings page (restore from commit above)
- Add `lemonsqueezy_customer_id` and `lemonsqueezy_subscription_id` columns to `organizations` if not already in schema
- Teams / Enterprise: contact form only — no Lemon Squeezy price, routes to Jordan agent with `CREATE_LEAD`
