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

@pytest.fixture(scope='session', autouse=True)
def set_test_db_env(test_db_url):
    os.environ['TEST_DB_URL'] = test_db_url
    # Create all tables in the temp DB before any tests run
    engine = get_engine(test_db_url)
    Base.metadata.create_all(bind=engine)
    yield
    os.environ.pop('TEST_DB_URL', None) 