from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.domain import AgentRun, Case
from app.schemas.agent import AgentRunResponse, AgentRunTriggerRequest
from app.schemas.case import AgentRunSchema
from app.agents.runner import AgentRunner

router = APIRouter(prefix="/agent", tags=["Agent Operations"])


@router.post("/run/{case_id}", response_model=AgentRunSchema)
def trigger_agent_run(case_id: str, db: Session = Depends(get_db)):
    case = db.query(Case).filter(
        (Case.id == case_id) | (Case.case_number == case_id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    try:
        runner = AgentRunner(db)
        agent_run = runner.run_case_agent(case.id)
        return agent_run
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent run failed: {str(e)}")


@router.get("/runs", response_model=List[AgentRunSchema])
def list_agent_runs(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    from sqlalchemy import desc
    runs = db.query(AgentRun).order_by(desc(AgentRun.started_at)).offset(skip).limit(limit).all()
    return runs


@router.get("/runs/{run_id}", response_model=AgentRunSchema)
def get_agent_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Agent Run {run_id} not found")
    return run

