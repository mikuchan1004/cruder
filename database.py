from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, create_engine,text

from config import DATABASE_URL


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)
def get_session():
    with Session(engine) as session:
        yield session
        session.commit()


# 연결 확인 잘 되었는지 확인용
if __name__ == "__main__":
    with engine.connect() as conn:
        result = conn.execute(text("SELECT DATABASE()"))
        print("연결 성공:", result.scalar())