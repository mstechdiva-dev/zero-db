"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase";

interface AlertConfig {
  slack_webhook_url: string;
  pagerduty_api_key: string;
  webhook_url: string;
  email_recipients: string[];
  notify_on: string[];
}

const ALL_RISK_LEVELS = ["low", "medium", "high", "critical"];

export default function SettingsPage() {
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

  useEffect(() => {
    loadAlertConfig();
  }, []);

  async function loadAlertConfig() {
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

  return (
    <div className="space-y-8 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-gray-400 mt-1">Manage alerts and team members</p>
      </div>

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
