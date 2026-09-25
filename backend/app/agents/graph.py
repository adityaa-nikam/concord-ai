from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session
from app.agents.state import CaseAgentState
from app.agents.nodes import (
    intake_node,
    understand_node,
    investigate_node,
    reconcile_node,
    ai_evidence_interpretation_node,
    policy_check_node,
    ai_resolution_proposal_node,
    decision_node,
    policy_gate_node,
    action_node,
    wait_node,
    verification_node,
    resolution_node,
    escalation_node
)


def route_decision(state: CaseAgentState) -> str:
    """Conditional routing based on decision node output."""
    d = state.get("decision")
    if d == "ACT":
        return "policy_gate"
    elif d == "WAIT":
        return "wait"
    elif d in ["RESOLVE", "RESOLVED", "NOTIFY_AND_CLOSE"]:
        return "resolution"
    else:
        return "escalation"


def route_policy_gate(state: CaseAgentState) -> str:
    """Conditional routing based on policy gate validation."""
    if state.get("policy_gate_passed", False):
        return "action"
    return "escalation"


def route_verification(state: CaseAgentState) -> str:
    """Conditional routing based on business outcome verification."""
    if state.get("verification_passed", False):
        return "resolution"
    return "escalation"


def build_tat_agent_graph(db: Session):
    """Builds and compiles the hybrid LangGraph state machine for CONCORD AI."""
    workflow = StateGraph(CaseAgentState)

    # Add nodes with closure wrapping DB session
    workflow.add_node("intake", lambda s: intake_node(s, db))
    workflow.add_node("understand", lambda s: understand_node(s, db))
    workflow.add_node("investigate", lambda s: investigate_node(s, db))
    workflow.add_node("reconcile", lambda s: reconcile_node(s, db))
    workflow.add_node("ai_evidence_interpretation", lambda s: ai_evidence_interpretation_node(s, db))
    workflow.add_node("policy_check", lambda s: policy_check_node(s, db))
    workflow.add_node("ai_resolution_proposal", lambda s: ai_resolution_proposal_node(s, db))
    workflow.add_node("decision", lambda s: decision_node(s, db))
    workflow.add_node("policy_gate", lambda s: policy_gate_node(s, db))
    workflow.add_node("action", lambda s: action_node(s, db))
    workflow.add_node("wait", lambda s: wait_node(s, db))
    workflow.add_node("verification", lambda s: verification_node(s, db))
    workflow.add_node("resolution", lambda s: resolution_node(s, db))
    workflow.add_node("escalation", lambda s: escalation_node(s, db))

    # Entry Point
    workflow.set_entry_point("intake")

    # Static edges
    workflow.add_edge("intake", "understand")
    workflow.add_edge("understand", "investigate")
    workflow.add_edge("investigate", "reconcile")
    workflow.add_edge("reconcile", "ai_evidence_interpretation")
    workflow.add_edge("ai_evidence_interpretation", "policy_check")
    workflow.add_edge("policy_check", "ai_resolution_proposal")
    workflow.add_edge("ai_resolution_proposal", "decision")

    # Conditional decision routing
    workflow.add_conditional_edges(
        "decision",
        route_decision,
        {
            "policy_gate": "policy_gate",
            "wait": "wait",
            "resolution": "resolution",
            "escalation": "escalation"
        }
    )

    # Conditional policy gate routing
    workflow.add_conditional_edges(
        "policy_gate",
        route_policy_gate,
        {
            "action": "action",
            "escalation": "escalation"
        }
    )

    # Edge from action to verification
    workflow.add_edge("action", "verification")

    # Conditional verification routing
    workflow.add_conditional_edges(
        "verification",
        route_verification,
        {
            "resolution": "resolution",
            "escalation": "escalation"
        }
    )

    # Terminal nodes
    workflow.add_edge("wait", END)
    workflow.add_edge("resolution", END)
    workflow.add_edge("escalation", END)

    return workflow.compile()
