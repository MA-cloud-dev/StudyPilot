from fastapi import APIRouter

from app.api.routes import assessments, knowledge, learning, plans, profile, workflow

api_router = APIRouter()
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(plans.router, prefix="/plans", tags=["plans"])
api_router.include_router(learning.router, prefix="/learning/session", tags=["learning-session"])
api_router.include_router(assessments.router, prefix="/assessments", tags=["assessments"])
api_router.include_router(workflow.router, prefix="/workflow", tags=["workflow"])
