"use client";

import { useEffect, useState, useCallback } from "react";
import { createClient } from "@/lib/supabase";

interface AlertConfig {
  slack_webhook_url: string;
  pagerduty_api_key: string;
  webhook_url: string;
  email_recipients: string[];
  notify_on: string[];
}

interface OrgBilling {
  plan: string;
  trial_ends_at: string;
  trial_converted: boolean;
  lemonsqueezy_customer_portal_url: string | null;
}

const ALL_RISK_LEVELS = ["low", "medium", "high", "critical"];

function trialDaysLeft(endsAt: string): number {
  return Math.max(0, Math.ceil((new Date(endsAt).getTime() - Date.now()) / 86_400_000));
}

export default function SettingsPage() {
  const [alertConfig, setAlertConfig] = useState<AlertConfig>({
    slack_webhook_url: "",
    pagerduty_api_key: "",
    webhook_url: "",
    email_recipients: [],
    notify_on: ["high", "critical"],
  });
  const [emailInput, setEmailInput] = useState("");
  const [billing, setBilling] = useState<OrgBilling | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [checkingOut, setCheckingOut] = useState(false);
  const [urlErrors, setUrlErrors] = useState<Record<string, string>>({});
  const [testing, setTesting] = useState(false);
  const [testResults, setTestResults] = useState<Record<string, { ok: boolean; status?: number; error?: string }> | null>(null);

  const loadSettings = useCallback(async () => {
    const supabase = createClient();
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return;

    const { data: userData } = await supabase
      .from("users")
      .select("org_id")
      .eq("auth_user_id", user.id)
      .single();
    if (!userData) return;

    const [{ data: configData }, { data: orgData }] = await Promise.all([
      supabase.from("alert_configs").select("*").eq("org_id", userData.org_id).single(),
      supabase
        .from("organizations")
        .select("plan, trial_ends_at, trial_converted, lemonsqueezy_customer_portal_url")
        .eq("id", userData.org_id)
        .single(),
    ]);

    if (configData) {
      setAlertConfig({
        slack_webhook_url: configData.slack_webhook_url ?? "",
        pagerduty_api_key: configData.pagerduty_api_key ?? "",
        webhook_url: configData.webhook_url ?? "",
        email_recipients: configData.email_recipients ?? [],
        notify_on: configData.notify_on ?? ["high", "critical"],
      });
      setEmailInput((configData.email_recipients ?? []).join(", "));
    }

    if (orgData) setBilling(orgData as OrgBilling);
  }, []);

  useEffect(() => { loadSettings(); }, [loadSettings]);

  function validateUrl(value: string): boolean {
    if (!value) return true;
    try {
      const u = new URL(value);
      return u.protocol === "https:" || u.protocol === "http:";
    } catch {
      return false;
    }
  }

  async function saveAlertConfig() {
    const errors: Record<string, string> = {};
    if (!validateUrl(alertConfig.webhook_url)) {
      errors.webhook_url = "Must be a valid URL (https://…)";
    }
    if (!validateUrl(alertConfig.slack_webhook_url)) {
      errors.slack_webhook_url = "Must be a valid URL (https://hooks.slack.com/…)";
    }
    if (Object.keys(errors).length > 0) {
      setUrlErrors(errors);
      return;
    }
    setUrlErrors({});
    setSaving(true);
    setSaved(false);
    try {
      const supabase = createClient();
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;

      const { data: userData } = await supabase
        .from("users")
        .select("org_id")
        .eq("auth_user_id", user.id)
        .single();
      if (!userData) return;

      const emails = emailInput.split(/[,\s]+/).map((e) => e.trim()).filter(Boolean);

      const { error } = await supabase.from("alert_configs").upsert({
        org_id: userData.org_id,
        slack_webhook_url: alertConfig.slack_webhook_url || null,
        pagerduty_api_key: alertConfig.pagerduty_api_key || null,
        webhook_url: alertConfig.webhook_url || null,
        email_recipients: emails,
        notify_on: alertConfig.notify_on,
      });

      if (error) throw error;
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error("Failed to save alert config:", err);
    } finally {
      setSaving(false);
    }
  }

  async function handleUpgrade() {
    setCheckingOut(true);
    try {
      const res = await fetch("/api/checkout", { method: "POST" });
      const data = await res.json();
      if (data.url) window.location.href = data.url;
    } catch (err) {
      console.error("Checkout failed:", err);
    } finally {
      setCheckingOut(false);
    }
  }

  async function sendTest() {
    setTesting(true);
    setTestResults(null);
    try {
      const res = await fetch("/api/webhook/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // Pass current form values so unsaved edits are tested correctly
        body: JSON.stringify({
          webhook_url: alertConfig.webhook_url || undefined,
          slack_webhook_url: alertConfig.slack_webhook_url || undefined,
        }),
      });
      let data: { results?: Record<string, { ok: boolean; status?: number; error?: string }>; error?: string } | null = null;
      try { data = await res.json(); } catch { /* non-JSON body */ }

      if (!res.ok) {
        setTestResults({ error: { ok: false, error: data?.error ?? `Request failed (${res.status})` } });
        return;
      }
      if (data?.results) {
        setTestResults(data.results);
        setTimeout(() => setTestResults(null), 8000);
      } else {
        setTestResults({ error: { ok: false, error: "Unexpected response from test endpoint" } });
      }
    } catch {
      setTestResults({ error: { ok: false, error: "Request failed" } });
    } finally {
      setTesting(false);
    }
  }

  function toggleRiskLevel(level: string) {
    setAlertConfig((prev) => ({
      ...prev,
      notify_on: prev.notify_on.includes(level)
        ? prev.notify_on.filter((l) => l !== level)
        : [...prev.notify_on, level],
    }));
  }

  const daysLeft = billing ? trialDaysLeft(billing.trial_ends_at) : 0;
  const isTrialActive = billing?.plan === "trial" && daysLeft > 0 && !billing.trial_converted;
  const isSolo = billing?.plan === "solo" || billing?.trial_converted;
  const isTeams = billing?.plan === "teams";
  const isEnterprise = billing?.plan === "enterprise";

  return (
    <div className="space-y-8 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-gray-400 mt-1">Manage billing and alerts</p>
      </div>

      {/* Billing section */}
      <section className="bg-[#111] border border-gray-800 rounded-xl p-6 space-y-4">
        <h2 className="text-lg font-semibold text-white">Billing</h2>

        {billing && (
          <div className="flex items-center gap-3">
            <span className={`text-xs font-mono font-bold px-2 py-1 rounded border uppercase ${
              isSolo ? "text-[#00e87a] bg-[#00e87a]/10 border-[#00e87a]/30" :
              isTeams ? "text-purple-400 bg-purple-400/10 border-purple-400/30" :
              isEnterprise ? "text-yellow-400 bg-yellow-400/10 border-yellow-400/30" :
              "text-blue-400 bg-blue-400/10 border-blue-400/30"
            }`}>
              {isSolo ? "Solo" : isTeams ? "Teams" : isEnterprise ? "Enterprise" : `Trial — ${daysLeft}d left`}
            </span>
            {isSolo && <span className="text-sm text-gray-500">$19/mo</span>}
            {isTeams && <span className="text-sm text-gray-500">$79/mo</span>}
          </div>
        )}

        {isTrialActive && (
          <div className="space-y-3">
            <p className="text-sm text-gray-400">
              {daysLeft} day{daysLeft !== 1 ? "s" : ""} remaining on your free trial.
            </p>
            <button
              onClick={handleUpgrade}
              disabled={checkingOut}
              className="px-4 py-2 bg-[#00e87a] text-black font-semibold rounded-lg hover:bg-[#00c96a] transition-colors text-sm disabled:opacity-50"
            >
              {checkingOut ? "Redirecting…" : "Upgrade to Solo — $19/mo"}
            </button>
          </div>
        )}

        {isSolo && (
          <div className="space-y-3">
            <p className="text-sm text-gray-400">Solo plan · 2 databases · 1 seat</p>
            {billing?.lemonsqueezy_customer_portal_url ? (
              <a
                href={billing.lemonsqueezy_customer_portal_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block px-4 py-2 border border-gray-700 text-gray-300 hover:text-white hover:border-gray-500 rounded-lg transition-colors text-sm"
              >
                Manage subscription
              </a>
            ) : (
              <p className="text-xs text-gray-600">
                To manage your subscription, visit your Lemon Squeezy account.
              </p>
            )}
          </div>
        )}

        {(isTeams || isEnterprise) && (
          <p className="text-sm text-gray-400">
            To make changes to your plan, email{" "}
            <a href="mailto:hello@schemazero.com" className="text-[#00e87a] hover:underline">
              hello@schemazero.com
            </a>
          </p>
        )}
      </section>

      {/* Alert config section */}
      <section className="bg-[#111] border border-gray-800 rounded-xl p-6 space-y-6">
        <h2 className="text-lg font-semibold text-white">Alert Configuration</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">
              Custom Webhook URL{" "}
              <span className="text-gray-600 text-xs">(fired first, before all other channels)</span>
            </label>
            <input
              type="url"
              value={alertConfig.webhook_url}
              onChange={(e) => {
                setAlertConfig((p) => ({ ...p, webhook_url: e.target.value }));
                setUrlErrors((p) => ({ ...p, webhook_url: "" }));
              }}
              placeholder="https://your-server.com/webhook"
              className={`w-full px-4 py-3 bg-[#0a0a0a] border rounded-lg text-white placeholder-gray-600 focus:outline-none transition-colors ${
                urlErrors.webhook_url ? "border-red-500 focus:border-red-400" : "border-gray-800 focus:border-[#00e87a]"
              }`}
            />
            {urlErrors.webhook_url && (
              <p className="text-red-400 text-xs mt-1">{urlErrors.webhook_url}</p>
            )}
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Slack Webhook URL</label>
            <input
              type="url"
              value={alertConfig.slack_webhook_url}
              onChange={(e) => {
                setAlertConfig((p) => ({ ...p, slack_webhook_url: e.target.value }));
                setUrlErrors((p) => ({ ...p, slack_webhook_url: "" }));
              }}
              placeholder="https://hooks.slack.com/services/..."
              className={`w-full px-4 py-3 bg-[#0a0a0a] border rounded-lg text-white placeholder-gray-600 focus:outline-none transition-colors ${
                urlErrors.slack_webhook_url ? "border-red-500 focus:border-red-400" : "border-gray-800 focus:border-[#00e87a]"
              }`}
            />
            {urlErrors.slack_webhook_url && (
              <p className="text-red-400 text-xs mt-1">{urlErrors.slack_webhook_url}</p>
            )}
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">PagerDuty Integration Key</label>
            <input
              type="password"
              value={alertConfig.pagerduty_api_key}
              onChange={(e) => setAlertConfig((p) => ({ ...p, pagerduty_api_key: e.target.value }))}
              placeholder="••••••••••••••••"
              className="w-full px-4 py-3 bg-[#0a0a0a] border border-gray-800 rounded-lg text-white placeholder-gray-600 focus:outline-none focus:border-[#00e87a] transition-colors"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">
              Email recipients{" "}
              <span className="text-gray-600 text-xs">(comma-separated)</span>
            </label>
            <input
              type="text"
              value={emailInput}
              onChange={(e) => setEmailInput(e.target.value)}
              placeholder="ops@company.com, dev@company.com"
              className="w-full px-4 py-3 bg-[#0a0a0a] border border-gray-800 rounded-lg text-white placeholder-gray-600 focus:outline-none focus:border-[#00e87a] transition-colors"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Alert on risk levels</label>
            <div className="flex gap-3">
              {ALL_RISK_LEVELS.map((level) => (
                <label key={level} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={alertConfig.notify_on.includes(level)}
                    onChange={() => toggleRiskLevel(level)}
                    className="accent-[#00e87a]"
                  />
                  <span className="text-sm text-gray-300 capitalize">{level}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <button
              onClick={saveAlertConfig}
              disabled={saving}
              className="px-4 py-2 bg-[#00e87a] text-black font-semibold rounded-lg hover:bg-[#00c96a] transition-colors text-sm disabled:opacity-50"
            >
              {saving ? "Saving…" : saved ? "Saved ✓" : "Save alert config"}
            </button>
            {(alertConfig.webhook_url || alertConfig.slack_webhook_url) && (
              <button
                onClick={sendTest}
                disabled={testing}
                className="px-4 py-2 border border-gray-700 text-gray-300 hover:text-white hover:border-gray-500 rounded-lg transition-colors text-sm disabled:opacity-50"
              >
                {testing ? "Sending…" : "Send test"}
              </button>
            )}
          </div>

          {testResults && (
            <div className="flex flex-wrap gap-2 pt-1">
              {Object.entries(testResults).map(([channel, result]) => (
                <span
                  key={channel}
                  className={`text-xs font-mono px-2 py-1 rounded border ${
                    result.ok
                      ? "text-[#00e87a] bg-[#00e87a]/10 border-[#00e87a]/30"
                      : "text-red-400 bg-red-400/10 border-red-400/30"
                  }`}
                >
                  {channel}: {result.ok ? `✓ ${result.status}` : `✗ ${result.error ?? result.status}`}
                </span>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
