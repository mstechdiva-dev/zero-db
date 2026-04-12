import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function middleware(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          );
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  const pathname = request.nextUrl.pathname;

  // Protect dashboard and onboarding routes — redirect unauthenticated users to login
  if (pathname.startsWith("/dashboard") || pathname.startsWith("/onboarding")) {
    if (!user) {
      const url = request.nextUrl.clone();
      url.pathname = "/auth/login";
      return NextResponse.redirect(url);
    }

    // Trial enforcement — check if trial has expired
    if (pathname.startsWith("/dashboard") && user) {
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
            // Trial expired — allow access to settings so they can upgrade,
            // but redirect away from all other dashboard pages
            if (!pathname.startsWith("/dashboard/settings")) {
              const url = request.nextUrl.clone();
              url.pathname = "/dashboard/settings";
              url.searchParams.set("trial_expired", "true");
              return NextResponse.redirect(url);
            }
          }
        }
      } catch {
        // If trial check fails, let them through — don't block on a DB error
      }
    }
  }

  // Redirect authenticated users away from auth pages
  if (pathname.startsWith("/auth") && user) {
    const url = request.nextUrl.clone();
    url.pathname = "/dashboard";
    return NextResponse.redirect(url);
  }

  return supabaseResponse;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
