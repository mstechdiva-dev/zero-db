import crypto from "crypto";

const LS_API_BASE = "https://api.lemonsqueezy.com/v1";
const API_KEY = process.env.LEMONSQUEEZY_API_KEY!;
const STORE_ID = process.env.NEXT_PUBLIC_LEMONSQUEEZY_STORE_ID!;
const SOLO_VARIANT_ID = process.env.LEMONSQUEEZY_SOLO_VARIANT_ID!;
const WEBHOOK_SECRET = process.env.LEMONSQUEEZY_WEBHOOK_SECRET!;

function lsHeaders() {
  return {
    Accept: "application/vnd.api+json",
    "Content-Type": "application/vnd.api+json",
    Authorization: `Bearer ${API_KEY}`,
  };
}

// Create a Lemon Squeezy checkout URL for the Solo plan.
// org_id is passed as custom data so the webhook can identify the org.
export async function createCheckoutUrl(email: string, orgId: string): Promise<string> {
  const res = await fetch(`${LS_API_BASE}/checkouts`, {
    method: "POST",
    headers: lsHeaders(),
    body: JSON.stringify({
      data: {
        type: "checkouts",
        attributes: {
          checkout_data: {
            email,
            custom: { org_id: orgId },
          },
        },
        relationships: {
          store: { data: { type: "stores", id: STORE_ID } },
          variant: { data: { type: "variants", id: SOLO_VARIANT_ID } },
        },
      },
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Lemon Squeezy checkout failed: ${err}`);
  }

  const data = await res.json();
  return data.data.attributes.url as string;
}

// Verify a Lemon Squeezy webhook signature.
// Header: X-Signature (hex HMAC-SHA256 of raw body with webhook secret)
export function verifyWebhookSignature(rawBody: string, signature: string): boolean {
  if (!WEBHOOK_SECRET) return false;
  const expected = crypto
    .createHmac("sha256", WEBHOOK_SECRET)
    .update(rawBody, "utf8")
    .digest("hex");
  try {
    return crypto.timingSafeEqual(
      Buffer.from(expected, "hex"),
      Buffer.from(signature.toLowerCase(), "hex")
    );
  } catch {
    return false;
  }
}
