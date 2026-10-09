from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.audit_event import AuditEvent
from app.schemas.approval import AuditEventResponse

router = APIRouter(prefix="/audit-events", tags=["Audit Events"])


@router.get("", response_model=List[AuditEventResponse])
async def list_audit_events(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(AuditEvent)
        .where(AuditEvent.user_id == user.id)
        .order_by(desc(AuditEvent.created_at))
        .limit(100)
    )
    res = await db.execute(stmt)
    return res.scalars().all()
