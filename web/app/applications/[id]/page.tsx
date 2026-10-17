"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import { FieldList, StatusSteps } from "@/components/case-parts";
import { Container, ContentSection, PageHeader } from "@/components/page-header";
import { Button, EmptyState, ErrorState, InlineError, Skeleton, StatusBadge } from "@/components/ui";
import { data } from "@/lib/data";
import { errorMessage } from "@/lib/errors";
import { STATUS_META, formatAmount, humanize, shortId } from "@/lib/format";
import { useApplicationCase } from "@/lib/hooks";
import { REQUIRED_FIELDS, type ApplicantFields, type Application } from "@/lib/types";

const CRUMBS = [{ href: "/", label: "Home" }];

const FIELD_LABELS: Partial<Record<keyof ApplicantFields, string>> = {
  annual_income: "Annual income",
  loan_amount: "Loan amount",
  annuity: "Loan annuity",
  goods_price: "Price of the goods",
};

/** The fields as the agent last saw them, or as submitted if extraction has not run yet. */
function currentFields(app: Application): ApplicantFields {
  return app.fields ?? { ...app.input.form, ...app.input.corrections, document_income: null };
}

/** Figures the applicant can correct in a reply: missing required fields, plus income on a mismatch. */
function correctableFields(app: Application): (keyof ApplicantFields)[] {
  const fields = currentFields(app);
  const keys: (keyof ApplicantFields)[] = REQUIRED_FIELDS.filter((k) => fields[k] == null);
  if (fields.document_income != null && !keys.includes("annual_income")) keys.unshift("annual_income");
  return keys;
}

export default function ApplicationStatusPage() {
  const { id } = useParams<{ id: string }>();
  const { data: result, error, loading } = useApplicationCase(id);

  if (loading) {
    return (
      <>
        <PageHeader narrow crumbs={CRUMBS} eyebrow="Your application" title="Loading your application…" />
        <Container narrow className="space-y-6 py-10">
          <Skeleton className="h-16" />
          <Skeleton className="h-64" />
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
          title="Application not found"
          body="Check the link, or start a new application."
          action={<Link href="/apply" className="text-sm font-semibold text-brand-700">Apply now →</Link>}
        />
      </Container>
    );
  }

  const { app } = result;
  const question = app.status === "needs_info" ? app.human_question : null;

  return (
    <>
      <PageHeader
        narrow
        crumbs={CRUMBS}
        eyebrow={`Application #${shortId(app.id)}`}
        title={STATUS_META[app.status].applicantText}
        description="This page updates on its own. You can keep it open or come back to this link later."
        aside={<StatusBadge status={app.status} />}
      />

      <section className="border-b border-line bg-white">
        <Container narrow className="py-6">
          <StatusSteps status={app.status} />
        </Container>
      </section>

      <Container narrow className="space-y-12 py-10">
        {question && <ReplyForm key={question} app={app} question={question} />}

        {app.status === "decided" && app.final_decision && (
          <div className={`rounded-2xl p-8 ${app.final_decision === "approve" ? "bg-brand-50" : "bg-rose-50"}`}>
            <p className="text-sm font-semibold text-muted">Decision</p>
            <p className={`mt-1 text-2xl font-bold ${app.final_decision === "approve" ? "text-brand-700" : "text-rose-700"}`}>
              {app.final_decision === "approve" ? "Your loan is approved" : "We cannot offer this loan right now"}
            </p>
            {app.decision_reason && <p className="mt-2 text-sm text-muted">{app.decision_reason}</p>}
          </div>
        )}

        <ContentSection title="What you told us" hint="Anything missing will be requested before we assess your application.">
          <div className="rounded-2xl border border-line bg-white px-5">
            <FieldList fields={currentFields(app)} formOnly />
          </div>
        </ContentSection>

        {app.input.documents.length > 0 && (
          <ContentSection title="Documents you attached">
            <ul className="divide-y divide-line rounded-2xl border border-line bg-white">
              {app.input.documents.map((d) => (
                <li key={d.name} className="flex items-center justify-between gap-4 px-5 py-3 text-sm">
                  <span className="font-medium text-ink">{d.name}</span>
                  <span className="text-muted">{humanize(d.kind)}</span>
                </li>
              ))}
            </ul>
          </ContentSection>
        )}
      </Container>
    </>
  );
}

function ReplyForm({ app, question }: { app: Application; question: string }) {
  const keys = correctableFields(app);
  const fields = currentFields(app);
  const [answer, setAnswer] = useState("");
  const [corrections, setCorrections] = useState<Partial<Record<keyof ApplicantFields, string>>>({});
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!answer.trim()) {
      setError("Please write an answer first.");
      return;
    }
    const parsed: Partial<Record<keyof ApplicantFields, number>> = {};
    for (const k of keys) {
      const raw = corrections[k]?.replaceAll(",", "").trim();
      if (!raw) continue;
      const n = Number(raw);
      if (!Number.isFinite(n) || n <= 0) {
        setError(`${FIELD_LABELS[k] ?? humanize(k)} must be a number greater than zero.`);
        return;
      }
      parsed[k] = n;
    }
    setSending(true);
    setError(null);
    try {
      await data.reply(app.id, { answer: answer.trim(), corrections: parsed });
    } catch (err) {
      setError(errorMessage(err));
      setSending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="overflow-hidden rounded-2xl border border-peach-200 bg-white shadow-soft">
      <div className="border-b border-peach-100 bg-peach-50 px-6 py-5">
        <p className="text-xs font-semibold uppercase tracking-wider text-peach-700">We have a question for you</p>
        <p className="mt-1.5 text-lg font-semibold text-ink">{question}</p>
      </div>
      <div className="space-y-5 p-6">
        <label className="block">
          <span className="text-sm font-semibold text-ink">Your answer</span>
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            rows={3}
            placeholder="Type your answer…"
            className="mt-1.5 w-full resize-none rounded-xl border border-line px-4 py-3 text-ink outline-none transition focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
          />
        </label>

        {keys.length > 0 && (
          <div>
            <p className="text-sm font-semibold text-ink">
              Update a figure <span className="font-normal text-muted">(optional)</span>
            </p>
            <p className="mt-0.5 text-xs text-muted">Figures you enter here replace what we have on file.</p>
            <div className="mt-3 grid gap-4 sm:grid-cols-2">
              {keys.map((k) => (
                <label key={k} className="flex flex-col gap-1.5">
                  <span className="text-xs font-semibold text-muted">
                    {FIELD_LABELS[k] ?? humanize(k)}
                    {fields[k] != null && <span className="font-normal"> · now {formatAmount(fields[k])}</span>}
                  </span>
                  <input
                    inputMode="decimal"
                    value={corrections[k] ?? ""}
                    onChange={(e) => setCorrections({ ...corrections, [k]: e.target.value })}
                    placeholder={fields[k] == null ? "Missing" : "0"}
                    className="rounded-xl border border-line px-4 py-2.5 tabular-nums text-ink outline-none transition placeholder:text-muted/40 focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
                  />
                </label>
              ))}
            </div>
          </div>
        )}

        <InlineError message={error} />
        <div className="flex justify-end">
          <Button type="submit" loading={sending}>
            Send answer
          </Button>
        </div>
      </div>
    </form>
  );
}
