from fastapi import APIRouter
from app.api.v1.gmail import router as gmail_router
from app.api.v1.emails import router as emails_router
from app.api.v1.approvals import router as approvals_router
from app.api.v1.drafts import router as drafts_router
from app.api.v1.settings import router as settings_router
from app.api.v1.audit_events import router as audit_events_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(gmail_router)
api_v1_router.include_router(emails_router)
api_v1_router.include_router(approvals_router)
api_v1_router.include_router(drafts_router)
api_v1_router.include_router(settings_router)
api_v1_router.include_router(audit_events_router)
