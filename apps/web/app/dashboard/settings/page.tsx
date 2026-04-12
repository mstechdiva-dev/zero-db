"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase";

type Plan = "trial" | "solo" | "teams" | "enterprise";

interface OrgData {
  id: string;
  plan: Plan;
  trial_ends_at: string | null;
  trial_converted: boolean;
  lemonsqueezy_customer_id: string | null;
}

interface AlertConfig {
  slack_webhook_url: string;
  pagerduty_api_key: string;
  webhook_url: string;
  email_recipients: string[];
  notify_on: string[];
}

const ALL_RISK_LEVELS = ["low", "medium", "high", "critical"];

export default function SettingsPage() {
  const [org, setOrg] = useState<OrgData | null>(null);
  const [alertConfig, setAlertConfig] = useState<AlertConfig>({
    slack_webhook_url: "",
    pagerduty_api_key: "",
    webhook_url: "",
    email_recipients: [],
    notify_on: ["high", "critical"],
  });
  const [emailInput, setEmailInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [trialDaysLeft, setTrialDaysLeft] = useState<number | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    const supabase = createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) return;

    const { data: userData } = await supabase
      .from("users")
      .select("org_id")
      .eq("auth_user_id", user.id)
      .single();
    if (!userData) return;

    const { data: orgData } = await supabase
      .from("organizations")
      .select("id, plan, trial_ends_at, trial_converted, lemonsqueezy_customer_id")
      .eq("id", userData.org_id)
      .single();
    if (orgData) {
      setOrg(orgData);
      if (orgData.plan === "trial" && orgData.trial_ends_at) {
        const msLeft = new Date(orgData.trial_ends_at).getTime() - Date.now();
        setTrialDaysLeft(Math.max(0, Math.ceil(msLeft / (1000 * 60 * 60 * 24))));
      }
    }

    const { data: configData } = await supabase
      .from("alert_configs")
      .select("*")
      .eq("org_id", userData.org_id)
      .single();
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
  }

  async function saveAlertConfig() {
    setSaving(true);
    setSaved(false);
    const supabase = createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) return;

    const { data: userData } = await supabase
      .from("users")
      .select("org_id")
      .eq("auth_user_id", user.id)
      .single();
    if (!userData) return;

    const emails = emailInput
      .split(/[,\s]+/)
      .map((e) => e.trim())
      .filter(Boolean);

    await supabase.from("alert_configs").upsert({
      org_id: userData.org_id,
      slack_webhook_url: alertConfig.slack_webhook_url || null,
      pagerduty_api_key: alertConfig.pagerduty_api_key || null,
      webhook_url: alertConfig.webhook_url || null,
      email_recipients: emails,
      notify_on: alertConfig.notify_on,
    });

    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  }

  function toggleRiskLevel(level: string) {
    setAlertConfig((prev) => ({
      ...prev,
      notify_on: prev.notify_on.includes(level)
        ? prev.notify_on.filter((l) => l !== level)
        : [...prev.notify_on, level],
    }));
  }

  async function handleUpgrade() {
    setCheckoutLoading(true);
    try {
      const res = await fetch("/api/billing/checkout", { method: "POST" });
      if (!res.ok) throw new Error("Failed to create checkout");
      const { checkoutUrl } = await res.json();
      window.location.href = checkoutUrl;
    } catch {
      setCheckoutLoading(false);
    }
  }

  async function handleManageSubscription() {
    if (!org?.lemonsqueezy_customer_id) return;
    setCheckoutLoading(true);
    try {
      const res = await fetch("/api/billing/portal", { method: "POST" });
      if (!res.ok) throw new Error("Failed to get portal URL");
      const { portalUrl } = await res.json();
      window.location.href = portalUrl;
    } catch {
      setCheckoutLoading(false);
    }
  }

  return (
    <div className="space-y-8 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-gray-400 mt-1">Manage alerts, billing, and your account</p>
      </div>

      {/* Billing Section */}
      <section className="bg-[#111] border border-gray-800 rounded-xl p-6 space-y-4">
        <h2 className="text-lg font-semibold text-white">Billing</h2>

        {org?.plan === "trial" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white font-medium">Free Trial</p>
                <p className="text-gray-400 text-sm mt-0.5">
                  {trialDaysLeft === null
                    ? "Loading…"
                    : trialDaysLeft === 0
                    ? "Your trial has expired."
                    : `${trialDaysLeft} day${trialDaysLeft === 1 ? "" : "s"} remaining`}
                </p>
              </div>
              <span className="px-2 py-1 bg-[#00e87a]/10 text-[#00e87a] text-xs font-semibold rounded">
                TRIAL
              </span>
            </div>
            <button
              onClick={handleUpgrade}
              disabled={checkoutLoading}
              className="w-full py-3 bg-[#00e87a] text-black font-semibold rounded-lg hover:bg-[#00c96a] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {checkoutLoading ? "Redirecting…" : "Upgrade to Solo — $19/mo"}
            </button>
            <p className="text-gray-500 text-xs">
              Solo: 1 seat, 1 database, full access. Cancel any time.
            </p>
            <div className="border-t border-gray-800 pt-4">
              <p className="text-gray-400 text-sm mb-2">Need more databases or seats?</p>
              <a
                href="mailto:hello@schemazero.com?subject=Teams%20inquiry"
                className="text-[#00e87a] text-sm hover:underline"
              >
                Contact us for Teams or Enterprise pricing →
              </a>
            </div>
          </div>
        )}

        {org?.plan === "solo" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white font-medium">Solo — $19/mo</p>
                <p className="text-gray-400 text-sm mt-0.5">Active subscription</p>
              </div>
              <span className="px-2 py-1 bg-[#00e87a]/10 text-[#00e87a] text-xs font-semibold rounded">
                SOLO
              </span>
            </div>
            <button
              onClick={handleManageSubscription}
              disabled={checkoutLoading}
              className="px-4 py-2 border border-gray-700 text-gray-300 font-medium rounded-lg hover:border-gray-500 transition-colors disabled:opacity-50 text-sm"
            >
              {checkoutLoading ? "Redirecting…" : "Manage Subscription"}
            </button>
          </div>
        )}

        {(org?.plan === "teams" || org?.plan === "enterprise") && (
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white font-medium capitalize">{org.plan} Plan</p>
              <p className="text-gray-400 text-sm mt-0.5">Managed by your account team</p>
            </div>
            <span className="px-2 py-1 bg-purple-500/10 text-purple-400 text-xs font-semibold rounded uppercase">
              {org.plan}
            </span>
          </div>
        )}
      </section>

      {/* Alert Configuration */}
      <section className="bg-[#111] border border-gray-800 rounded-xl p-6 space-y-6">
        <h2 className="text-lg font-semibold text-white">Alert Configuration</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">
              Custom Webhook URL{" "}
              <span className="text-gray-600 text-xs">(fired first, for all risk levels)</span>
            </label>
            <input
              type="url"
              value={alertConfig.webhook_url}
              onChange={(e) =>
                setAlertConfig((p) => ({ ...p, webhook_url: e.target.value }))
              }
              placeholder="https://your-server.com/webhook"
              className="w-full px-4 py-3 bg-[#0a0a0a] border border-gray-800 rounded-lg text-white placeholder-gray-600 focus:outline-none focus:border-[#00e87a] transition-colors"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Slack Webhook URL</label>
            <input
              type="url"
              value={alertConfig.slack_webhook_url}
              onChange={(e) =>
                setAlertConfig((p) => ({ ...p, slack_webhook_url: e.target.value }))
              }
              placeholder="https://hooks.slack.com/services/..."
              className="w-full px-4 py-3 bg-[#0a0a0a] border border-gray-800 rounded-lg text-white placeholder-gray-600 focus:outline-none focus:border-[#00e87a] transition-colors"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">
              PagerDuty Integration Key
            </label>
            <input
              type="password"
              value={alertConfig.pagerduty_api_key}
              onChange={(e) =>
                setAlertConfig((p) => ({ ...p, pagerduty_api_key: e.target.value }))
              }
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

          <button
            onClick={saveAlertConfig}
            disabled={saving}
            className="px-4 py-2 bg-[#00e87a] text-black font-semibold rounded-lg hover:bg-[#00c96a] transition-colors text-sm disabled:opacity-50"
          >
            {saving ? "Saving…" : saved ? "Saved ✓" : "Save alert config"}
          </button>
        </div>
      </section>
    </div>
  );
}
