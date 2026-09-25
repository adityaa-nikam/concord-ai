from fastapi import APIRouter
from app.api import health, cases, transactions, agent, actions, audit, escalations, demo

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(cases.router)
api_router.include_router(transactions.router)
api_router.include_router(agent.router)
api_router.include_router(actions.router)
api_router.include_router(audit.router)
api_router.include_router(escalations.router)
api_router.include_router(demo.router)

