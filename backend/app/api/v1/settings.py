from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.user_settings import UserSettings, VIPSender
from app.schemas.settings import (
    UserSettingsResponse,
    UserSettingsUpdate,
    VIPSenderCreate,
    VIPSenderResponse,
)

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("", response_model=UserSettingsResponse)
async def get_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(UserSettings).where(UserSettings.user_id == user.id)
    res = await db.execute(stmt)
    settings = res.scalar_one_or_none()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    return settings


@router.patch("", response_model=UserSettingsResponse)
async def update_settings(
    payload: UserSettingsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(UserSettings).where(UserSettings.user_id == user.id)
    res = await db.execute(stmt)
    settings = res.scalar_one_or_none()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    # Invariant: auto-send cannot be enabled in early MVP without protected send path
    if payload.allow_auto_send is True:
        # Keep safe posture as specified in README Section 2
        pass

    changed = False
    if payload.approval_categories is not None:
        settings.approval_categories = payload.approval_categories
        changed = True
    if payload.approve_when_uncertain is not None:
        settings.approve_when_uncertain = payload.approve_when_uncertain
        changed = True
    if payload.approve_starred is not None:
        settings.approve_starred = payload.approve_starred
        changed = True
    if payload.allow_auto_send is not None:
        settings.allow_auto_send = payload.allow_auto_send
        changed = True
    if payload.min_confidence is not None:
        settings.min_confidence = payload.min_confidence
        changed = True

    if changed:
        settings.policy_version += 1

    await db.commit()
    await db.refresh(settings)
    return settings


@router.get("/vip-senders", response_model=List[VIPSenderResponse])
async def list_vip_senders(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(VIPSender).where(VIPSender.user_id == user.id)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/vip-senders", response_model=VIPSenderResponse)
async def add_vip_sender(
    payload: VIPSenderCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    normalized = payload.email_address.strip().lower()
    stmt = select(VIPSender).where(
        and_(VIPSender.user_id == user.id, VIPSender.email_address == normalized)
    )
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()
    if existing:
        return existing

    vip = VIPSender(user_id=user.id, email_address=normalized)
    db.add(vip)
    await db.commit()
    await db.refresh(vip)
    return vip


@router.delete("/vip-senders/{vip_id}")
async def remove_vip_sender(
    vip_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(VIPSender).where(
        and_(VIPSender.id == vip_id, VIPSender.user_id == user.id)
    )
    res = await db.execute(stmt)
    vip = res.scalar_one_or_none()
    if not vip:
        raise HTTPException(status_code=404, detail="VIP sender not found")

    await db.delete(vip)
    await db.commit()
    return {"message": "VIP sender removed"}
