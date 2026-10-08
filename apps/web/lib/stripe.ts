import Stripe from "stripe";
import { createClient } from "@supabase/supabase-js";

let client: Stripe | null = null;

export function stripeConfigured(): boolean {
  return Boolean(process.env.STRIPE_SECRET_KEY);
}

export function getStripe(): Stripe {
  const key = process.env.STRIPE_SECRET_KEY;
  if (!key) throw new Error("STRIPE_SECRET_KEY is not set");
  if (!client) {
    // STRIPE_API_BASE_URL lets tests point at a local fake Stripe. Leave it unset.
    const base = process.env.STRIPE_API_BASE_URL;
    if (base) {
      const u = new URL(base);
      client = new Stripe(key, {
        host: u.hostname,
        port: u.port || undefined,
        protocol: u.protocol === "https:" ? "https" : "http",
      });
    } else {
      client = new Stripe(key);
    }
  }
  return client;
}

// Subscription states that mean "paying", and states that mean "over".
// Anything else (past_due, incomplete, paused) leaves the plan alone: Stripe retries.
export const PAYING_STATUSES = ["active", "trialing"];
export const ENDED_STATUSES = ["canceled", "unpaid", "incomplete_expired"];

export function serviceDb() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false } }
  );
}

// Stripe returns an id string, an expanded object, or null.
export function idOf(value: string | { id: string } | null | undefined): string | null {
  if (!value) return null;
  return typeof value === "string" ? value : value.id;
}
