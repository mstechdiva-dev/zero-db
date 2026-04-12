import { cookies } from "next/headers";
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

  if (user) {
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

        if (
          org &&
          org.plan === "trial" &&
          !org.trial_converted &&
          org.trial_ends_at &&
          new Date(org.trial_ends_at) < new Date()
        ) {
          redirect("/dashboard/settings?trial_expired=true");
        }
      }
    } catch {
      // If trial check fails, let them through — don't block on a DB error
    }
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
