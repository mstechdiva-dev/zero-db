import crypto from "crypto";

/**
 * Verifies a Lemon Squeezy webhook signature.
 * LemonSqueezy signs the raw request body with HMAC-SHA256 using the webhook secret.
 */
export function verifyLemonSqueezyWebhook(
  rawBody: string,
  signature: string,
  secret: string
): boolean {
  const digest = crypto
    .createHmac("sha256", secret)
    .update(rawBody)
    .digest("hex");
  try {
    return crypto.timingSafeEqual(
      Buffer.from(digest, "hex"),
      Buffer.from(signature, "hex")
    );
  } catch {
    return false;
  }
}
