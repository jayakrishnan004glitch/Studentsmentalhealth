import { createServerClient } from "@supabase/ssr";
import { type NextRequest, NextResponse } from "next/server";

import { supabaseKey, supabaseUrl } from "./env";

/**
 * Refreshes the Supabase session cookie on every request, so Server
 * Components always see a valid session. Called from src/proxy.ts.
 */
export async function updateSession(request: NextRequest) {
  let response = NextResponse.next({ request });

  const supabase = createServerClient(supabaseUrl, supabaseKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, options),
        );
      },
    },
  });

  // Do not remove: this call is what refreshes an expired access token.
  // getClaims() verifies the JWT against the project's public keys.
  await supabase.auth.getClaims();

  return response;
}
