from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.db.base import get_db
from app.demo.orchestrator import DemoOrchestrator

router = APIRouter(prefix="/demo", tags=["Demo Orchestrator"])


@router.get("/health", response_model=Dict[str, Any])
def demo_health_check(db: Session = Depends(get_db)):
    """Automated demo readiness health check endpoint for hackathon judges."""
    return DemoOrchestrator.get_demo_health(db)


@router.get("/scenarios", response_model=Dict[str, Any])
def list_demo_scenarios():
    """Lists pre-configured judge demo scenarios."""
    return {
        "count": len(DemoOrchestrator.DEMO_SCENARIOS),
        "scenarios": list(DemoOrchestrator.DEMO_SCENARIOS.values())
    }


@router.post("/reset", response_model=Dict[str, Any])
def reset_demo_environment(db: Session = Depends(get_db)):
    """Resets synthetic demo database back to clean baseline state."""
    return DemoOrchestrator.reset_demo_environment(db)


@router.post("/scenario/{scenario_id}/run", response_model=Dict[str, Any])
def run_demo_scenario(scenario_id: str, db: Session = Depends(get_db)):
    """Executes a judge demo scenario through the full autonomous Concord-AI workflow."""
    try:
        return DemoOrchestrator.run_demo_scenario(scenario_id, db)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing demo scenario: {str(e)}"
        )
