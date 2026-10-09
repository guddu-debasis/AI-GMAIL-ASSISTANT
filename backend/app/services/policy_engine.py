from dataclasses import dataclass
from typing import Set, List, Dict, Any, Optional
from app.schemas.classification import EmailClassification


@dataclass(frozen=True)
class Policy:
    approval_categories: Set[str]
    approve_when_uncertain: bool = True
    approve_starred: bool = True
    allow_auto_send: bool = False
    min_confidence: float = 0.80


@dataclass(frozen=True)
class EmailContext:
    is_starred: bool = False
    sender_is_vip: bool = False
    sender: str = ""
    subject: Optional[str] = None


@dataclass(frozen=True)
class PolicyDecision:
    action: str  # "pending_approval", "draft_ready", "auto_send_eligible"
    requires_approval: bool
    reasons: List[str]


def evaluate_policy(
    email: EmailContext,
    classification: Optional[EmailClassification],
    policy: Policy,
) -> PolicyDecision:
    """
    Deterministic Policy Engine.
    Pure function that evaluates email context and LLM classification against user-defined policy.
    Never calls external services or databases.
    Fail-closed: Any invalid, missing, or untrusted input requires human approval.
    """
    reasons: List[str] = []

    # Fail closed for missing/invalid classification
    if classification is None:
        return PolicyDecision(
            action="pending_approval",
            requires_approval=True,
            reasons=["missing_or_invalid_classification"],
        )

    # 1. Starred email rule
    if email.is_starred and policy.approve_starred:
        reasons.append("starred_email")

    # 2. VIP sender rule
    if email.sender_is_vip:
        reasons.append("vip_sender")

    # 3. Protected category rule
    if classification.category in policy.approval_categories:
        reasons.append("protected_category")

    # 4. Elevated risk rule (medium or high risk)
    if classification.risk_level in {"medium", "high"}:
        reasons.append("elevated_risk")

    # 5. Uncertain classification / low confidence rule
    uncertain = (
        classification.risk_level == "uncertain"
        or classification.confidence < policy.min_confidence
    )
    if uncertain and policy.approve_when_uncertain:
        reasons.append("uncertain_classification")

    # If any reason triggered approval requirement:
    requires_approval = bool(reasons)

    if requires_approval:
        action = "pending_approval"
    elif policy.allow_auto_send:
        action = "auto_send_eligible"
    else:
        # Default safe posture: low risk, but auto-send is disabled -> draft ready
        action = "draft_ready"

    return PolicyDecision(
        action=action,
        requires_approval=requires_approval,
        reasons=reasons,
    )
