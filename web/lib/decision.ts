import type { DecisionRequest, HumanDecision, Recommendation } from "./types";

/**
 * Whether a reviewer's decision goes against the agent. Mirrors _resolve_final_decision in
 * api/app/agent/pipeline.py: a missing recommendation counts as refer, which never conflicts.
 */
export function contradictsAgent(decision: HumanDecision, recommendation: Recommendation | undefined): boolean {
  return (decision === "approve" && recommendation === "decline") || (decision === "reject" && recommendation === "approve");
}

/** Build the decision body: plain approve/reject, or an override carrying the final decision. */
export function decisionRequest(
  reviewerId: string,
  decision: HumanDecision,
  recommendation: Recommendation | undefined,
  reason: string | null,
): DecisionRequest {
  if (contradictsAgent(decision, recommendation)) {
    return { reviewer_id: reviewerId, action: "override", final_decision: decision, reason };
  }
  return { reviewer_id: reviewerId, action: decision, final_decision: null, reason };
}
