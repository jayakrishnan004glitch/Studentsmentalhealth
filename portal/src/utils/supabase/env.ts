/** Public Supabase settings (safe in the browser). Fails fast if missing. */
export const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
export const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? "";

if (!supabaseUrl || !supabaseKey) {
  throw new Error(
    "Missing NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY. " +
      "Copy portal/.env.example to portal/.env.local.",
  );
}
