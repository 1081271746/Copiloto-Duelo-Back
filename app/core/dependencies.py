from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.security.tokens import authenticate


bearer = HTTPBearer(auto_error=False)


def get_db(request: Request):
    with request.app.state.session_factory() as db:
        yield db


def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(bearer),
                     db=Depends(get_db)):
    from fastapi import HTTPException
    if credentials is None:
        raise HTTPException(401, "authentication_required", headers={"WWW-Authenticate": "Bearer"})
    user, claims = authenticate(credentials.credentials, db, request.app.state.settings)
    request.state.token_claims = claims
    return user
