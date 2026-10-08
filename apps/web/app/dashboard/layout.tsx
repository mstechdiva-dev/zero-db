import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { createServerClient } from "@supabase/ssr";
import Sidebar from "@/components/dashboard/Sidebar";
import TrialBanner from "@/components/shared/TrialBanner";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const cookieStore = await cookies();

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll() {
          // Server components cannot set cookies; handled by middleware
        },
      },
    }
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  // Settings must stay reachable when blocked, so people can upgrade (no redirect loop).
  const onSettings = ((await headers()).get("x-pathname") ?? "").startsWith("/dashboard/settings");

  if (user && !onSettings) {
    let blocked: "expired" | "check_failed" | null = null;
    try {
      const { data: userData } = await supabase
        .from("users")
        .select("org_id")
        .eq("auth_user_id", user.id)
        .single();

      if (userData?.org_id) {
        const { data: org } = await supabase
          .from("organizations")
          .select("plan, trial_ends_at, trial_converted")
          .eq("id", userData.org_id)
          .single();

        if (!org) {
          blocked = "check_failed";
        } else if (
          org.plan === "trial" &&
          !org.trial_converted &&
          (!org.trial_ends_at || new Date(org.trial_ends_at) < new Date())
        ) {
          blocked = "expired";
        }
      } else {
        blocked = "check_failed";
      }
    } catch (err) {
      // We couldn't prove the plan, so don't let them through.
      console.error("Plan check failed", err);
      blocked = "check_failed";
    }
    // redirect() works by throwing, so it must stay outside the try/catch above
    // (inside it, the catch swallowed the redirect and nobody was ever cut off).
    if (blocked === "expired") redirect("/dashboard/settings?trial_expired=true");
    if (blocked === "check_failed") redirect("/dashboard/settings?plan_check_failed=true");
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] flex">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TrialBanner />
        <main className="flex-1 p-8">{children}</main>
      </div>
    </div>
  );
}
