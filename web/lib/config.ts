// Public settings, inlined at build time from the repo-root .env (see next.config.ts).
// When Supabase or the API URL is missing, the app runs on in-memory demo data instead.

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";
export const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
export const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

export const IS_DEMO_MODE = !(API_URL && SUPABASE_URL && SUPABASE_ANON_KEY);
