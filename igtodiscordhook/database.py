from datetime import datetime, timezone
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel, Session, select
from sqlalchemy.engine import Engine


class Post(SQLModel, table=True):
    __tablename__ = "ig_posts"

    id: Optional[int] = Field(default=None, primary_key=True)

    ig_account_id: int = Field(foreign_key="ig_accounts.id")
    ig_pk: int
    webhook_message_id: Optional[int] = None

    ig_account: "IGAccount" = Relationship(back_populates="ig_posts")


class IGAccount(SQLModel, table=True):
    __tablename__ = "ig_accounts"

    id: Optional[int] = Field(default=None, primary_key=True)

    ig_pk: int
    webhook_id: int
    min_time: datetime = Field(default_factory=datetime.utcnow)

    @property
    def aware_min_time(self) -> datetime:
        return self.min_time.replace(tzinfo=timezone.utc)

    @aware_min_time.setter
    def aware_min_time(self, value: datetime) -> None:
        assert value.tzinfo is not None
        delta = value.tzinfo.utcoffset(value)
        assert delta is not None
        self.min_time = value - delta

    ig_posts: List["Post"] = Relationship(back_populates="ig_account")

    @classmethod
    def get(cls, session: Session, pk: int | str, webhook_id: int):
        pk_i = int(pk)
        query = select(cls).where(cls.ig_pk == pk_i, cls.webhook_id == webhook_id)
        acc = session.exec(query).one_or_none()
        if acc is None:
            acc = cls(ig_pk=pk_i, webhook_id=webhook_id)
            session.add(acc)
        return acc

    def make_post(self, session: Session, pk: int | str) -> Post:
        pk_i = int(pk)
        # use ig_account_id=-1 to remove type errors (overwritten by ig_account=self)
        post = Post(ig_account_id=-1, ig_account=self, ig_pk=pk_i)
        session.add(post)
        return post


class DB:
    engine: Engine

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        SQLModel.metadata.create_all(engine)

    def session(self) -> Session:
        return Session(self.engine)

    def get_ig_account(
        self, session: Session, pk: int | str, webhook_id: int
    ) -> IGAccount:
        return IGAccount.get(session, pk=pk, webhook_id=webhook_id)

    def make_ig_post(self, session: Session, pk: int | str, account: IGAccount) -> Post:
        return account.make_post(session, pk)
