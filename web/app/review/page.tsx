"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Container, PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, RecommendationBadge, Skeleton, StatusBadge } from "@/components/ui";
import { formatAmount, formatPercent, shortId, timeAgo } from "@/lib/format";
import { useApplications } from "@/lib/hooks";
import type { Application, Status } from "@/lib/types";

const TABS: { key: string; label: string; statuses: Status[] }[] = [
  { key: "review", label: "Needs review", statuses: ["pending_review"] },
  { key: "info", label: "Waiting on applicant", statuses: ["needs_info"] },
  { key: "cleared", label: "Auto-cleared", statuses: ["auto_cleared"] },
  { key: "progress", label: "In progress", statuses: ["submitted", "analyzing"] },
  { key: "decided", label: "Decided", statuses: ["decided"] },
  { key: "all", label: "All", statuses: ["submitted", "analyzing", "needs_info", "pending_review", "auto_cleared", "decided"] },
];

const STATS: { label: string; statuses: Status[]; dot: string }[] = [
  { label: "Awaiting a reviewer", statuses: ["pending_review"], dot: "bg-lavender-400" },
  { label: "Waiting on applicant", statuses: ["needs_info"], dot: "bg-peach-400" },
  { label: "Auto-cleared", statuses: ["auto_cleared"], dot: "bg-brand-400" },
  { label: "Decided", statuses: ["decided"], dot: "bg-sky-400" },
];

export default function ReviewQueuePage() {
  const { data: apps, error, loading } = useApplications();
  const [tab, setTab] = useState(TABS[0].key);
  const active = TABS.find((t) => t.key === tab) ?? TABS[0];
  const rows = (apps ?? []).filter((a) => active.statuses.includes(a.status));
  const count = (statuses: Status[]) => apps?.filter((a) => statuses.includes(a.status)).length;

  return (
    <>
      <PageHeader
        crumbs={[{ href: "/", label: "Home" }]}
        eyebrow="Loan officer workspace"
        title="Review cases"
        description="Applications the router could not clear on its own. The list updates live as cases move."
        aside={
          <span className="inline-flex items-center gap-2 rounded-full bg-white px-3.5 py-1.5 text-sm font-semibold text-brand-700 ring-1 ring-brand-100">
            <span className="size-2 animate-pulse rounded-full bg-brand-400" /> Live updates
          </span>
        }
      />

      <section className="border-b border-line bg-white">
        <Container className="grid grid-cols-2 divide-line md:grid-cols-4 md:divide-x">
          {STATS.map((s) => (
            <div key={s.label} className="py-6 md:px-8 md:first:pl-0">
              <p className="flex items-center gap-2 text-sm text-muted">
                <span className={`size-2 rounded-full ${s.dot}`} /> {s.label}
              </p>
              {loading ? (
                <Skeleton className="mt-2 h-8 w-10" />
              ) : (
                <p className="mt-1 text-3xl font-extrabold tracking-tight text-ink">{count(s.statuses) ?? "—"}</p>
              )}
            </div>
          ))}
        </Container>
      </section>

      <Container className="py-10">
        <div className="flex gap-6 overflow-x-auto border-b border-line">
          {TABS.map((t) => {
            const n = count(t.statuses);
            const selected = t.key === active.key;
            return (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`-mb-px flex items-center gap-2 whitespace-nowrap border-b-2 pb-3 text-sm font-semibold transition ${
                  selected ? "border-brand-600 text-ink" : "border-transparent text-muted hover:text-ink"
                }`}
              >
                {t.label}
                {n !== undefined && (
                  <span className={`rounded-full px-2 py-0.5 text-[11px] ${selected ? "bg-brand-100 text-brand-800" : "bg-slate-100 text-slate-500"}`}>
                    {n}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        <div className="mt-6 overflow-hidden rounded-2xl border border-line bg-white">
          {loading ? (
            <div className="space-y-3 p-6">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12" />
              ))}
            </div>
          ) : error ? (
            <ErrorState message={error} />
          ) : rows.length === 0 ? (
            <EmptyState title="All clear" body={`No applications in “${active.label.toLowerCase()}” right now.`} />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[52rem] text-left text-sm">
                <thead className="border-b border-line bg-canvas text-xs font-semibold uppercase tracking-wider text-muted">
                  <tr>
                    <th className="px-6 py-3">Case</th>
                    <th className="px-6 py-3">Agent recommendation</th>
                    <th className="px-6 py-3 text-right">Loan amount</th>
                    <th className="px-6 py-3 text-right">Confidence</th>
                    <th className="px-6 py-3">Status</th>
                    <th className="px-6 py-3 text-right">Received</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {rows.map((app) => (
                    <QueueRow key={app.id} app={app} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Container>
    </>
  );
}

function QueueRow({ app }: { app: Application }) {
  const router = useRouter();
  const out = app.agent_output;
  const href = `/review/${app.id}`;
  return (
    <tr onClick={() => router.push(href)} className="cursor-pointer transition hover:bg-brand-50/60">
      <td className="px-6 py-4">
        <Link href={href} className="font-mono font-semibold text-ink hover:text-brand-700">
          #{shortId(app.id)}
        </Link>
      </td>
      <td className="max-w-md px-6 py-4">
        {out ? (
          <div className="flex items-center gap-3">
            <RecommendationBadge recommendation={out.recommendation} />
            <span className="truncate text-muted">{out.reasons[0]}</span>
          </div>
        ) : (
          <span className="text-muted">Not analyzed yet</span>
        )}
      </td>
      <td className="px-6 py-4 text-right font-semibold tabular-nums text-ink">{formatAmount(app.fields?.loan_amount)}</td>
      <td className="px-6 py-4 text-right tabular-nums text-ink">{out ? formatPercent(out.confidence, 0) : "—"}</td>
      <td className="px-6 py-4">
        <StatusBadge status={app.status} />
      </td>
      <td className="px-6 py-4 text-right text-muted">{timeAgo(app.created_at)}</td>
    </tr>
  );
}
