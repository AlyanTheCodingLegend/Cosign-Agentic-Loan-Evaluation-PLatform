"use client";

import { useRouter } from "next/navigation";
import { useState, type ChangeEvent, type FormEvent } from "react";
import { Container, PageHeader } from "@/components/page-header";
import { Button, InlineError } from "@/components/ui";
import { data } from "@/lib/data";
import { errorMessage } from "@/lib/errors";
import type { ApplicationForm, DocumentKind } from "@/lib/types";

type FieldKey = "loan_amount" | "goods_price" | "annuity" | "annual_income" | "years_employed";

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
      { key: "annuity", label: "Loan annuity", hint: "The repayment amount on the loan.", required: true },
    ],
  },
  {
    title: "Your income",
    body: "The income you state here is checked against any document you attach below.",
    fields: [
      { key: "annual_income", label: "Annual income", hint: "Your total yearly income before tax.", required: true, suffix: "/ year" },
      { key: "years_employed", label: "Years with current employer", hint: "Use decimals for months, e.g. 1.5.", required: false, suffix: "years" },
    ],
  },
];

const FIELDS = SECTIONS.flatMap((s) => s.fields);

const DOCUMENT_KINDS: { value: DocumentKind; label: string }[] = [
  { value: "bank_statement", label: "Bank statement" },
  { value: "salary_slip", label: "Salary slip" },
];

// Plain-text files only: the API takes documents already converted to text.
const MAX_DOCUMENT_CHARS = 20_000;
const TEXT_FILE_ACCEPT = ".txt,.csv,.md,text/plain";

type NumberState = Record<FieldKey, string>;

const EMPTY: NumberState = { loan_amount: "", goods_price: "", annuity: "", annual_income: "", years_employed: "" };

function toNumber(raw: string): number | null {
  const trimmed = raw.replaceAll(",", "").trim();
  return trimmed === "" ? null : Number(trimmed);
}

function validate(values: NumberState): string | null {
  for (const f of FIELDS) {
    const n = toNumber(values[f.key]);
    if (n === null) continue;
    if (!Number.isFinite(n)) return `${f.label} must be a number.`;
    if (f.key === "years_employed" ? n < 0 : n <= 0) return `${f.label} must be greater than zero.`;
  }
  return null;
}

function buildForm(values: NumberState): ApplicationForm {
  return {
    annual_income: toNumber(values.annual_income),
    loan_amount: toNumber(values.loan_amount),
    annuity: toNumber(values.annuity),
    goods_price: toNumber(values.goods_price),
    years_employed: toNumber(values.years_employed),
    // Bureau scores never come from the applicant.
    ext_source_1: null,
    ext_source_2: null,
    ext_source_3: null,
  };
}

export default function ApplyPage() {
  const router = useRouter();
  const [values, setValues] = useState<NumberState>(EMPTY);
  const [docKind, setDocKind] = useState<DocumentKind>("bank_statement");
  const [docName, setDocName] = useState("");
  const [docText, setDocText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const required = FIELDS.filter((f) => f.required);
  const missing = required.filter((f) => values[f.key].trim() === "");
  const started = missing.length < required.length;

  async function onFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    try {
      const text = await file.text();
      if (text.length > MAX_DOCUMENT_CHARS) {
        setError(`That file is too long. Keep documents under ${MAX_DOCUMENT_CHARS.toLocaleString()} characters.`);
        return;
      }
      setDocText(text);
      setDocName(file.name);
      setError(null);
    } catch (err) {
      setError(`Could not read ${file.name}: ${errorMessage(err)}`);
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const invalid = validate(values);
    if (invalid) {
      setError(invalid);
      return;
    }
    setError(null);
    setSubmitting(true);
    const text = docText.trim();
    const documents = text ? [{ name: docName || `${docKind}.txt`, kind: docKind, text }] : [];
    try {
      const { id } = await data.createApplication({ form: buildForm(values), documents });
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
                  <label key={f.key} className="flex flex-col gap-1.5">
                    <span className="flex items-center gap-2 text-sm font-semibold text-ink">
                      {f.label}
                      {!f.required && <span className="text-xs font-normal text-muted">(optional)</span>}
                    </span>
                    <span className="flex items-center rounded-xl border border-line bg-white transition focus-within:border-brand-400 focus-within:ring-4 focus-within:ring-brand-100">
                      <input
                        inputMode="decimal"
                        value={values[f.key]}
                        onChange={(e) => setValues({ ...values, [f.key]: e.target.value })}
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

          <section className="grid gap-6 border-b border-line p-6 sm:p-8 md:grid-cols-[14rem_1fr]">
            <div>
              <h2 className="text-base font-bold text-ink">
                Supporting document <span className="text-xs font-normal text-muted">(optional)</span>
              </h2>
              <p className="mt-1 text-sm text-muted">
                Paste the text of a bank statement or salary slip. If it states an annual income, we compare it with
                yours.
              </p>
            </div>
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-3">
                <div className="inline-flex rounded-full bg-canvas p-1 ring-1 ring-inset ring-line">
                  {DOCUMENT_KINDS.map((k) => (
                    <button
                      key={k.value}
                      type="button"
                      onClick={() => setDocKind(k.value)}
                      className={`rounded-full px-4 py-1.5 text-sm font-semibold transition ${
                        docKind === k.value ? "bg-white text-ink shadow-sm ring-1 ring-line" : "text-muted hover:text-ink"
                      }`}
                    >
                      {k.label}
                    </button>
                  ))}
                </div>
                <label className="cursor-pointer rounded-full px-4 py-1.5 text-sm font-semibold text-brand-700 ring-1 ring-inset ring-brand-200 transition hover:bg-brand-50">
                  Load a .txt file
                  <input type="file" accept={TEXT_FILE_ACCEPT} onChange={onFile} className="sr-only" />
                </label>
                {docName && (
                  <span className="flex items-center gap-2 text-xs text-muted">
                    {docName}
                    <button
                      type="button"
                      onClick={() => {
                        setDocName("");
                        setDocText("");
                      }}
                      className="font-semibold text-rose-600 hover:text-rose-700"
                    >
                      Remove
                    </button>
                  </span>
                )}
              </div>
              <textarea
                value={docText}
                onChange={(e) => setDocText(e.target.value.slice(0, MAX_DOCUMENT_CHARS))}
                rows={6}
                placeholder={"Account holder statement, Jan to Dec\nEmployer: Acme Ltd.\nAnnual income: 150,000"}
                className="w-full resize-y rounded-xl border border-line px-4 py-3 font-mono text-sm text-ink outline-none transition placeholder:text-muted/40 focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
              />
              <p className="text-xs text-muted">
                Tip: a line like <span className="font-mono text-ink">Annual income: 150,000</span> is the clearest way to
                state yearly income. Leave out personal details such as your age or family status.
              </p>
            </div>
          </section>

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
                "We read your form and any document, and compute affordability in code.",
                "If something is missing or your income doesn't match the document, we ask you one clear question.",
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
