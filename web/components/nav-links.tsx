"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", label: "Home" },
  { href: "/apply", label: "Apply for a loan" },
  { href: "/review", label: "Review cases" },
];

function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

function Links({ pathname }: { pathname: string }) {
  return NAV.map((item) => (
    <Link
      key={item.href}
      href={item.href}
      className={`whitespace-nowrap rounded-full px-3.5 py-1.5 text-sm font-medium transition ${
        isActive(pathname, item.href) ? "bg-brand-50 text-brand-800" : "text-muted hover:text-ink"
      }`}
    >
      {item.label}
    </Link>
  ));
}

function CurrentLinks() {
  return <Links pathname={usePathname()} />;
}

/** Nav links with the current section highlighted. Pass `pathname` to render without the URL. */
export function NavLinks({ pathname }: { pathname?: string }) {
  return pathname === undefined ? <CurrentLinks /> : <Links pathname={pathname} />;
}
