from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import or_, select

from app.core.dependencies import get_current_user, get_db
from app.models.entities import Exercise, ExerciseCompletion, Resource
from app.schemas.analysis import GriefCategory
from app.schemas.library import CompletionInput, CompletionOutput, ExerciseOutput, ResourceOutput
from app.services.library import LibraryService


router = APIRouter(tags=["library"])


@router.get("/exercises", response_model=list[ExerciseOutput])
def exercises(category: GriefCategory | None = None, limit: int = Query(50, ge=1, le=100),
              offset: int = Query(0, ge=0), user=Depends(get_current_user), db=Depends(get_db)):
    query = select(Exercise)
    if category:
        query = query.where(Exercise.category == category.value)
    return db.scalars(query.order_by(Exercise.title).limit(limit).offset(offset)).all()


@router.get("/exercises/{exercise_id}", response_model=ExerciseOutput)
def exercise_detail(exercise_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    exercise = db.get(Exercise, exercise_id)
    if exercise is None:
        raise HTTPException(404, "not_found")
    return exercise


@router.get("/resources", response_model=list[ResourceOutput])
def resources(category: str | None = Query(None, max_length=40), limit: int = Query(50, ge=1, le=100),
              offset: int = Query(0, ge=0), user=Depends(get_current_user), db=Depends(get_db)):
    query = select(Resource).where(or_(Resource.country == user.country, Resource.country.is_(None)))
    if category:
        query = query.where(Resource.category == category)
    return db.scalars(query.order_by(Resource.title).limit(limit).offset(offset)).all()


@router.get("/recommendations")
def recommendations(request: Request, user=Depends(get_current_user), db=Depends(get_db)):
    return LibraryService(db, request.app.state.settings).recommendations(user)


@router.post("/exercises/{exercise_id}/complete", response_model=CompletionOutput, status_code=201)
async def complete(exercise_id: str, data: CompletionInput, request: Request,
                   user=Depends(get_current_user), db=Depends(get_db)):
    item = LibraryService(db, request.app.state.settings).complete(exercise_id, data, user)
    await request.app.state.events.publish(user.id, "tracking.updated", {"completion_id": item.id})
    return item


@router.get("/exercise-history", response_model=list[CompletionOutput])
def exercise_history(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                      user=Depends(get_current_user), db=Depends(get_db)):
    return db.scalars(select(ExerciseCompletion).where(ExerciseCompletion.user_id == user.id)
                       .order_by(ExerciseCompletion.completed_at.desc()).limit(limit).offset(offset)).all()
