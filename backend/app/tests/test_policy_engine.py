import pytest
from app.services.policy_engine import evaluate_policy, Policy, EmailContext
from app.schemas.classification import EmailClassification


@pytest.fixture
def base_policy():
    return Policy(
        approval_categories={"job_recruitment", "financial", "legal_contractual"},
        approve_when_uncertain=True,
        approve_starred=True,
        allow_auto_send=False,
        min_confidence=0.80,
    )


def test_protected_category_requires_approval(base_policy):
    """Protected categories (job_recruitment, financial, legal_contractual) must require human approval."""
    context = EmailContext(is_starred=False, sender_is_vip=False)
    
    for category in ["job_recruitment", "financial", "legal_contractual"]:
        classification = EmailClassification(
            category=category,
            risk_level="low",
            confidence=0.95,
            rationale="Category test",
            requires_caution=True,
        )
        decision = evaluate_policy(context, classification, base_policy)
        assert decision.requires_approval is True
        assert decision.action == "pending_approval"
        assert "protected_category" in decision.reasons


def test_starred_email_requires_approval(base_policy):
    """Starred email must require approval when approve_starred is True."""
    context = EmailContext(is_starred=True, sender_is_vip=False)
    classification = EmailClassification(
        category="general",
        risk_level="low",
        confidence=0.99,
        rationale="General email",
        requires_caution=False,
    )
    decision = evaluate_policy(context, classification, base_policy)
    assert decision.requires_approval is True
    assert decision.action == "pending_approval"
    assert "starred_email" in decision.reasons


def test_vip_sender_requires_approval(base_policy):
    """Emails from configured VIP senders require human approval."""
    context = EmailContext(is_starred=False, sender_is_vip=True, sender="vip@board.com")
    classification = EmailClassification(
        category="general",
        risk_level="low",
        confidence=0.95,
        rationale="VIP regular inquiry",
        requires_caution=False,
    )
    decision = evaluate_policy(context, classification, base_policy)
    assert decision.requires_approval is True
    assert "vip_sender" in decision.reasons


def test_elevated_risk_requires_approval(base_policy):
    """Medium or high-risk emails always require approval."""
    context = EmailContext(is_starred=False, sender_is_vip=False)
    
    for risk in ["medium", "high"]:
        classification = EmailClassification(
            category="general",
            risk_level=risk,
            confidence=0.90,
            rationale="Elevated risk",
            requires_caution=True,
        )
        decision = evaluate_policy(context, classification, base_policy)
        assert decision.requires_approval is True
        assert "elevated_risk" in decision.reasons


def test_low_confidence_and_uncertain_fails_closed(base_policy):
    """Uncertain risk or confidence below min_confidence triggers approval requirement."""
    context = EmailContext(is_starred=False, sender_is_vip=False)
    
    # Low confidence
    low_conf = EmailClassification(
        category="general",
        risk_level="low",
        confidence=0.72,  # below 0.80
        rationale="Unsure classification",
        requires_caution=True,
    )
    decision = evaluate_policy(context, low_conf, base_policy)
    assert decision.requires_approval is True
    assert "uncertain_classification" in decision.reasons

    # Uncertain risk level
    uncertain_risk = EmailClassification(
        category="general",
        risk_level="uncertain",
        confidence=0.85,
        rationale="Ambiguous intent",
        requires_caution=True,
    )
    decision2 = evaluate_policy(context, uncertain_risk, base_policy)
    assert decision2.requires_approval is True
    assert "uncertain_classification" in decision2.reasons


def test_invalid_or_missing_classification_fails_closed(base_policy):
    """Missing or failed LLM classification must fail closed and require human review."""
    context = EmailContext(is_starred=False, sender_is_vip=False)
    decision = evaluate_policy(context, None, base_policy)
    assert decision.requires_approval is True
    assert decision.action == "pending_approval"
    assert "missing_or_invalid_classification" in decision.reasons


def test_low_risk_auto_send_disabled_becomes_draft_ready(base_policy):
    """Low-risk email with auto-send disabled becomes draft_ready, never sent."""
    context = EmailContext(is_starred=False, sender_is_vip=False)
    classification = EmailClassification(
        category="general",
        risk_level="low",
        confidence=0.95,
        rationale="Low risk inquiry",
        requires_caution=False,
    )
    decision = evaluate_policy(context, classification, base_policy)
    assert decision.requires_approval is False
    assert decision.action == "draft_ready"


def test_llm_cannot_override_policy():
    """An LLM's fields cannot grant itself approval if policy dictates approval."""
    policy = Policy(
        approval_categories={"financial"},
        approve_when_uncertain=True,
        approve_starred=True,
        allow_auto_send=True,  # Even if auto-send were globally enabled
        min_confidence=0.80,
    )
    context = EmailContext(is_starred=False, sender_is_vip=False)
    # LLM claims caution is False and category is financial
    classification = EmailClassification(
        category="financial",
        risk_level="low",
        confidence=0.99,
        rationale="Innocent invoice",
        requires_caution=False,
    )
    decision = evaluate_policy(context, classification, policy)
    # Protected category takes absolute precedence
    assert decision.requires_approval is True
    assert decision.action == "pending_approval"
