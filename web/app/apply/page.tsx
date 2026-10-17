"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Container, PageHeader } from "@/components/page-header";
import { Button, InlineError } from "@/components/ui";
import { data } from "@/lib/data";
import { errorMessage } from "@/lib/errors";
import type { CreateApplicationRequest } from "@/lib/types";

type FieldKey = keyof CreateApplicationRequest;

interface FieldDef {
  key: FieldKey;
  label: string;
  hint: string;
  required: boolean;
  suffix?: string;
}

const SECTIONS: { title: string; body: string; fields: FieldDef[] }[] = [
  {
    title: "The loan",
    body: "What you want to buy and how you plan to repay it.",
    fields: [
      { key: "loan_amount", label: "Loan amount", hint: "How much you would like to borrow.", required: true },
      { key: "goods_price", label: "Price of the goods", hint: "What the loan pays for.", required: true },
      { key: "annuity", label: "Monthly installment", hint: "The repayment you expect each month.", required: true, suffix: "/ month" },
    ],
  },
  {
    title: "Your income",
    body: "We compare what you tell us with your bank statement, if you share one.",
    fields: [
      { key: "annual_income", label: "Annual income", hint: "Your total yearly income before tax.", required: true, suffix: "/ year" },
      {
        key: "document_income",
        label: "Income on your bank statement",
        hint: "The yearly income your statement shows.",
        required: false,
        suffix: "/ year",
      },
    ],
  },
  {
    title: "Employment",
    body: "Helps us understand how stable your income is.",
    fields: [{ key: "years_employed", label: "Years with current employer", hint: "Use decimals for months, e.g. 1.5.", required: false, suffix: "years" }],
  },
];

const FIELDS = SECTIONS.flatMap((s) => s.fields);

type FormState = Record<FieldKey, string>;

const EMPTY: FormState = {
  loan_amount: "",
  goods_price: "",
  annuity: "",
  annual_income: "",
  document_income: "",
  years_employed: "",
};

function toNumber(raw: string): number | null {
  const trimmed = raw.replaceAll(",", "").trim();
  return trimmed === "" ? null : Number(trimmed);
}

function validate(form: FormState): string | null {
  for (const f of FIELDS) {
    const n = toNumber(form[f.key]);
    if (n === null) continue;
    if (!Number.isFinite(n)) return `${f.label} must be a number.`;
    if (f.key === "years_employed" ? n < 0 : n <= 0) return `${f.label} must be greater than zero.`;
  }
  return null;
}

export default function ApplyPage() {
  const router = useRouter();
  const [form, setForm] = useState<FormState>(EMPTY);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const required = FIELDS.filter((f) => f.required);
  const missing = required.filter((f) => form[f.key].trim() === "");
  const started = missing.length < required.length;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const invalid = validate(form);
    if (invalid) {
      setError(invalid);
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const body = Object.fromEntries(FIELDS.map((f) => [f.key, toNumber(form[f.key])])) as unknown as CreateApplicationRequest;
      const { id } = await data.createApplication(body);
      router.push(`/applications/${id}`);
    } catch (err) {
      setError(errorMessage(err));
      setSubmitting(false);
    }
  }

  return (
    <>
      <PageHeader
        crumbs={[{ href: "/", label: "Home" }]}
        eyebrow="Loan application"
        title="Apply for a loan"
        description="It takes about a minute. Our analyst checks your numbers right away, and a loan officer reviews anything that needs a human eye."
      />

      <Container className="grid gap-12 py-12 lg:grid-cols-[1fr_18rem]">
        <form onSubmit={onSubmit} className="rounded-2xl border border-line bg-white">
          {SECTIONS.map((section) => (
            <section key={section.title} className="grid gap-6 border-b border-line p-6 sm:p-8 md:grid-cols-[14rem_1fr]">
              <div>
                <h2 className="text-base font-bold text-ink">{section.title}</h2>
                <p className="mt-1 text-sm text-muted">{section.body}</p>
              </div>
              <div className="grid gap-5 sm:grid-cols-2">
                {section.fields.map((f) => (
                  <label key={f.key} className={`flex flex-col gap-1.5 ${section.fields.length === 1 ? "sm:col-span-2 sm:max-w-sm" : ""}`}>
                    <span className="flex items-center gap-2 text-sm font-semibold text-ink">
                      {f.label}
                      {!f.required && <span className="text-xs font-normal text-muted">(optional)</span>}
                    </span>
                    <span className="flex items-center rounded-xl border border-line bg-white transition focus-within:border-brand-400 focus-within:ring-4 focus-within:ring-brand-100">
                      <input
                        inputMode="decimal"
                        value={form[f.key]}
                        onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                        placeholder="0"
                        className="w-full min-w-0 bg-transparent px-4 py-3 tabular-nums text-ink outline-none placeholder:text-muted/40"
                      />
                      {f.suffix && <span className="shrink-0 pr-4 text-xs text-muted">{f.suffix}</span>}
                    </span>
                    <span className="text-xs text-muted">{f.hint}</span>
                  </label>
                ))}
              </div>
            </section>
          ))}

          <div className="flex flex-col gap-4 p-6 sm:p-8">
            {started && missing.length > 0 && (
              <p className="rounded-xl bg-peach-50 px-4 py-3 text-sm text-peach-700">
                You can still submit. We will ask you for {missing.map((f) => f.label.toLowerCase()).join(", ")} before
                we assess anything.
              </p>
            )}
            <InlineError message={error} />
            <div className="flex flex-wrap items-center justify-between gap-4">
              <p className="text-xs text-muted">By submitting, you agree that your figures are checked by our AI analyst.</p>
              <Button type="submit" loading={submitting}>
                Submit application
              </Button>
            </div>
          </div>
        </form>

        <aside className="space-y-8 lg:sticky lg:top-24 lg:self-start">
          <div>
            <h2 className="text-sm font-bold text-ink">What happens next</h2>
            <ol className="mt-4 space-y-4">
              {[
                "We compute affordability from your numbers.",
                "If something is missing or doesn't match, we ask you one clear question.",
                "Larger loans and any possible decline always go to a loan officer.",
              ].map((t, i) => (
                <li key={t} className="flex gap-3 text-sm text-muted">
                  <span className="grid size-6 shrink-0 place-items-center rounded-full bg-brand-100 text-xs font-bold text-brand-700">
                    {i + 1}
                  </span>
                  {t}
                </li>
              ))}
            </ol>
          </div>
          <div className="border-t border-line pt-8">
            <h2 className="text-sm font-bold text-ink">Fair by design</h2>
            <p className="mt-2 text-sm text-muted">
              We never ask for your gender, age or family status, and they never reach our model.
            </p>
          </div>
        </aside>
      </Container>
    </>
  );
}
