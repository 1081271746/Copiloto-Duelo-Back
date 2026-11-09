from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user, get_db
from app.services.tracking import TrackingService


router = APIRouter(tags=["tracking"])


@router.get("/tracking/summary")
def summary(days: int = Query(30, ge=1, le=365), user=Depends(get_current_user), db=Depends(get_db)):
    return TrackingService(db).summary(user.id, days)


@router.get("/tracking/trends")
def trends(days: int = Query(30, ge=1, le=365), user=Depends(get_current_user), db=Depends(get_db)):
    return TrackingService(db).trends(user.id, days)


@router.get("/tracking/timeline")
def timeline(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
             user=Depends(get_current_user), db=Depends(get_db)):
    return TrackingService(db).timeline(user.id, limit, offset)
