from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select

from app.core.dependencies import get_current_user, get_db
from app.models.entities import EmotionalAnalysis, JournalEntry
from app.repositories.base import UserRepository
from app.schemas.analysis import AnalysisOutput, AnalysisResponse
from app.services.analysis import AnalysisService


router = APIRouter(tags=["analysis"])


@router.post("/journal/{entry_id}/analyze", response_model=AnalysisResponse, status_code=201)
async def analyze_entry(entry_id: str, request: Request, user=Depends(get_current_user), db=Depends(get_db)):
    return await AnalysisService(db, request.app.state.settings, request.app.state.events,
                                 request.app.state.analyzer).analyze(entry_id, user)


@router.get("/journal/{entry_id}/analyses", response_model=list[AnalysisOutput])
def entry_analyses(entry_id: str, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                   user=Depends(get_current_user), db=Depends(get_db)):
    UserRepository(db, JournalEntry).get(entry_id, user.id)
    return db.scalars(select(EmotionalAnalysis).where(
        EmotionalAnalysis.entry_id == entry_id, EmotionalAnalysis.user_id == user.id,
    ).order_by(EmotionalAnalysis.created_at.desc()).limit(limit).offset(offset)).all()


@router.get("/analyses", response_model=list[AnalysisOutput])
def list_analyses(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                  user=Depends(get_current_user), db=Depends(get_db)):
    return UserRepository(db, EmotionalAnalysis).list(user.id, limit, offset)


@router.get("/analyses/{analysis_id}", response_model=AnalysisOutput)
def get_analysis(analysis_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    return UserRepository(db, EmotionalAnalysis).get(analysis_id, user.id)
