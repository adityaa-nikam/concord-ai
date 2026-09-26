import os
import json
import time
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import httpx

from app.core.config import settings
from app.schemas.reconciliation import ReconciliationResult, Conflict
from app.policies.schemas import PolicyCitation
from app.services.tat_engine import TATEvaluationResult

logger = logging.getLogger("tat_guardian.core.llm_provider")


# =========================================================
# Structured Pydantic LLM Schemas
# =========================================================

class AIEvidenceAssessment(BaseModel):
    assessment: str = Field(description="CROSS_SYSTEM_CONFLICT, PENDING_CONSISTENT, ALREADY_RESOLVED, INCONSISTENT_HOLD, or INCOMPLETE")
    known_facts: List[str] = Field(default_factory=list, description="List of verified system facts extracted from tool telemetry")
    uncertainties: List[str] = Field(default_factory=list, description="Telemetry gaps or unresolved questions")
    recommended_next_evidence: List[str] = Field(default_factory=list, description="List of allowlisted investigation tools to call next if evidence is incomplete")
    risk_flags: List[str] = Field(default_factory=list, description="Risk flags such as high-value, prompt injection, or administrative holds")
    reasoning_summary: str = Field(description="Concise natural-language synthesis of the evidence assessment")


class AIResolutionProposal(BaseModel):
    decision: str = Field(description="Proposed decision: ACT, WAIT, or ESCALATE")
    action: Optional[str] = Field(default=None, description="Proposed action from allowlist: INITIATE_REVERSAL, WAIT_AND_MONITOR, CREATE_ESCALATION, SEND_NOTIFICATION")
    reason_code: str = Field(description="Standard reason code: ELIGIBLE_EXCEPTION, PENDING_WITHIN_TAT, ALREADY_RESOLVED, INCONSISTENT_BANK_HOLD, HIGH_VALUE_THRESHOLD_EXCEEDED, etc.")
    requires_verification: bool = Field(default=True, description="Whether post-action verification is required")
    confidence: float = Field(default=0.90, description="Model confidence score (0.0 to 1.0)")
    reasoning_summary: str = Field(description="Concise decision rationale explaining why this resolution path is proposed under retrieved policy")


class LLMProvider:
    """Configurable LLM Provider supporting LIVE LLM (OpenAI / Gemini API) and MOCK LLM modes."""

    @classmethod
    def get_provider_name(cls) -> str:
        prov = os.getenv("LLM_PROVIDER", getattr(settings, "LLM_PROVIDER", "mistral")).lower()
        key = cls.get_api_key()
        if key:
            if key.startswith("mstrl_"):
                return "mistral"
            if key.startswith("gsk_"):
                return "groq"
        return prov

    @classmethod
    def get_model_name(cls) -> str:
        prov = cls.get_provider_name()
        if prov == "groq":
            default_model = "llama-3.3-70b-versatile"
        elif prov == "mistral":
            default_model = "mistral-small-latest"
        else:
            default_model = "gpt-4o"
        return os.getenv("LLM_MODEL", getattr(settings, "LLM_MODEL", default_model))

    @classmethod
    def get_api_key(cls) -> Optional[str]:
        key = (
            os.getenv("MISTRAL_API_KEY") or
            getattr(settings, "MISTRAL_API_KEY", None) or
            os.getenv("GROQ_API_KEY") or
            os.getenv("OPENAI_API_KEY") or
            getattr(settings, "OPENAI_API_KEY", None) or
            os.getenv("ANTHROPIC_API_KEY") or
            getattr(settings, "ANTHROPIC_API_KEY", None) or
            os.getenv("GOOGLE_API_KEY") or
            os.getenv("LLM_API_KEY")
        )
        if key and not key.startswith("your_"):
            return key
        return None

    @classmethod
    def is_live_mode(cls) -> bool:
        provider = cls.get_provider_name()
        api_key = cls.get_api_key()
        return provider in ["mistral", "groq", "openai", "gemini", "anthropic", "openrouter"] and bool(api_key)


    # =========================================================
    # 1. AI Evidence Interpretation
    # =========================================================

    @classmethod
    def assess_evidence(
        cls,
        customer_message: str,
        normalized_evidence: List[Dict[str, Any]],
        reconciliation_summary: str,
        reconciled_category: str,
        conflicts: List[Dict[str, Any]],
        missing_fields: List[str],
        already_called_tools: Optional[List[str]] = None
    ) -> AIEvidenceAssessment:
        """Invokes LLM (or mock) to reason broadly over structured evidence and recommend next investigation steps."""
        start_time = time.time()
        provider = cls.get_provider_name()
        called_set = set(already_called_tools or [])

        if not cls.is_live_mode():
            logger.info(f"LLM Provider: Executing MOCK assessment mode (Provider: {provider}).")
            mock_res = cls._mock_assess_evidence(
                customer_message=customer_message,
                normalized_evidence=normalized_evidence,
                reconciled_category=reconciled_category,
                conflicts=conflicts,
                missing_fields=missing_fields,
                already_called_tools=already_called_tools
            )
            mock_res.recommended_next_evidence = [t for t in mock_res.recommended_next_evidence if t not in called_set]
            return mock_res

        # LIVE LLM Completion
        try:
            logger.info(f"LLM Provider: Executing LIVE LLM completion via {provider} ({cls.get_model_name()}).")
            prompt = cls._build_evidence_assessment_prompt(
                customer_message=customer_message,
                normalized_evidence=normalized_evidence,
                reconciliation_summary=reconciliation_summary,
                reconciled_category=reconciled_category,
                conflicts=conflicts,
                missing_fields=missing_fields
            )
            raw_json = cls._call_llm_api(prompt, schema_class=AIEvidenceAssessment)
            result = AIEvidenceAssessment(**raw_json)
            # Filter out tools already executed
            result.recommended_next_evidence = [t for t in result.recommended_next_evidence if t not in called_set]
            latency_ms = round((time.time() - start_time) * 1000, 2)
            logger.info(f"LIVE LLM Evidence Assessment succeeded in {latency_ms} ms.")
            return result
        except Exception as e:
            logger.error(f"LIVE LLM evidence assessment call failed ({e}). Falling back to safe assessment.")
            return AIEvidenceAssessment(
                assessment="LIVE_LLM_FAILURE",
                known_facts=[],
                uncertainties=[f"Live LLM provider error: {str(e)}"],
                recommended_next_evidence=[],
                risk_flags=["LLM_SERVICE_UNAVAILABLE"],
                reasoning_summary=f"Live LLM provider call failed ({e}). System requires safe evaluation."
            )

    # =========================================================
    # 2. AI Resolution Proposal
    # =========================================================

    @classmethod
    def propose_resolution(
        cls,
        customer_message: str,
        reconciliation: ReconciliationResult,
        citations: List[PolicyCitation],
        tat_result: TATEvaluationResult,
        amount: float = 0.0,
        prompt_injection_detected: bool = False
    ) -> AIResolutionProposal:
        """Invokes LLM (or mock) to propose structured resolution (ACT / WAIT / ESCALATE) under policy constraints."""
        start_time = time.time()
        provider = cls.get_provider_name()

        if not cls.is_live_mode():
            logger.info(f"LLM Provider: Executing MOCK resolution proposal mode (Provider: {provider}).")
            return cls._mock_propose_resolution(
                customer_message=customer_message,
                reconciliation=reconciliation,
                citations=citations,
                tat_result=tat_result,
                amount=amount,
                prompt_injection_detected=prompt_injection_detected
            )

        # LIVE LLM Completion
        try:
            logger.info(f"LLM Provider: Executing LIVE LLM resolution proposal via {provider} ({cls.get_model_name()}).")
            prompt = cls._build_resolution_proposal_prompt(
                customer_message=customer_message,
                reconciliation=reconciliation,
                citations=citations,
                tat_result=tat_result,
                amount=amount,
                prompt_injection_detected=prompt_injection_detected
            )
            raw_json = cls._call_llm_api(prompt, schema_class=AIResolutionProposal)
            result = AIResolutionProposal(**raw_json)
            latency_ms = round((time.time() - start_time) * 1000, 2)
            logger.info(f"LIVE LLM Resolution Proposal succeeded in {latency_ms} ms.")
            return result
        except Exception as e:
            logger.error(f"LIVE LLM resolution proposal failed ({e}). Safely escalating case.")
            return AIResolutionProposal(
                decision="ESCALATE",
                action="CREATE_ESCALATION",
                reason_code="LLM_PROVIDER_FAILURE",
                requires_verification=True,
                confidence=0.0,
                reasoning_summary=f"Live LLM API call failed ({e}). System safely escalated dispute to human operations to prevent unauthorized financial action."
            )

    # =========================================================
    # Mock LLM Fallback Heuristics
    # =========================================================

    @classmethod
    def _mock_assess_evidence(
        cls,
        customer_message: str,
        normalized_evidence: List[Dict[str, Any]],
        reconciled_category: str,
        conflicts: List[Dict[str, Any]],
        missing_fields: List[str],
        already_called_tools: Optional[List[str]] = None
    ) -> AIEvidenceAssessment:
        facts = [f"{item.get('source')}.{item.get('field')} = {item.get('value')}" for item in normalized_evidence[:5]]
        uncertainties = []
        next_ev = []
        called_set = set(already_called_tools or [])

        if ("beneficiary_credit_status" in missing_fields or "beneficiary_data" in missing_fields) and "get_beneficiary_status" not in called_set:
            uncertainties.append("Beneficiary bank credit confirmation is unconfirmed")
            next_ev.append("get_beneficiary_status")

        reasoning = f"AI Assessment: Evaluated {len(normalized_evidence)} telemetry items. Category: {reconciled_category}."
        if conflicts:
            reasoning += f" Detected {len(conflicts)} system conflict(s): {conflicts[0].get('summary', '')}"

        return AIEvidenceAssessment(
            assessment=reconciled_category,
            known_facts=facts,
            uncertainties=uncertainties,
            recommended_next_evidence=next_ev,
            risk_flags=["PROMPT_INJECTION_RISK"] if "ignore" in (customer_message or "").lower() else [],
            reasoning_summary=reasoning
        )

    @classmethod
    def _mock_propose_resolution(
        cls,
        customer_message: str,
        reconciliation: ReconciliationResult,
        citations: List[PolicyCitation],
        tat_result: TATEvaluationResult,
        amount: float = 0.0,
        prompt_injection_detected: bool = False
    ) -> AIResolutionProposal:
        top_pol = citations[0].policy_id if citations else "POL-FALLBACK"

        if prompt_injection_detected:
            return AIResolutionProposal(
                decision="ESCALATE",
                action="CREATE_ESCALATION",
                reason_code="PROMPT_INJECTION_ATTEMPT_DETECTED",
                requires_verification=False,
                confidence=0.99,
                reasoning_summary="Untrusted customer message contains prompt injection instructions. Escalating to human ops."
            )

        if reconciliation.status == "ALREADY_RESOLVED" or reconciliation.reconciled_case_category == "ALREADY_RESOLVED":
            return AIResolutionProposal(
                decision="RESOLVE",
                action="SEND_NOTIFICATION",
                reason_code="ALREADY_RESOLVED",
                requires_verification=False,
                confidence=0.98,
                reasoning_summary="Evidence confirms transaction was already reversed prior. Proposing notification to customer."
            )

        if amount > 50000.0 and reconciliation.status == "CONFLICT":
            return AIResolutionProposal(
                decision="ESCALATE",
                action="CREATE_ESCALATION",
                reason_code="HIGH_VALUE_THRESHOLD_EXCEEDED",
                requires_verification=True,
                confidence=0.95,
                reasoning_summary=f"Dispute amount ₹{amount} exceeds automated limit ₹50,000 for cross-system conflicts. Proposing Tier 2 Ops escalation."
            )

        if reconciliation.reconciled_case_category == "PENDING_CONSISTENT":
            return AIResolutionProposal(
                decision="WAIT",
                action="WAIT_AND_MONITOR",
                reason_code="PENDING_WITHIN_TAT",
                requires_verification=True,
                confidence=0.92,
                reasoning_summary="Transaction is pending consistently across gateway and core ledger within clearing buffer. Proposing WAIT & MONITOR."
            )

        if reconciliation.status == "CONFLICT" and reconciliation.reconciled_case_category == "CROSS_SYSTEM_CONFLICT":
            return AIResolutionProposal(
                decision="ACT",
                action="INITIATE_REVERSAL",
                reason_code="ELIGIBLE_EXCEPTION",
                requires_verification=True,
                confidence=0.95,
                reasoning_summary=f"Cross-system state conflict detected (Gateway SUCCESS vs Payee NOT_CREDITED). Proposing AUTO_REVERSAL under {top_pol}."
            )

        return AIResolutionProposal(
            decision="ESCALATE",
            action="CREATE_ESCALATION",
            reason_code="UNRESOLVED_CROSS_SYSTEM_CONFLICT",
            requires_verification=True,
            confidence=0.70,
            reasoning_summary="Unresolved state discrepancy across system boundaries. Proposing human ops escalation."
        )

    # =========================================================
    # Live HTTP LLM API Client (OpenAI JSON Schema Completion)
    # =========================================================

    @classmethod
    def _call_llm_api(cls, prompt: str, schema_class: type[BaseModel]) -> Dict[str, Any]:
        api_key = cls.get_api_key()
        model = cls.get_model_name()
        provider = cls.get_provider_name()

        if provider == "groq" or (api_key and api_key.startswith("gsk_")):
            url = "https://api.groq.com/openai/v1/chat/completions"
        elif provider == "mistral" or (api_key and api_key.startswith("mstrl_")):
            url = "https://api.mistral.ai/v1/chat/completions"
        else:
            url = "https://api.openai.com/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": f"You are Concord-AI, an expert autonomous payment exception resolution agent. Return JSON strictly matching schema: {schema_class.model_json_schema()}"},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }

        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)


    @classmethod
    def _build_evidence_assessment_prompt(cls, customer_message, normalized_evidence, reconciliation_summary, reconciled_category, conflicts, missing_fields) -> str:
        return f"""
UNTRUSTED Customer Complaint: "{customer_message}"

Normalized Telemetry: {json.dumps(normalized_evidence)}
Reconciliation Category: {reconciled_category}
Summary: {reconciliation_summary}
Conflicts: {json.dumps(conflicts)}
Missing Fields: {json.dumps(missing_fields)}

Provide structured JSON matching AIEvidenceAssessment schema:
- assessment
- known_facts (list of strings)
- uncertainties (list of strings)
- recommended_next_evidence (list of allowlisted tools if telemetry missing)
- risk_flags (list of strings)
- reasoning_summary
"""

    @classmethod
    def _build_resolution_proposal_prompt(cls, customer_message, reconciliation, citations, tat_result, amount, prompt_injection_detected) -> str:
        top_pol = citations[0].policy_id if citations else "POL-NONE"
        return f"""
Customer Complaint: "{customer_message}"
Amount: ₹{amount}
Reconciliation Status: {reconciliation.status} ({reconciliation.reconciled_case_category})
Top Policy Citation: {top_pol}
TAT Status: {tat_result.tat_status}
Prompt Injection Flag: {prompt_injection_detected}

Propose a structured JSON resolution matching AIResolutionProposal schema:
- decision: "ACT", "WAIT", or "ESCALATE"
- action: "INITIATE_REVERSAL", "WAIT_AND_MONITOR", "CREATE_ESCALATION", or "SEND_NOTIFICATION"
- reason_code: "ELIGIBLE_EXCEPTION", "PENDING_WITHIN_TAT", "ALREADY_RESOLVED", "HIGH_VALUE_THRESHOLD_EXCEEDED", "PROMPT_INJECTION_ATTEMPT_DETECTED"
- requires_verification: true/false
- confidence: float
- reasoning_summary: concise rationale
"""
