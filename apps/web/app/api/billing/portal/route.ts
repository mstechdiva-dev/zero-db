import { NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";
import { getCustomerPortalUrl } from "@/lib/lemonsqueezy";

export async function POST(request: NextRequest) {
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: () => {},
      },
    }
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const supabaseAdmin = (await import("@supabase/supabase-js")).createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );

  const { data: userData } = await supabaseAdmin
    .from("users")
    .select("org_id")
    .eq("auth_user_id", user.id)
    .single();

  if (!userData?.org_id) {
    return NextResponse.json({ error: "Organization not found" }, { status: 404 });
  }

  const { data: org } = await supabaseAdmin
    .from("organizations")
    .select("lemonsqueezy_customer_id")
    .eq("id", userData.org_id)
    .single();

  if (!org?.lemonsqueezy_customer_id) {
    return NextResponse.json({ error: "No Lemon Squeezy customer on file" }, { status: 404 });
  }

  try {
    const portalUrl = await getCustomerPortalUrl(org.lemonsqueezy_customer_id);
    return NextResponse.json({ portalUrl });
  } catch (err) {
    console.error("Customer portal fetch failed:", err);
    return NextResponse.json(
      { error: "Failed to get customer portal URL" },
      { status: 500 }
    );
  }
}
