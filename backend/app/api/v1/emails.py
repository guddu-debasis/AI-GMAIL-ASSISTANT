from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.email import Email
from app.schemas.email import EmailListItem, EmailDetailResponse

router = APIRouter(prefix="/emails", tags=["Emails"])


@router.get("", response_model=List[EmailListItem])
async def list_emails(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Email)
        .options(selectinload(Email.classification), selectinload(Email.reply_draft))
        .where(Email.user_id == user.id)
        .order_by(desc(Email.created_at))
    )
    res = await db.execute(stmt)
    emails = res.scalars().all()

    # In-memory filter for demo simplicity or SQL filter
    filtered = []
    for em in emails:
        if category and (not em.classification or em.classification.category != category):
            continue
        if status and (not em.reply_draft or em.reply_draft.status != status):
            continue
        filtered.append(em)

    return filtered


@router.get("/{email_id}", response_model=EmailDetailResponse)
async def get_email_detail(
    email_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Email)
        .options(selectinload(Email.classification), selectinload(Email.reply_draft))
        .where(and_(Email.id == email_id, Email.user_id == user.id))
    )
    res = await db.execute(stmt)
    email = res.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email
