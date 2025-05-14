from backend.database import get_engine, get_session_local
from sqlalchemy.orm import Session

def get_db():
    engine = get_engine()
    SessionLocal = get_session_local(engine)
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close() 