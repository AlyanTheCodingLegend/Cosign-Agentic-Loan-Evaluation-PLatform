# Risk policy

This is the policy the app, the prompted fallback model and the training labels all use. The numbers live in `api/app/config.py` and the logic in `api/app/agent/policy.py`. Change them there, then update this file and tell the other person.

It is a distilled policy checked against Home Credit outcomes, not real underwriter judgment. A fine-tuned model learns this policy; it does not learn how a human underwriter would decide.

## Inputs

- **Payment-to-income** = `AMT_ANNUITY / (AMT_INCOME_TOTAL / 12)`. The data has no existing-debt figure, so this is payment-to-income and not true debt-to-income.
- **Loan-to-income** = `AMT_CREDIT / AMT_INCOME_TOTAL`.
- **Score average** = mean of the `EXT_SOURCE_1/2/3` values that are present. Null scores are skipped, never imputed.

Currency is unspecified, so every cutoff is a ratio or a score, taken from percentiles of a 4,000-row stratified sample of `application_train.csv`.

## Recommendation rules

Checked in this order; the first match wins.

| Order | Condition | Recommendation |
| --- | --- | --- |
| 1 | All three external scores are null | `refer` |
| 2 | Payment-to-income **> 3.65** (p90), or score average **<= 0.35** (p15) | `decline` |
| 3 | Payment-to-income **> 2.77** (p75), or loan-to-income **> 5.23** (p75), or score average **<= 0.44** (p30) | `refer` |
| 4 | Otherwise | `approve` |

Loan-to-income only ever refers. It never declines on its own, because on this data it barely predicts default.

## Routing (applied on top of the recommendation)

Any application can still be sent to a human by the router, in this order:

1. Form income and document income differ by **more than 10%**: ask the applicant (`needs_info`).
2. Loan amount **above 1,129,500** (p90 of `AMT_CREDIT`): human sign-off (`pending_review`).
3. Recommendation is `decline` or `refer`: `pending_review`. Nothing is auto-rejected.
4. The model sets `needs_human`: `pending_review`.
5. Confidence **below 0.80**: `pending_review`.
6. Otherwise: `auto_cleared`.

Thresholds in the router trigger strictly (a value exactly at the limit does not trigger). In the recommendation rules, the score limits are inclusive (bottom percentile band) and the ratio limits are strict.

## Check against real outcomes

`python seed/validate_policy.py` applies this policy to the sample and prints the default rate per bucket (TARGET is used only for this check, never as an input):

| Bucket | Share | Default rate |
| --- | --- | --- |
| approve | 46% | 3.8% |
| refer | 31% | 8.4% |
| decline | 23% | 16.1% |

The overall default rate is 8.1%. The separation comes mainly from the external scores. The affordability ratios act as guardrails and are weak predictors of default on this data.

## Protected attributes

Gender, age or birth date, and family status are never inputs to the policy, a prompt or a training row.
