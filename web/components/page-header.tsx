import Link from "next/link";
import type { ReactNode } from "react";

export function Container({
  children,
  className = "",
  narrow = false,
}: {
  children: ReactNode;
  className?: string;
  narrow?: boolean;
}) {
  return (
    <div className={`mx-auto w-full px-4 sm:px-6 lg:px-8 ${narrow ? "max-w-4xl" : "max-w-7xl"} ${className}`}>{children}</div>
  );
}

/** Full-width title band at the top of an inner page. */
export function PageHeader({
  eyebrow,
  title,
  description,
  crumbs,
  aside,
  narrow = false,
}: {
  eyebrow?: string;
  title: ReactNode;
  description?: ReactNode;
  crumbs?: { href: string; label: string }[];
  aside?: ReactNode;
  narrow?: boolean;
}) {
  return (
    <section className="border-b border-line bg-gradient-to-b from-brand-50 to-canvas">
      <Container narrow={narrow} className="py-10 sm:py-12">
        {crumbs && (
          <nav className="mb-4 flex items-center gap-2 text-sm text-muted">
            {crumbs.map((c, i) => (
              <span key={c.href} className="flex items-center gap-2">
                {i > 0 && <span className="text-muted/40">/</span>}
                <Link href={c.href} className="hover:text-ink">
                  {c.label}
                </Link>
              </span>
            ))}
          </nav>
        )}
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div className="max-w-2xl">
            {eyebrow && <p className="text-sm font-semibold text-brand-600">{eyebrow}</p>}
            <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-ink sm:text-4xl">{title}</h1>
            {description && <p className="mt-3 text-base text-muted">{description}</p>}
          </div>
          {aside}
        </div>
      </Container>
    </section>
  );
}

/** A titled block inside a page, separated by spacing rather than a card. */
export function ContentSection({
  title,
  hint,
  action,
  children,
}: {
  title: string;
  hint?: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-ink">{title}</h2>
          {hint && <p className="mt-0.5 text-sm text-muted">{hint}</p>}
        </div>
        {action}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}
