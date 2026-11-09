from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import HTTPException

from app.core.config import Settings
from app.models.entities import TokenSession, User


password_hasher = PasswordHasher()
dummy_hash = password_hasher.hash(str(uuid4()))


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return password_hasher.verify(hashed, password)
    except (VerificationError, InvalidHashError):
        return False


def create_token(user: User, db, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.token_minutes)
    session_id = str(uuid4())
    db.add(TokenSession(id=session_id, user_id=user.id, expires_at=expires))
    db.commit()
    return jwt.encode(
        {"sub": user.id, "jti": session_id, "ver": user.token_version,
         "iat": now, "exp": expires, "iss": settings.jwt_issuer, "aud": settings.jwt_audience},
        settings.jwt_secret, algorithm="HS256",
    )


def authenticate(token: str, db, settings: Settings) -> tuple[User, dict]:
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"],
                            issuer=settings.jwt_issuer, audience=settings.jwt_audience,
                            options={"require": ["exp", "iat", "sub", "jti", "ver", "iss", "aud"]})
        if not isinstance(claims["sub"], str) or not claims["sub"]:
            raise ValueError()
        if not isinstance(claims["jti"], str) or not claims["jti"]:
            raise ValueError()
        if type(claims["ver"]) is not int or claims["ver"] < 0:
            raise ValueError()
        user = db.get(User, claims["sub"])
        session = db.get(TokenSession, claims["jti"])
        if not user or not session or session.revoked or session.user_id != user.id:
            raise ValueError()
        if claims["ver"] != user.token_version:
            raise ValueError()
        return user, claims
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        raise HTTPException(401, "invalid_token", headers={"WWW-Authenticate": "Bearer"}) from None
