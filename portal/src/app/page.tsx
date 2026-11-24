import { Suspense } from "react";

import { createClient } from "@/utils/supabase/server";

/**
 * Placeholder home for the counsellor/admin portal (built in Week 3).
 * The static shell renders instantly; the session check streams in.
 */
export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-4 py-16">
      <h1 className="text-3xl font-semibold tracking-tight">MH Companion portal</h1>
      <p className="text-zinc-600 dark:text-zinc-400">
        Counsellor and admin portal. The alerts dashboard and knowledge-base manager arrive in
        Week 3.
      </p>
      <section className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
        <h2 className="mb-2 font-medium">Supabase connection</h2>
        <Suspense fallback={<p className="text-zinc-500">Checking…</p>}>
          <ConnectionStatus />
        </Suspense>
      </section>
    </main>
  );
}

/** Reads the session cookie, so it is request-time (dynamic) content. */
async function ConnectionStatus() {
  const supabase = await createClient();
  const { data, error } = await supabase.auth.getClaims();
  if (error) {
    return (
      <p className="text-red-700 dark:text-red-400">Could not reach Supabase: {error.message}</p>
    );
  }
  const email = data?.claims?.email as string | undefined;
  return <p>Connected. {email ? <>Signed in as {email}.</> : <>Not signed in.</>}</p>;
}
