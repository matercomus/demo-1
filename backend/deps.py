import os
from backend.database import get_engine, get_session_local
from sqlalchemy.orm import Session

def get_db():
    db_url = os.environ.get("TEST_DB_URL")
    engine = get_engine(db_url)
    SessionLocal = get_session_local(engine)
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close() 