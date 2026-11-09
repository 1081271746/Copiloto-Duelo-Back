from fastapi import APIRouter, Depends, Request, Response
from starlette.concurrency import run_in_threadpool

from app.core.dependencies import get_current_user, get_db
from app.models.entities import TokenSession
from app.schemas.auth import LoginInput, PasswordChange, ProfileUpdate, RegisterInput, TokenOutput, UserOutput
from app.security.tokens import create_token, hash_password, verify_password
from app.services.auth import AuthService


router = APIRouter(tags=["auth"])


@router.post("/auth/register", response_model=UserOutput, status_code=201)
async def register(data: RegisterInput, request: Request, db=Depends(get_db)):
    await request.app.state.events.rate_limit(f"register:{request.client.host}", 10, 60)
    return await run_in_threadpool(AuthService(db).register, data)


@router.post("/auth/login", response_model=TokenOutput)
async def login(data: LoginInput, request: Request, db=Depends(get_db)):
    settings = request.app.state.settings
    await request.app.state.events.rate_limit(f"login:{request.client.host}", 20, 60)
    user = await run_in_threadpool(AuthService(db).login, data)
    return TokenOutput(access_token=create_token(user, db, settings), expires_in=settings.token_minutes * 60)


@router.post("/auth/logout", status_code=204)
async def logout(request: Request, user=Depends(get_current_user), db=Depends(get_db)):
    session = db.get(TokenSession, request.state.token_claims["jti"])
    session.revoked = True
    db.commit()
    await request.app.state.events.publish(user.id, "auth.session_revoked", {"session_id": session.id})
    return Response(status_code=204)


@router.get("/users/me", response_model=UserOutput)
def profile(user=Depends(get_current_user)):
    return user


@router.patch("/users/me", response_model=UserOutput)
def update_profile(data: ProfileUpdate, user=Depends(get_current_user), db=Depends(get_db)):
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    db.commit()
    return user


@router.post("/users/me/password", status_code=204)
async def change_password(data: PasswordChange, request: Request, user=Depends(get_current_user), db=Depends(get_db)):
    from fastapi import HTTPException
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, "incorrect_password")
    user.password_hash = hash_password(data.new_password)
    user.token_version += 1
    db.commit()
    await request.app.state.events.publish(user.id, "auth.revoked", {})
    return Response(status_code=204)
