"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import { FieldList, StatusSteps } from "@/components/case-parts";
import { Container, ContentSection, PageHeader } from "@/components/page-header";
import { Button, EmptyState, ErrorState, InlineError, Skeleton, StatusBadge } from "@/components/ui";
import { data, finalDecision, openQuestion } from "@/lib/data";
import { errorMessage } from "@/lib/errors";
import { STATUS_META, shortId } from "@/lib/format";
import { useApplicationCase } from "@/lib/hooks";

const CRUMBS = [{ href: "/", label: "Home" }];

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

  const { app, events } = result;
  const question = openQuestion(app, events);
  const decision = app.status === "decided" ? finalDecision(events) : null;

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
        {question && <ReplyForm id={app.id} question={question} />}

        {decision && (
          <div className={`rounded-2xl p-8 ${decision.decision === "approve" ? "bg-brand-50" : "bg-rose-50"}`}>
            <p className="text-sm font-semibold text-muted">Decision</p>
            <p className={`mt-1 text-2xl font-bold ${decision.decision === "approve" ? "text-brand-700" : "text-rose-700"}`}>
              {decision.decision === "approve" ? "Your loan is approved" : "We cannot offer this loan right now"}
            </p>
            {decision.reason && <p className="mt-2 text-sm text-muted">{decision.reason}</p>}
          </div>
        )}

        <ContentSection title="What you told us" hint="Anything missing will be requested before we assess your application.">
          <div className="rounded-2xl border border-line bg-white px-5">
            <FieldList fields={app.fields} formOnly />
          </div>
        </ContentSection>
      </Container>
    </>
  );
}

function ReplyForm({ id, question }: { id: string; question: string }) {
  const [answer, setAnswer] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!answer.trim()) {
      setError("Please write an answer first.");
      return;
    }
    setSending(true);
    setError(null);
    try {
      await data.reply(id, { answer: answer.trim() });
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
      <div className="space-y-3 p-6">
        <textarea
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          rows={3}
          placeholder="Type your answer…"
          className="w-full resize-none rounded-xl border border-line px-4 py-3 text-ink outline-none transition focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
        />
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
