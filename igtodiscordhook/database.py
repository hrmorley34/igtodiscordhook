from datetime import datetime, timezone
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel, Session, select

# import sqlmodel
from sqlalchemy.engine import Engine


class Post(SQLModel, table=True):
    __tablename__ = "ig_posts"

    ig_account_pk: int = Field(foreign_key="ig_accounts.ig_pk")
    ig_pk: int = Field(primary_key=True)
    webhook_message_id: Optional[int] = None

    ig_account: "IGAccount" = Relationship(back_populates="ig_posts")


class IGAccount(SQLModel, table=True):
    __tablename__ = "ig_accounts"

    ig_pk: int = Field(primary_key=True)
    min_time: datetime = Field(default_factory=datetime.utcnow)

    @property
    def aware_min_time(self) -> datetime:
        return self.min_time.replace(tzinfo=timezone.utc)

    ig_posts: List["Post"] = Relationship(back_populates="ig_account")


class DB:
    engine: Engine

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        SQLModel.metadata.create_all(engine)

    def session(self) -> Session:
        return Session(self.engine)

    def get_ig_account(self, session: Session, pk: int) -> IGAccount:
        query = select(IGAccount).where(IGAccount.ig_pk == pk)
        acc = session.exec(query).one_or_none()
        if acc is None:
            acc = IGAccount(ig_pk=pk)
            session.add(acc)
        return acc

    def make_ig_post(self, session: Session, pk: int, account_pk: int):
        account = self.get_ig_account(session, pk=account_pk)
        post = Post(ig_account_pk=account.ig_pk, ig_pk=pk)
        session.add(post)
        return post
