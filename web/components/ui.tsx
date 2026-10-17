import type { ButtonHTMLAttributes, ReactNode } from "react";
import { RECOMMENDATION_META, STATUS_META, TONE_CLASSES, type Tone } from "@/lib/format";
import type { Recommendation, Status } from "@/lib/types";

export function Chip({ tone, children, pulse = false }: { tone: Tone; children: ReactNode; pulse?: boolean }) {
  const t = TONE_CLASSES[tone];
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${t.chip}`}
    >
      <span className={`size-1.5 rounded-full ${t.dot} ${pulse ? "animate-pulse" : ""}`} />
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: Status }) {
  const meta = STATUS_META[status];
  return (
    <Chip tone={meta.tone} pulse={status === "analyzing"}>
      {meta.label}
    </Chip>
  );
}

export function RecommendationBadge({ recommendation }: { recommendation: Recommendation }) {
  const meta = RECOMMENDATION_META[recommendation];
  return <Chip tone={meta.tone}>{meta.label}</Chip>;
}

type ButtonVariant = "primary" | "soft" | "ghost" | "danger";

const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-brand-600 text-white hover:bg-brand-700 shadow-sm shadow-brand-700/20",
  soft: "bg-brand-50 text-brand-800 ring-1 ring-inset ring-brand-200 hover:bg-brand-100",
  ghost: "text-muted hover:bg-brand-50 hover:text-ink",
  danger: "bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-200 hover:bg-rose-100",
};

export function Button({
  variant = "primary",
  loading = false,
  className = "",
  children,
  disabled,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; loading?: boolean }) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${BUTTON_VARIANTS[variant]} ${className}`}
    >
      {loading && <Spinner />}
      {children}
    </button>
  );
}

export function Spinner() {
  return <span className="size-4 animate-spin rounded-full border-2 border-current border-r-transparent" />;
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-xl bg-brand-100/60 ${className}`} />;
}

export function EmptyState({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 px-6 py-14 text-center">
      <div className="mb-2 grid size-12 place-items-center rounded-2xl bg-brand-50 text-brand-500 ring-1 ring-brand-100">
        <svg viewBox="0 0 24 24" className="size-6" fill="none" stroke="currentColor" strokeWidth={1.8}>
          <path d="M4 13h4l2 3h4l2-3h4M5 13l2-7h10l2 7v5H5z" strokeLinejoin="round" />
        </svg>
      </div>
      <p className="font-semibold text-ink">{title}</p>
      <p className="max-w-sm text-sm text-muted">{body}</p>
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="m-4 rounded-2xl bg-rose-50 px-5 py-4 text-sm text-rose-700 ring-1 ring-inset ring-rose-200">
      <p className="font-semibold">Could not load data</p>
      <p className="mt-0.5">{message}</p>
    </div>
  );
}

export function InlineError({ message }: { message: string | null }) {
  if (!message) return null;
  return <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700 ring-1 ring-inset ring-rose-200">{message}</p>;
}
