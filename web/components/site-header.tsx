import Link from "next/link";
import { Suspense } from "react";
import { IS_DEMO_MODE } from "@/lib/config";
import { NavLinks } from "./nav-links";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-white/85 backdrop-blur-md">
      {IS_DEMO_MODE && (
        <div className="bg-brand-800 px-4 py-1.5 text-center text-xs text-brand-50">
          Demo mode: the API and Supabase are not connected, so you are seeing seeded sample applications.
        </div>
      )}
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-8 px-4 sm:px-6 lg:px-8">
        <Logo />
        <nav className="hidden items-center gap-1 md:flex">
          {/* The active link depends on the URL, which is only known at request time. */}
          <Suspense fallback={<NavLinks pathname="" />}>
            <NavLinks />
          </Suspense>
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <Link
            href="/review"
            className="hidden rounded-full px-4 py-2 text-sm font-semibold text-brand-800 transition hover:bg-brand-50 sm:inline-flex"
          >
            For loan officers
          </Link>
          <Link
            href="/apply"
            className="rounded-full bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700"
          >
            Apply now
          </Link>
        </div>
      </div>
      <nav className="flex gap-1 overflow-x-auto border-t border-line px-4 py-2 md:hidden">
        <Suspense fallback={<NavLinks pathname="" />}>
          <NavLinks />
        </Suspense>
      </nav>
    </header>
  );
}

export function Logo({ light = false }: { light?: boolean }) {
  return (
    <Link href="/" className="flex shrink-0 items-center gap-2.5">
      <span className="grid size-8 place-items-center rounded-lg bg-gradient-to-br from-brand-400 to-brand-700">
        <svg viewBox="0 0 24 24" className="size-4.5 text-white" fill="none" stroke="currentColor" strokeWidth={2.4}>
          <path d="M5 12.5l4.2 4.2L19 7" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
      <span className={`text-lg font-bold tracking-tight ${light ? "text-white" : "text-ink"}`}>Clearpath</span>
    </Link>
  );
}
