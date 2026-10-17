"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import { AuditTrail, ConfidenceMeter, FieldList, MetricTiles, StatusSteps } from "@/components/case-parts";
import { Container, ContentSection, PageHeader } from "@/components/page-header";
import { Button, EmptyState, ErrorState, InlineError, RecommendationBadge, Skeleton, StatusBadge } from "@/components/ui";
import { data, finalDecision, openQuestion } from "@/lib/data";
import { errorMessage } from "@/lib/errors";
import { shortId, timeAgo } from "@/lib/format";
import { useApplicationCase } from "@/lib/hooks";
import type { Application, HumanDecision, Recommendation } from "@/lib/types";

const CRUMBS = [
  { href: "/", label: "Home" },
  { href: "/review", label: "Review cases" },
];

export default function ReviewCasePage() {
  const { id } = useParams<{ id: string }>();
  const { data: result, error, loading } = useApplicationCase(id);

  if (loading) {
    return (
      <>
        <PageHeader crumbs={CRUMBS} title="Loading case…" />
        <Container className="grid gap-10 py-10 lg:grid-cols-[1fr_24rem]">
          <div className="space-y-6">
            <Skeleton className="h-48" />
            <Skeleton className="h-32" />
          </div>
          <Skeleton className="h-80" />
        </Container>
      </>
    );
  }
  if (error) {
    return (
      <Container className="py-10">
        <ErrorState message={error} />
      </Container>
    );
  }
  if (!result?.app) {
    return (
      <Container className="py-16">
        <EmptyState
          title="Case not found"
          body="It may have been removed, or the link is wrong."
          action={<Link href="/review" className="text-sm font-semibold text-brand-700">Back to review cases →</Link>}
        />
      </Container>
    );
  }

  const { app, events } = result;
  const out = app.agent_output;
  const question = openQuestion(app, events);
  const decided = app.status === "decided" ? finalDecision(events) : null;

  return (
    <>
      <PageHeader
        crumbs={CRUMBS}
        eyebrow={`Submitted ${timeAgo(app.created_at)} · updated ${timeAgo(app.updated_at)}`}
        title={<span className="font-mono">Case #{shortId(app.id)}</span>}
        aside={<StatusBadge status={app.status} />}
      />

      <section className="border-b border-line bg-white">
        <Container className="py-6">
          <StatusSteps status={app.status} />
        </Container>
      </section>

      <Container className="grid gap-12 py-10 lg:grid-cols-[1fr_24rem]">
        <div className="space-y-12">
          <ContentSection
            title="Agent recommendation"
            hint="The model recommends; the router's rules chose this path."
            action={out && <RecommendationBadge recommendation={out.recommendation} />}
          >
            {out ? (
              <div className="space-y-5">
                <ConfidenceMeter value={out.confidence} />
                <ul className="divide-y divide-line rounded-2xl border border-line bg-white">
                  {out.reasons.map((r) => (
                    <li key={r} className="flex gap-3 px-5 py-3.5 text-sm text-ink">
                      <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-brand-400" />
                      {r}
                    </li>
                  ))}
                </ul>
                {out.human_question && (
                  <p className="border-l-4 border-lavender-200 bg-lavender-50 px-5 py-3 text-sm text-ink">
                    <span className="block text-xs font-semibold text-lavender-700">Question for the reviewer</span>
                    {out.human_question}
                  </p>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted">The reasoner has not run on this case yet.</p>
            )}
            {question && (
              <p className="mt-5 border-l-4 border-peach-200 bg-peach-50 px-5 py-3 text-sm text-ink">
                <span className="block text-xs font-semibold text-peach-700">Waiting on the applicant</span>
                {question}
              </p>
            )}
          </ContentSection>

          <ContentSection title="Affordability" hint="Computed in code, never by the model.">
            <MetricTiles metrics={app.metrics} />
          </ContentSection>

          <ContentSection title="Applicant details" hint="Extracted from the form and documents. No protected attributes.">
            <div className="rounded-2xl border border-line bg-white px-5">
              <FieldList fields={app.fields} />
            </div>
          </ContentSection>
        </div>

        <aside className="space-y-10 lg:sticky lg:top-24 lg:self-start">
          {app.status === "pending_review" || app.status === "auto_cleared" ? (
            <DecisionPanel app={app} />
          ) : decided ? (
            <div className={`rounded-2xl p-6 ${decided.decision === "approve" ? "bg-brand-50" : "bg-rose-50"}`}>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted">Final decision</p>
              <p className={`mt-1 text-2xl font-bold ${decided.decision === "approve" ? "text-brand-700" : "text-rose-700"}`}>
                {decided.decision === "approve" ? "Approved" : "Rejected"}
              </p>
              {decided.reason && <p className="mt-2 text-sm text-muted">{decided.reason}</p>}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-line p-6">
              <p className="text-sm font-semibold text-ink">No decision needed yet</p>
              <p className="mt-1 text-sm text-muted">
                This case is {app.status === "needs_info" ? "waiting on the applicant" : "still being analyzed"}. It
                will come back to the queue if it needs you.
              </p>
            </div>
          )}
          <AuditTrail events={events} />
        </aside>
      </Container>
    </>
  );
}

function isOverride(decision: HumanDecision, recommendation: Recommendation | undefined): boolean {
  return (decision === "approve" && recommendation === "decline") || (decision === "reject" && recommendation === "approve");
}

function DecisionPanel({ app }: { app: Application }) {
  const recommendation = app.agent_output?.recommendation;
  const [decision, setDecision] = useState<HumanDecision>(recommendation === "decline" ? "reject" : "approve");
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const override = isOverride(decision, recommendation);
  const reasonRequired = decision === "reject" || override;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (reasonRequired && !reason.trim()) {
      setError(override ? "An override needs a reason. It is stored in the override log." : "A rejection needs a reason.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await data.decide(app.id, { decision, override, reason: reason.trim() || null });
    } catch (err) {
      setError(errorMessage(err));
      setSaving(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="rounded-2xl border border-line bg-white shadow-soft">
      <div className="border-b border-line px-6 py-4">
        <p className="text-base font-bold text-ink">Your decision</p>
        <p className="mt-0.5 text-sm text-muted">
          {app.status === "auto_cleared" ? "The router cleared this case. Confirm to finalize." : "This case needs a human call."}
        </p>
      </div>
      <div className="space-y-4 p-6">
        <div className="grid grid-cols-2 gap-1 rounded-full bg-canvas p-1 ring-1 ring-inset ring-line">
          {(["approve", "reject"] as const).map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => setDecision(d)}
              className={`rounded-full py-2 text-sm font-semibold capitalize transition ${
                decision === d ? (d === "approve" ? "bg-brand-600 text-white shadow-sm" : "bg-rose-500 text-white shadow-sm") : "text-muted hover:text-ink"
              }`}
            >
              {d}
            </button>
          ))}
        </div>

        {override && (
          <p className="rounded-xl bg-peach-50 px-3 py-2 text-xs text-peach-700">
            This goes against the agent&apos;s <strong>{recommendation}</strong> recommendation, so it is recorded as an
            override.
          </p>
        )}

        <label className="block">
          <span className="text-sm font-semibold text-ink">
            Reason {reasonRequired ? <span className="text-rose-600">(required)</span> : <span className="font-normal text-muted">(optional)</span>}
          </span>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={4}
            placeholder="Cite the field or metric that drove your call…"
            className="mt-1.5 w-full resize-none rounded-xl border border-line px-4 py-3 text-sm text-ink outline-none transition focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
          />
        </label>

        <InlineError message={error} />

        <Button type="submit" loading={saving} variant={decision === "reject" ? "danger" : "primary"} className="w-full">
          {override ? "Record override" : decision === "approve" ? "Approve application" : "Reject application"}
        </Button>
      </div>
    </form>
  );
}
