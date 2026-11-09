from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session


class UserRepository:
    def __init__(self, db: Session, model):
        self.db = db
        self.model = model

    def get(self, object_id: str, user_id: str):
        item = self.db.scalar(select(self.model).where(
            self.model.id == object_id, self.model.user_id == user_id,
        ))
        if item is None:
            raise HTTPException(404, "not_found")
        return item

    def list(self, user_id: str, limit: int = 50, offset: int = 0):
        return self.db.scalars(select(self.model).where(self.model.user_id == user_id)
                               .order_by(self.model.created_at.desc(), self.model.id)
                               .limit(limit).offset(offset)).all()
