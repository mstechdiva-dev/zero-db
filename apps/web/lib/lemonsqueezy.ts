/**
 * Lemon Squeezy client for SchemaZero billing.
 *
 * Solo plan: $19/mo — self-serve via Lemon Squeezy checkout.
 * Teams / Enterprise: Contact form only — no Lemon Squeezy price.
 */

const LEMONSQUEEZY_API_BASE = "https://api.lemonsqueezy.com/v1";

const STORE_ID = process.env.NEXT_PUBLIC_LEMONSQUEEZY_STORE_ID!;
const API_KEY = process.env.LEMONSQUEEZY_API_KEY!;

// Solo plan variant ID — set this to your actual Lemon Squeezy variant ID
const SOLO_VARIANT_ID = process.env.LEMONSQUEEZY_SOLO_VARIANT_ID!;

interface CreateCheckoutOptions {
  email: string;
  orgId: string;
  /** Redirect URL after successful checkout */
  successUrl?: string;
}

interface LemonSqueezyCheckout {
  checkoutUrl: string;
}

/**
 * Create a Lemon Squeezy checkout session for the Solo plan.
 * Returns the checkout URL to redirect the user to.
 */
export async function createSoloCheckout({
  email,
  orgId,
  successUrl = `${process.env.NEXT_PUBLIC_APP_URL ?? ""}/dashboard?upgraded=true`,
}: CreateCheckoutOptions): Promise<LemonSqueezyCheckout> {
  if (!API_KEY || !STORE_ID || !SOLO_VARIANT_ID) {
    throw new Error("Lemon Squeezy environment variables are not configured");
  }

  const res = await fetch(`${LEMONSQUEEZY_API_BASE}/checkouts`, {
    method: "POST",
    headers: {
      Accept: "application/vnd.api+json",
      "Content-Type": "application/vnd.api+json",
      Authorization: `Bearer ${API_KEY}`,
    },
    body: JSON.stringify({
      data: {
        type: "checkouts",
        attributes: {
          checkout_options: {
            embed: false,
          },
          checkout_data: {
            email,
            custom: {
              org_id: orgId,
            },
          },
          product_options: {
            redirect_url: successUrl,
          },
        },
        relationships: {
          store: {
            data: { type: "stores", id: STORE_ID },
          },
          variant: {
            data: { type: "variants", id: SOLO_VARIANT_ID },
          },
        },
      },
    }),
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`Lemon Squeezy checkout creation failed: ${error}`);
  }

  const data = await res.json();
  const checkoutUrl = data?.data?.attributes?.url;
  if (!checkoutUrl) {
    throw new Error("Lemon Squeezy did not return a checkout URL");
  }

  return { checkoutUrl };
}

/**
 * Create a Lemon Squeezy customer portal URL for subscription management.
 */
export async function getCustomerPortalUrl(
  customerId: string
): Promise<string> {
  if (!API_KEY) {
    throw new Error("LEMONSQUEEZY_API_KEY is not set");
  }

  const res = await fetch(
    `${LEMONSQUEEZY_API_BASE}/customers/${customerId}`,
    {
      headers: {
        Accept: "application/vnd.api+json",
        Authorization: `Bearer ${API_KEY}`,
      },
    }
  );

  if (!res.ok) {
    throw new Error("Failed to fetch Lemon Squeezy customer");
  }

  const data = await res.json();
  return data?.data?.attributes?.urls?.customer_portal ?? "";
}

/**
 * Verify a Lemon Squeezy webhook signature.
 *
 * Lemon Squeezy signs webhooks with HMAC-SHA256 using the signing secret
 * configured in your store's webhook settings. The signature is sent in
 * the X-Signature header as a hex digest.
 */
export async function verifyWebhookSignature(
  rawBody: string,
  signature: string,
  secret: string
): Promise<boolean> {
  const encoder = new TextEncoder();
  const keyData = encoder.encode(secret);
  const messageData = encoder.encode(rawBody);

  const cryptoKey = await crypto.subtle.importKey(
    "raw",
    keyData,
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );

  const signatureBuffer = await crypto.subtle.sign("HMAC", cryptoKey, messageData);
  const expectedHex = Array.from(new Uint8Array(signatureBuffer))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");

  return expectedHex === signature;
}
