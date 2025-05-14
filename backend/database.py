from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

def get_engine(db_url=None):
    if db_url is None:
        db_url = "sqlite:///./app.db"
    return create_engine(db_url, connect_args={"check_same_thread": False})

def get_session_local(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
