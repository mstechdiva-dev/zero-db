import { NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";
import { createClient } from "@supabase/supabase-js";

function serviceDb() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false } }
  );
}

const PRIVATE_HOSTNAME = /^(localhost|.*\.local)$|^(127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|169\.254\.|0\.|::1$|fc00:|fe80:)/i;
const AWS_METADATA = /169\.254\.169\.254|metadata\.google\.internal/i;

function isSafeUrl(raw: string): { ok: true; url: URL } | { ok: false; reason: string } {
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    return { ok: false, reason: "Invalid URL" };
  }
  if (url.protocol !== "https:") {
    return { ok: false, reason: "Only https:// URLs are allowed" };
  }
  if (PRIVATE_HOSTNAME.test(url.hostname) || AWS_METADATA.test(url.hostname)) {
    return { ok: false, reason: "URL targets a private or reserved address" };
  }
  return { ok: true, url };
}

function isValidSlackUrl(raw: string): boolean {
  try {
    const u = new URL(raw);
    return u.hostname === "hooks.slack.com";
  } catch {
    return false;
  }
}

const TEST_PAYLOAD = {
  event: "schema.change",
  test: true,
  change: {
    id: "test-00000000-0000-0000-0000-000000000000",
    change_type: "column_dropped",
    object_type: "column",
    object_name: "users.email",
    schema_name: "public",
    risk_level: "high",
    detected_at: new Date().toISOString(),
  },
};

const SLACK_TEST_PAYLOAD = {
  text: "SchemaZero test alert",
  blocks: [
    {
      type: "section",
      text: {
        type: "mrkdwn",
        text: "*SchemaZero — Test Alert*\nThis is a test notification from SchemaZero. Your Slack integration is working correctly.",
      },
    },
    {
      type: "context",
      elements: [{ type: "mrkdwn", text: `Sent at ${new Date().toLocaleString()}` }],
    },
  ],
};

export async function POST(request: NextRequest) {
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { cookies: { getAll: () => request.cookies.getAll(), setAll: () => {} } }
  );

  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  // Caller may pass URL overrides (current form values, not yet saved)
  let bodyUrls: { webhook_url?: string; slack_webhook_url?: string } = {};
  try {
    bodyUrls = await request.json();
  } catch {
    // no body is fine — fall back to saved config
  }

  let webhookUrl = bodyUrls.webhook_url?.trim() || null;
  let slackUrl = bodyUrls.slack_webhook_url?.trim() || null;

  // If caller didn't provide URLs, load saved config from DB
  if (!webhookUrl && !slackUrl) {
    const db = serviceDb();

    const { data: userData, error: userError } = await db
      .from("users")
      .select("org_id")
      .eq("auth_user_id", user.id)
      .single();
    if (userError) {
      if (userError.code === "PGRST116") {
        return NextResponse.json({ error: "User not found" }, { status: 404 });
      }
      return NextResponse.json({ error: "Failed to load user", details: userError.message }, { status: 500 });
    }

    const { data: config, error: configError } = await db
      .from("alert_configs")
      .select("webhook_url, slack_webhook_url")
      .eq("org_id", userData.org_id)
      .single();
    if (configError && configError.code !== "PGRST116") {
      return NextResponse.json({ error: "Failed to load alert config", details: configError.message }, { status: 500 });
    }

    webhookUrl = config?.webhook_url ?? null;
    slackUrl = config?.slack_webhook_url ?? null;
  }

  if (!webhookUrl && !slackUrl) {
    return NextResponse.json({ error: "No webhook URLs configured" }, { status: 400 });
  }

  const results: Record<string, { ok: boolean; status?: number; error?: string }> = {};

  if (webhookUrl) {
    const safe = isSafeUrl(webhookUrl);
    if (!safe.ok) {
      results.webhook = { ok: false, error: safe.reason };
    } else {
      try {
        const res = await fetch(safe.url.toString(), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(TEST_PAYLOAD),
          redirect: "error",
          signal: AbortSignal.timeout(8000),
        });
        results.webhook = { ok: res.ok, status: res.status };
      } catch (err) {
        results.webhook = { ok: false, error: err instanceof Error ? err.message : "Request failed" };
      }
    }
  }

  if (slackUrl) {
    const safe = isSafeUrl(slackUrl);
    if (!safe.ok) {
      results.slack = { ok: false, error: safe.reason };
    } else if (!isValidSlackUrl(slackUrl)) {
      results.slack = { ok: false, error: "Must be a hooks.slack.com URL" };
    } else {
      try {
        const res = await fetch(safe.url.toString(), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(SLACK_TEST_PAYLOAD),
          redirect: "error",
          signal: AbortSignal.timeout(8000),
        });
        results.slack = { ok: res.ok, status: res.status };
      } catch (err) {
        results.slack = { ok: false, error: err instanceof Error ? err.message : "Request failed" };
      }
    }
  }

  return NextResponse.json({ results });
}
