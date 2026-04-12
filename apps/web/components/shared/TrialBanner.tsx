"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase";

export default function TrialBanner() {
  const [daysLeft, setDaysLeft] = useState<number | null>(null);
  const [isPaid, setIsPaid] = useState(false);

  useEffect(() => {
    const supabase = createClient();

    async function fetchTrialStatus() {
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

      const { data: org } = await supabase
        .from("organizations")
        .select("plan, trial_ends_at, trial_converted")
        .eq("id", userData.org_id)
        .single();

      if (!org) return;

      if (org.plan !== "trial" || org.trial_converted) {
        setIsPaid(true);
        return;
      }

      const msLeft = new Date(org.trial_ends_at).getTime() - Date.now();
      setDaysLeft(Math.max(0, Math.ceil(msLeft / (1000 * 60 * 60 * 24))));
    }

    fetchTrialStatus();
  }, []);

  if (isPaid || daysLeft === null) return null;

  const isUrgent = daysLeft <= 3;

  return (
    <div
      className={`px-6 py-2.5 flex items-center justify-between text-sm ${
        isUrgent
          ? "bg-orange-400/10 border-b border-orange-400/20"
          : "bg-[#00e87a]/5 border-b border-[#00e87a]/10"
      }`}
    >
      <span className={isUrgent ? "text-orange-400" : "text-gray-400"}>
        {daysLeft === 0
          ? "Your trial has expired."
          : `${daysLeft} day${daysLeft === 1 ? "" : "s"} left in your trial.`}
      </span>
      <a
        href="/dashboard/settings"
        className={`font-semibold text-xs px-3 py-1 rounded-lg transition-colors ${
          isUrgent
            ? "bg-orange-400 text-black hover:bg-orange-300"
            : "bg-[#00e87a] text-black hover:bg-[#00c96a]"
        }`}
      >
        Upgrade to Solo — $19/mo
      </a>
    </div>
  );
}
