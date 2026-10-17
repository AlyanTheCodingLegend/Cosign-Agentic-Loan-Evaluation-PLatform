import { formatAmount, formatPercent, formatRatio, formatTime, humanize } from "@/lib/format";
import type { ApplicantFields, AuditEvent, Metrics, Status } from "@/lib/types";

const STEPS: { key: string; label: string; matches: Status[] }[] = [
  { key: "submitted", label: "Submitted", matches: ["submitted"] },
  { key: "analyzing", label: "Analyzing", matches: ["analyzing", "needs_info"] },
  { key: "routed", label: "Routed", matches: ["pending_review", "auto_cleared"] },
  { key: "decided", label: "Decided", matches: ["decided"] },
];

/** Horizontal progress through the status flow. needs_info pauses at the analyzing step. */
export function StatusSteps({ status }: { status: Status }) {
  const current = STEPS.findIndex((s) => s.matches.includes(status));
  const paused = status === "needs_info";
  return (
    <ol className="flex items-center gap-2">
      {STEPS.map((step, i) => {
        const done = i < current || status === "decided";
        const active = i === current && status !== "decided";
        return (
          <li key={step.key} className="flex flex-1 items-center gap-2 last:flex-none">
            <div className="flex items-center gap-2">
              <span
                className={`grid size-7 shrink-0 place-items-center rounded-full text-xs font-bold transition ${
                  done
                    ? "bg-brand-500 text-white"
                    : active
                      ? paused
                        ? "bg-peach-100 text-peach-700 ring-2 ring-peach-200"
                        : "animate-pulse-ring bg-brand-100 text-brand-700 ring-2 ring-brand-300"
                      : "bg-white text-muted ring-1 ring-line"
                }`}
              >
                {done ? "✓" : paused && active ? "?" : i + 1}
              </span>
              <span className={`hidden text-xs font-semibold sm:inline ${done || active ? "text-ink" : "text-muted"}`}>
                {active && paused ? "Waiting on you" : step.label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <span className={`h-0.5 flex-1 rounded-full ${i < current || status === "decided" ? "bg-brand-300" : "bg-line"}`} />
            )}
          </li>
        );
      })}
    </ol>
  );
}

export function ConfidenceMeter({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = value >= 0.8 ? "from-brand-300 to-brand-500" : value >= 0.6 ? "from-lavender-200 to-lavender-400" : "from-peach-200 to-peach-400";
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-xs font-medium text-muted">Model confidence</span>
        <span className="text-sm font-bold text-ink">{pct}%</span>
      </div>
      <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-brand-50 ring-1 ring-inset ring-line">
        <div className={`h-full rounded-full bg-gradient-to-r ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function MetricTiles({ metrics }: { metrics: Metrics | null }) {
  if (!metrics) {
    return (
      <p className="rounded-2xl border border-dashed border-line px-5 py-4 text-sm text-muted">
        Metrics are not computed yet. They are calculated in code once all required fields are present.
      </p>
    );
  }
  const tiles = [
    { label: "Loan to income", value: formatRatio(metrics.loan_to_income), hint: "loan ÷ annual income" },
    { label: "Payment to income", value: formatPercent(metrics.payment_to_income), hint: "installment ÷ monthly income" },
    {
      label: "Income mismatch",
      value: metrics.income_mismatch_pct == null ? "No document" : formatPercent(metrics.income_mismatch_pct),
      hint: "form vs document income",
    },
  ];
  return (
    <div className="grid divide-y divide-line rounded-2xl border border-line bg-white sm:grid-cols-3 sm:divide-x sm:divide-y-0">
      {tiles.map((t) => (
        <div key={t.label} className="p-5">
          <p className="text-xs font-medium text-muted">{t.label}</p>
          <p className="mt-1 text-2xl font-bold tracking-tight text-ink">{t.value}</p>
          <p className="mt-0.5 text-[11px] text-muted">{t.hint}</p>
        </div>
      ))}
    </div>
  );
}

const FIELD_ROWS: { key: keyof ApplicantFields; label: string; kind: "amount" | "years" | "score" }[] = [
  { key: "annual_income", label: "Annual income (form)", kind: "amount" },
  { key: "document_income", label: "Annual income (document)", kind: "amount" },
  { key: "loan_amount", label: "Loan amount", kind: "amount" },
  { key: "annuity", label: "Monthly installment", kind: "amount" },
  { key: "goods_price", label: "Goods price", kind: "amount" },
  { key: "years_employed", label: "Years employed", kind: "years" },
  { key: "ext_source_1", label: "External score 1", kind: "score" },
  { key: "ext_source_2", label: "External score 2", kind: "score" },
  { key: "ext_source_3", label: "External score 3", kind: "score" },
];

const BUREAU_FIELDS: (keyof ApplicantFields)[] = ["ext_source_1", "ext_source_2", "ext_source_3"];

/** Applicant fields; `formOnly` hides bureau scores, which the applicant never provides. */
export function FieldList({ fields, formOnly = false }: { fields: ApplicantFields | null; formOnly?: boolean }) {
  const rows = formOnly ? FIELD_ROWS.filter((r) => !BUREAU_FIELDS.includes(r.key)) : FIELD_ROWS;
  return (
    <dl className="divide-y divide-line">
      {rows.map((row) => {
        const v = fields?.[row.key] ?? null;
        const text = v == null ? null : row.kind === "amount" ? formatAmount(v) : row.kind === "years" ? `${v} yrs` : v.toFixed(2);
        return (
          <div key={row.key} className="flex items-center justify-between py-2.5 text-sm">
            <dt className="text-muted">{row.label}</dt>
            <dd className={text ? "font-semibold tabular-nums text-ink" : "rounded-full bg-peach-50 px-2 py-0.5 text-xs font-semibold text-peach-700"}>
              {text ?? "Missing"}
            </dd>
          </div>
        );
      })}
    </dl>
  );
}

const ACTOR_STYLE: Record<string, string> = {
  applicant: "bg-sky-100 text-sky-700",
  agent: "bg-brand-100 text-brand-700",
  router: "bg-lavender-100 text-lavender-700",
  reviewer: "bg-peach-100 text-peach-700",
};

function describe(event: AuditEvent): string {
  const { from, to, recommendation, confidence, decision, override, answer } = event.payload;
  if (event.event_type === "status_changed" && typeof to === "string") {
    return `${typeof from === "string" ? humanize(from) : "—"} → ${humanize(to)}`;
  }
  if (typeof recommendation === "string") {
    return `Recommended ${recommendation}${typeof confidence === "number" ? ` at ${Math.round(confidence * 100)}%` : ""}`;
  }
  if (typeof decision === "string") return `${humanize(decision)}${override === true ? " (override)" : ""}`;
  if (typeof answer === "string") return `“${answer}”`;
  return "";
}

export function AuditTrail({ events }: { events: AuditEvent[] }) {
  return (
    <section>
      <h2 className="text-base font-bold text-ink">Audit trail</h2>
      <p className="mt-0.5 text-sm text-muted">Append-only. Every state change is recorded.</p>
      {events.length === 0 ? (
        <p className="mt-4 text-sm text-muted">No events yet.</p>
      ) : (
        <ol className="relative ml-1 mt-5 border-l border-line">
          {events.map((e) => (
            <li key={e.id} className="mb-4 ml-4 last:mb-0">
              <span className="absolute -left-[5px] mt-1.5 size-2.5 rounded-full bg-brand-300 ring-4 ring-canvas" />
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${ACTOR_STYLE[e.actor] ?? "bg-slate-100 text-slate-600"}`}>
                  {e.actor}
                </span>
                <span className="text-sm font-medium text-ink">{humanize(e.event_type)}</span>
                <span className="ml-auto text-[11px] tabular-nums text-muted">{formatTime(e.created_at)}</span>
              </div>
              {describe(e) && <p className="mt-0.5 text-xs text-muted">{describe(e)}</p>}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
