import pytest
import tempfile
import os
from backend.database import get_engine, get_session_local, Base

@pytest.fixture(scope='session')
def test_db_url():
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tf:
        db_path = tf.name
    yield f"sqlite:///{db_path}"
    os.remove(db_path)

@pytest.fixture(scope='function')
def db_session(test_db_url):
    engine = get_engine(test_db_url)
    Base.metadata.create_all(bind=engine)
    SessionLocal = get_session_local(engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine) 