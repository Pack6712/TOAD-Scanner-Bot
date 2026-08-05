from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession
)

from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = "sqlite+aiosqlite:///scam.db"

engine = create_async_engine(
    DATABASE_URL,
    echo=False
)

Session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    pass 