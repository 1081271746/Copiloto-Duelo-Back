from fastapi import APIRouter, Depends, Query, Request, Response

from app.core.dependencies import get_current_user, get_db
from app.models.entities import JournalEntry, SafetyAlert, utc_now
from app.repositories.base import UserRepository
from app.schemas.journal import AlertOutput, JournalCreate, JournalMutation, JournalOutput, JournalUpdate
from app.services.journal import JournalService
from app.services.safety import SafetyService


router = APIRouter(tags=["journal"])


def get_service(request: Request, db=Depends(get_db)):
    return JournalService(db, request.app.state.settings, request.app.state.events)


@router.post("/journal", response_model=JournalMutation, status_code=201)
async def create_entry(data: JournalCreate, user=Depends(get_current_user), service=Depends(get_service)):
    return await service.create(data, user)


@router.get("/journal", response_model=list[JournalOutput])
def list_entries(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                 user=Depends(get_current_user), db=Depends(get_db)):
    return UserRepository(db, JournalEntry).list(user.id, limit, offset)


@router.get("/journal/{entry_id}", response_model=JournalOutput)
def get_entry(entry_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    return UserRepository(db, JournalEntry).get(entry_id, user.id)


@router.patch("/journal/{entry_id}", response_model=JournalMutation)
async def update_entry(entry_id: str, data: JournalUpdate, user=Depends(get_current_user), service=Depends(get_service)):
    return await service.update(entry_id, data, user)


@router.delete("/journal/{entry_id}", status_code=204)
async def delete_entry(entry_id: str, user=Depends(get_current_user), service=Depends(get_service)):
    await service.delete(entry_id, user)
    return Response(status_code=204)


@router.get("/alerts", response_model=list[AlertOutput], tags=["safety"])
def list_alerts(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                user=Depends(get_current_user), db=Depends(get_db)):
    return UserRepository(db, SafetyAlert).list(user.id, limit, offset)


@router.get("/alerts/{alert_id}", response_model=AlertOutput, tags=["safety"])
def get_alert(alert_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    return UserRepository(db, SafetyAlert).get(alert_id, user.id)


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertOutput, tags=["safety"])
def acknowledge_alert(alert_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    alert = UserRepository(db, SafetyAlert).get(alert_id, user.id)
    alert.acknowledged_at = alert.acknowledged_at or utc_now()
    db.commit()
    return alert


@router.get("/safety/resources", tags=["safety"])
def safety_resources(request: Request, user=Depends(get_current_user)):
    return SafetyService(request.app.state.settings).guidance(user.country, "none")
