import Link from "next/link";
import { Logo } from "./site-header";

const COLUMNS = [
  {
    title: "Product",
    links: [
      { href: "/apply", label: "Apply for a loan" },
      { href: "/review", label: "Review cases" },
      { href: "/#how-it-works", label: "How it works" },
    ],
  },
  {
    title: "Principles",
    links: [
      { href: "/#principles", label: "Never auto-reject" },
      { href: "/#principles", label: "Audit trail" },
      { href: "/#principles", label: "Fair by design" },
    ],
  },
  {
    title: "Help",
    links: [
      { href: "/#faq", label: "FAQ" },
      { href: "/#faq", label: "What data we use" },
    ],
  },
];

export function SiteFooter() {
  return (
    <footer className="bg-brand-900 text-brand-100">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-14 sm:px-6 md:grid-cols-[1.4fr_repeat(3,1fr)] lg:px-8">
        <div>
          <Logo light />
          <p className="mt-4 max-w-xs text-sm text-brand-200/80">
            An AI analyst does the underwriting legwork. A loan officer makes the call wherever judgment is needed.
          </p>
        </div>
        {COLUMNS.map((col) => (
          <div key={col.title}>
            <p className="text-sm font-semibold text-white">{col.title}</p>
            <ul className="mt-4 space-y-2.5 text-sm">
              {col.links.map((l) => (
                <li key={l.label}>
                  <Link href={l.href} className="text-brand-200/80 transition hover:text-white">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-white/10">
        <div className="mx-auto flex max-w-7xl flex-wrap justify-between gap-2 px-4 py-5 text-xs text-brand-200/60 sm:px-6 lg:px-8">
          <p>© 2026 Clearpath. Hackathon prototype, not a real lender.</p>
          <p>The model recommends, rules route, people decide.</p>
        </div>
      </div>
    </footer>
  );
}
