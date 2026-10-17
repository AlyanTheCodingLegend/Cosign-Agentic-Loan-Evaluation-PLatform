import type { Recommendation, Status } from "./types";

// Currency is unspecified in the source data, so amounts are shown without a symbol.
const amount = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

export function formatAmount(value: number | null | undefined): string {
  return value == null ? "—" : amount.format(value);
}

export function formatPercent(fraction: number | null | undefined, digits = 1): string {
  return fraction == null ? "—" : `${(fraction * 100).toFixed(digits)}%`;
}

export function formatRatio(value: number | null | undefined): string {
  return value == null ? "—" : `${value.toFixed(2)}×`;
}

export function shortId(id: string): string {
  return id.slice(0, 8).toUpperCase();
}

export function timeAgo(isoDate: string): string {
  const seconds = Math.max(0, Math.round((Date.now() - new Date(isoDate).getTime()) / 1000));
  if (seconds < 60) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function formatTime(isoDate: string): string {
  return new Date(isoDate).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

export function humanize(snake: string): string {
  const s = snake.replaceAll("_", " ");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export const STATUS_META: Record<Status, { label: string; tone: Tone; applicantText: string }> = {
  submitted: { label: "Submitted", tone: "slate", applicantText: "We have your application." },
  analyzing: { label: "Analyzing", tone: "sky", applicantText: "Our analyst is reviewing your details." },
  needs_info: { label: "Needs info", tone: "peach", applicantText: "We need a little more information from you." },
  pending_review: { label: "In review", tone: "lavender", applicantText: "A loan officer is reviewing your application." },
  auto_cleared: { label: "Auto-cleared", tone: "mint", applicantText: "Your application cleared our checks." },
  decided: { label: "Decided", tone: "teal", applicantText: "A decision has been made." },
};

export const RECOMMENDATION_META: Record<Recommendation, { label: string; tone: Tone }> = {
  approve: { label: "Approve", tone: "mint" },
  refer: { label: "Refer", tone: "lavender" },
  decline: { label: "Decline", tone: "rose" },
};

export type Tone = "slate" | "sky" | "peach" | "lavender" | "mint" | "teal" | "rose";

export const TONE_CLASSES: Record<Tone, { chip: string; dot: string }> = {
  slate: { chip: "bg-slate-100 text-slate-600 ring-slate-200", dot: "bg-slate-400" },
  sky: { chip: "bg-sky-50 text-sky-700 ring-sky-200", dot: "bg-sky-400" },
  peach: { chip: "bg-peach-50 text-peach-700 ring-peach-200", dot: "bg-peach-400" },
  lavender: { chip: "bg-lavender-50 text-lavender-700 ring-lavender-200", dot: "bg-lavender-400" },
  mint: { chip: "bg-brand-50 text-brand-700 ring-brand-200", dot: "bg-brand-400" },
  teal: { chip: "bg-brand-600 text-white ring-brand-600", dot: "bg-white" },
  rose: { chip: "bg-rose-50 text-rose-700 ring-rose-200", dot: "bg-rose-400" },
};
