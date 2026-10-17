import Link from "next/link";
import type { ReactNode } from "react";
import { Container } from "@/components/page-header";

const STEPS = [
  { title: "Apply", body: "Tell us the loan amount, the price of the goods and your income. No paperwork maze." },
  { title: "Analyze", body: "Our AI analyst extracts your details and computes affordability ratios in code." },
  { title: "Route", body: "Clear rules decide: approve quickly, ask you a question, or bring in a loan officer." },
  { title: "Decide", body: "A person signs off on every hard case, and every decline, with the reason on record." },
];

const FACTS = [
  { value: "0", label: "automatic rejections" },
  { value: "100%", label: "of actions in the audit log" },
  { value: "5", label: "explainable routing rules" },
  { value: "0", label: "protected attributes in the model" },
];

const FAQ = [
  {
    q: "Does an AI decide whether I get a loan?",
    a: "No. The AI analyst prepares a recommendation with reasons. Clear cases can be approved quickly, but any possible decline, any large loan and any case with conflicting data is decided by a human loan officer.",
  },
  {
    q: "What information do you use?",
    a: "Your income, the loan amount, the loan annuity, the price of what you are buying and, if you share it, your employment history and bank statement income. We never ask for or use gender, age or family status.",
  },
  {
    q: "What happens if my numbers don't match?",
    a: "We pause and ask you a specific question, for example which of two income figures is correct. Once you answer, your application picks up where it left off.",
  },
  {
    q: "Can a loan officer disagree with the AI?",
    a: "Yes, and they often should. Every override is stored with the officer's reason, so decisions stay accountable.",
  },
];

export default function Home() {
  return (
    <>
      <Hero />

      <section className="border-y border-line bg-white">
        <Container className="flex flex-wrap items-center justify-center gap-x-10 gap-y-3 py-6 text-sm text-muted">
          <span className="font-semibold text-ink">Built on</span>
          <span>Home Credit lending data</span>
          <span className="hidden text-line sm:inline">•</span>
          <span>An open language model</span>
          <span className="hidden text-line sm:inline">•</span>
          <span>FastAPI agent with MCP tools</span>
          <span className="hidden text-line sm:inline">•</span>
          <span>Supabase realtime</span>
        </Container>
      </section>

      <section id="how-it-works" className="scroll-mt-20 bg-white py-20 sm:py-24">
        <Container>
          <SectionHeading
            eyebrow="How it works"
            title="From application to decision in four steps"
            body="The AI handles the legwork. People handle judgment. You always know which one is looking at your case."
          />
          <ol className="relative mt-14 grid gap-10 md:grid-cols-4 md:gap-6">
            <span aria-hidden className="absolute left-0 right-0 top-6 hidden h-px bg-brand-200 md:block" />
            {STEPS.map((s, i) => (
              <li key={s.title} className="relative">
                <span className="relative grid size-12 place-items-center rounded-full bg-brand-600 text-lg font-bold text-white ring-8 ring-white">
                  {i + 1}
                </span>
                <h3 className="mt-5 text-lg font-bold text-ink">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{s.body}</p>
              </li>
            ))}
          </ol>
        </Container>
      </section>

      <section className="py-20 sm:py-24">
        <Container className="space-y-24">
          <FeatureRow
            eyebrow="Explainable"
            title="Every reason points to a real number"
            body="Recommendations come with reasons that cite your actual figures, such as payment-to-income or loan-to-income. The arithmetic is done in code, never guessed by the model."
            points={["Ratios computed by code, not the AI", "Reasons tied to specific fields", "Confidence shown to the officer"]}
            visual={<ReasonsMock />}
          />
          <FeatureRow
            reverse
            eyebrow="Human in the loop"
            title="When something doesn't add up, we ask"
            body="Missing details or an income that differs from your bank statement? The agent pauses and asks you one specific question instead of guessing, then resumes when you answer."
            points={["No silent assumptions", "One clear question at a time", "Your case resumes automatically"]}
            visual={<QuestionMock />}
          />
          <FeatureRow
            eyebrow="Accountable"
            title="Officers can overrule the AI, on the record"
            body="Loan officers see the full picture and make the final call. When they disagree with the recommendation, their reason is saved alongside it in an append-only log."
            points={["Append-only audit trail", "Every override has a reason", "Nothing is deleted or rewritten"]}
            visual={<AuditMock />}
          />
        </Container>
      </section>

      <section id="principles" className="scroll-mt-20 bg-brand-700 py-16 text-white">
        <Container>
          <div className="grid gap-10 lg:grid-cols-[1fr_1.4fr] lg:items-center">
            <div>
              <p className="text-sm font-semibold text-brand-200">Our principles</p>
              <h2 className="mt-2 text-3xl font-extrabold tracking-tight">Built so that people stay in charge</h2>
              <p className="mt-4 text-brand-100/80">
                These aren&apos;t settings. They are rules built into how the system works.
              </p>
            </div>
            <dl className="grid grid-cols-2 gap-x-8 gap-y-10">
              {FACTS.map((f) => (
                <div key={f.label} className="border-l-2 border-brand-300 pl-5">
                  <dt className="text-4xl font-extrabold tracking-tight">{f.value}</dt>
                  <dd className="mt-1 text-sm text-brand-100/80">{f.label}</dd>
                </div>
              ))}
            </dl>
          </div>
        </Container>
      </section>

      <section className="bg-white py-20 sm:py-24">
        <Container className="grid gap-6 md:grid-cols-2">
          <Audience
            tone="bg-brand-50"
            eyebrow="For applicants"
            title="A fair answer, without the guesswork"
            points={["Apply in about a minute", "Track your application live", "Answer questions in plain language"]}
            cta={{ href: "/apply", label: "Start your application" }}
          />
          <Audience
            tone="bg-lavender-50"
            eyebrow="For loan officers"
            title="Spend your time on the cases that need you"
            points={["A live queue of escalated cases", "Ratios, reasons and history on one page", "Approve, reject or override with a reason"]}
            cta={{ href: "/review", label: "Open the review queue" }}
          />
        </Container>
      </section>

      <section id="faq" className="scroll-mt-20 py-20 sm:py-24">
        <Container className="grid gap-12 lg:grid-cols-[1fr_1.6fr]">
          <SectionHeading
            align="left"
            eyebrow="FAQ"
            title="Questions, answered"
            body="Straight answers about how decisions are made."
          />
          <div className="divide-y divide-line border-y border-line">
            {FAQ.map((item) => (
              <details key={item.q} className="group py-5">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold text-ink">
                  {item.q}
                  <span className="grid size-7 shrink-0 place-items-center rounded-full bg-brand-50 text-brand-700 transition group-open:rotate-45">
                    +
                  </span>
                </summary>
                <p className="mt-3 pr-10 text-sm leading-relaxed text-muted">{item.a}</p>
              </details>
            ))}
          </div>
        </Container>
      </section>

      <section className="pb-20">
        <Container>
          <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-brand-100 via-brand-50 to-lavender-50 px-8 py-14 text-center sm:px-16">
            <h2 className="text-3xl font-extrabold tracking-tight text-ink">Ready when you are</h2>
            <p className="mx-auto mt-3 max-w-lg text-muted">
              Submit an application and watch it move through the system in real time.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <Link href="/apply" className="rounded-full bg-brand-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-brand-700">
                Apply for a loan
              </Link>
              <Link href="/review" className="rounded-full bg-white px-6 py-3 text-sm font-semibold text-brand-800 transition hover:bg-brand-50">
                Review cases
              </Link>
            </div>
          </div>
        </Container>
      </section>
    </>
  );
}

function Hero() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-brand-50 via-canvas to-canvas">
      <div aria-hidden className="absolute -right-40 -top-40 size-[36rem] rounded-full bg-brand-100 blur-3xl" />
      <div aria-hidden className="absolute -left-32 top-40 size-[24rem] rounded-full bg-lavender-100/70 blur-3xl" />
      <Container className="relative grid items-center gap-14 py-20 lg:grid-cols-[1.05fr_1fr] lg:py-28">
        <div>
          <p className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-xs font-semibold text-brand-700 shadow-sm ring-1 ring-brand-100">
            <span className="size-1.5 rounded-full bg-brand-400" /> Human-in-the-loop lending
          </p>
          <h1 className="mt-6 text-4xl font-extrabold leading-[1.05] tracking-tight text-ink sm:text-6xl">
            Loans decided by people,
            <span className="block text-brand-600">prepared by AI.</span>
          </h1>
          <p className="mt-6 max-w-lg text-lg leading-relaxed text-muted">
            Clearpath&apos;s AI analyst checks your numbers in seconds. A loan officer steps in wherever judgment is
            needed, and nothing is ever rejected without a human looking at it.
          </p>
          <div className="mt-9 flex flex-wrap gap-3">
            <Link href="/apply" className="rounded-full bg-brand-600 px-7 py-3.5 text-sm font-semibold text-white shadow-lg shadow-brand-600/20 transition hover:bg-brand-700">
              Apply for a loan
            </Link>
            <Link href="/#how-it-works" className="rounded-full px-7 py-3.5 text-sm font-semibold text-brand-800 ring-1 ring-inset ring-brand-200 transition hover:bg-white">
              See how it works
            </Link>
          </div>
          <ul className="mt-10 flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted">
            {["Takes about a minute", "Every decision explained", "Never auto-rejected"].map((t) => (
              <li key={t} className="flex items-center gap-2">
                <Check /> {t}
              </li>
            ))}
          </ul>
        </div>
        <BrowserFrame>
          <QueueMock />
        </BrowserFrame>
      </Container>
    </section>
  );
}

function SectionHeading({
  eyebrow,
  title,
  body,
  align = "center",
}: {
  eyebrow: string;
  title: string;
  body: string;
  align?: "center" | "left";
}) {
  return (
    <div className={align === "center" ? "mx-auto max-w-2xl text-center" : ""}>
      <p className="text-sm font-semibold text-brand-600">{eyebrow}</p>
      <h2 className="mt-2 text-3xl font-extrabold tracking-tight text-ink sm:text-4xl">{title}</h2>
      <p className="mt-4 text-muted">{body}</p>
    </div>
  );
}

function FeatureRow({
  eyebrow,
  title,
  body,
  points,
  visual,
  reverse = false,
}: {
  eyebrow: string;
  title: string;
  body: string;
  points: string[];
  visual: ReactNode;
  reverse?: boolean;
}) {
  return (
    <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-20">
      <div className={reverse ? "lg:order-2" : ""}>
        <p className="text-sm font-semibold text-brand-600">{eyebrow}</p>
        <h2 className="mt-2 text-3xl font-extrabold tracking-tight text-ink">{title}</h2>
        <p className="mt-4 leading-relaxed text-muted">{body}</p>
        <ul className="mt-6 space-y-3">
          {points.map((p) => (
            <li key={p} className="flex items-center gap-3 text-sm font-medium text-ink">
              <Check /> {p}
            </li>
          ))}
        </ul>
      </div>
      <div className="rounded-3xl bg-gradient-to-br from-brand-50 to-lavender-50 p-6 sm:p-10">{visual}</div>
    </div>
  );
}

function Audience({
  tone,
  eyebrow,
  title,
  points,
  cta,
}: {
  tone: string;
  eyebrow: string;
  title: string;
  points: string[];
  cta: { href: string; label: string };
}) {
  return (
    <div className={`flex flex-col rounded-3xl p-8 sm:p-10 ${tone}`}>
      <p className="text-sm font-semibold text-brand-700">{eyebrow}</p>
      <h3 className="mt-2 text-2xl font-extrabold tracking-tight text-ink">{title}</h3>
      <ul className="mt-6 flex-1 space-y-3">
        {points.map((p) => (
          <li key={p} className="flex items-center gap-3 text-sm text-ink">
            <Check /> {p}
          </li>
        ))}
      </ul>
      <Link href={cta.href} className="mt-8 text-sm font-semibold text-brand-700 hover:text-brand-900">
        {cta.label} →
      </Link>
    </div>
  );
}

function Check() {
  return (
    <span className="grid size-5 shrink-0 place-items-center rounded-full bg-brand-100 text-brand-700">
      <svg viewBox="0 0 24 24" className="size-3" fill="none" stroke="currentColor" strokeWidth={3}>
        <path d="M5 12.5l4.2 4.2L19 7" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  );
}

function BrowserFrame({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-hidden rounded-2xl bg-white shadow-2xl shadow-brand-900/10 ring-1 ring-line">
      <div className="flex items-center gap-2 border-b border-line bg-canvas px-4 py-3">
        <span className="size-2.5 rounded-full bg-rose-200" />
        <span className="size-2.5 rounded-full bg-peach-200" />
        <span className="size-2.5 rounded-full bg-brand-200" />
        <span className="ml-3 flex-1 rounded-md bg-white px-3 py-1 text-[11px] text-muted ring-1 ring-line">clearpath.app/review</span>
      </div>
      {children}
    </div>
  );
}

const MOCK_ROWS = [
  { id: "F6C8B7A9", rec: "Decline", recClass: "bg-rose-50 text-rose-700", amount: "1,150,000", status: "In review" },
  { id: "D4A6F5E7", rec: "Approve", recClass: "bg-brand-50 text-brand-700", amount: "2,400,000", status: "In review" },
  { id: "C3F5E4D6", rec: "Refer", recClass: "bg-lavender-50 text-lavender-700", amount: "780,000", status: "In review" },
  { id: "A1F3C2D4", rec: "Approve", recClass: "bg-brand-50 text-brand-700", amount: "300,000", status: "Auto-cleared" },
];

function QueueMock() {
  return (
    <div className="p-5">
      <div className="flex items-center justify-between">
        <p className="text-sm font-bold text-ink">Review queue</p>
        <span className="flex items-center gap-1.5 text-[11px] font-semibold text-brand-700">
          <span className="size-1.5 animate-pulse rounded-full bg-brand-400" /> Live
        </span>
      </div>
      <table className="mt-4 w-full text-left text-xs">
        <thead className="text-muted">
          <tr className="border-b border-line">
            <th className="pb-2 font-medium">Case</th>
            <th className="pb-2 font-medium">Agent</th>
            <th className="pb-2 text-right font-medium">Amount</th>
            <th className="pb-2 text-right font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {MOCK_ROWS.map((r) => (
            <tr key={r.id} className="border-b border-line last:border-0">
              <td className="py-3 font-mono font-semibold text-ink">#{r.id}</td>
              <td className="py-3">
                <span className={`rounded-full px-2 py-0.5 font-semibold ${r.recClass}`}>{r.rec}</span>
              </td>
              <td className="py-3 text-right tabular-nums text-ink">{r.amount}</td>
              <td className="py-3 text-right text-muted">{r.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ReasonsMock() {
  return (
    <div className="rounded-2xl bg-white p-6 shadow-xl shadow-brand-900/5">
      <div className="flex items-center justify-between">
        <p className="text-sm font-bold text-ink">Agent recommendation</p>
        <span className="rounded-full bg-lavender-50 px-2.5 py-1 text-xs font-semibold text-lavender-700">Refer · 60%</span>
      </div>
      <div className="mt-3 h-1.5 rounded-full bg-brand-50">
        <div className="h-full w-[60%] rounded-full bg-gradient-to-r from-peach-200 to-peach-400" />
      </div>
      <ul className="mt-5 space-y-2.5 text-sm text-ink">
        <li className="border-l-2 border-brand-300 pl-3">payment_to_income 3.00 is above the 2.77 refer limit</li>
        <li className="border-l-2 border-brand-300 pl-3">average external score 0.42 is in the refer band</li>
        <li className="border-l-2 border-brand-300 pl-3">two external scores are missing</li>
      </ul>
    </div>
  );
}

function QuestionMock() {
  return (
    <div className="rounded-2xl bg-white p-6 shadow-xl shadow-brand-900/5">
      <p className="text-xs font-semibold uppercase tracking-wider text-peach-700">We have a question</p>
      <p className="mt-2 text-sm font-semibold text-ink">
        The income on your form (900,000) differs from your bank statement (720,000). Which figure is correct?
      </p>
      <div className="mt-4 rounded-xl bg-canvas px-4 py-3 text-sm text-muted ring-1 ring-line">
        The statement is correct, my form included a one-off bonus.
      </div>
      <div className="mt-4 flex justify-end">
        <span className="rounded-full bg-brand-600 px-4 py-2 text-xs font-semibold text-white">Send answer</span>
      </div>
    </div>
  );
}

function AuditMock() {
  const rows = [
    { who: "agent", what: "Recommended decline at 85%", tone: "bg-brand-100 text-brand-700" },
    { who: "router", what: "Analyzing → Pending review", tone: "bg-lavender-100 text-lavender-700" },
    { who: "reviewer", what: "Approve (override)", tone: "bg-peach-100 text-peach-700" },
  ];
  return (
    <div className="rounded-2xl bg-white p-6 shadow-xl shadow-brand-900/5">
      <p className="text-sm font-bold text-ink">Audit trail</p>
      <ol className="mt-4 space-y-4 border-l border-line pl-5">
        {rows.map((r) => (
          <li key={r.what} className="relative">
            <span className="absolute -left-[25px] top-1 size-2.5 rounded-full bg-brand-300 ring-4 ring-white" />
            <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${r.tone}`}>{r.who}</span>
            <p className="mt-1 text-sm text-ink">{r.what}</p>
          </li>
        ))}
      </ol>
      <p className="mt-5 rounded-xl bg-peach-50 px-4 py-3 text-xs text-peach-700">
        “Four years with the same employer and a matching bank statement; payment is affordable.”
      </p>
    </div>
  );
}
