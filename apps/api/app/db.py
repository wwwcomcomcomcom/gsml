from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from . import models  # noqa: F401  ensure models are imported before create_all

    Base.metadata.create_all(bind=engine)

    # 기존 DB에 source 컬럼이 없을 경우 자동으로 추가
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE request_logs ADD COLUMN source VARCHAR"))
            conn.commit()
        except Exception:
            pass  # 이미 존재하면 무시


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
