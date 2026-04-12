import { NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";
import { createSoloCheckout } from "@/lib/lemonsqueezy";

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

  // Get the org ID
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

  try {
    const { checkoutUrl } = await createSoloCheckout({
      email: user.email ?? "",
      orgId: userData.org_id,
    });
    return NextResponse.json({ checkoutUrl });
  } catch (err) {
    console.error("Checkout creation failed:", err);
    return NextResponse.json(
      { error: "Failed to create checkout session" },
      { status: 500 }
    );
  }
}
