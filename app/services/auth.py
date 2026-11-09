from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.entities import User
from app.security.tokens import dummy_hash, hash_password, password_hasher, verify_password


class AuthService:
    def __init__(self, db):
        self.db = db

    def register(self, data) -> User:
        user = User(email=str(data.email), name=data.name, country=data.country,
                    password_hash=hash_password(data.password))
        self.db.add(user)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(409, "email_already_registered") from None
        return user

    def login(self, data) -> User:
        user = self.db.scalar(select(User).where(User.email == str(data.email).lower()))
        valid = verify_password(data.password, user.password_hash if user else dummy_hash)
        if not user or not valid:
            raise HTTPException(401, "invalid_credentials")
        if password_hasher.check_needs_rehash(user.password_hash):
            user.password_hash = hash_password(data.password)
            self.db.commit()
        return user
