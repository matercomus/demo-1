from fastapi.testclient import TestClient
from backend.main import app
from backend.deps import get_db
from backend.database import get_engine, get_session_local, Base
import pytest
from datetime import date
import tempfile
import os

@pytest.fixture(scope="module")
def test_db_engine():
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tf:
        db_path = tf.name
    engine = get_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    os.remove(db_path)

@pytest.fixture(scope="module")
def test_session_local(test_db_engine):
    return get_session_local(test_db_engine)

@pytest.fixture(autouse=True)
def override_get_db(test_session_local):
    def _override_get_db():
        db = test_session_local()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()

def test_chore_step_and_list():
    """
    Test the step-based chore creation and listing via API endpoints.
    This does not use the agent or prompt flows.
    """
    client = TestClient(app)
    # Create a chore via step flow
    today = str(date.today())
    # Step 1: name
    r = client.post("/chore/step", json={"current_data": {}, "user_input": {"chore_name": "Test Chore"}})
    # Step 2: assigned_members
    r = client.post("/chore/step", json={"current_data": {"chore_name": "Test Chore"}, "user_input": {"assigned_members": ["Alex"]}})
    # Step 3: start_date
    r = client.post("/chore/step", json={"current_data": {"chore_name": "Test Chore", "assigned_members": ["Alex"]}, "user_input": {"start_date": today}})
    # Step 4: repetition
    r = client.post("/chore/step", json={"current_data": {"chore_name": "Test Chore", "assigned_members": ["Alex"], "start_date": today}, "user_input": {"repetition": "daily"}})
    # Step 5: confirm
    r = client.post("/chore/step", json={"current_data": {"chore_name": "Test Chore", "assigned_members": ["Alex"], "start_date": today, "repetition": "daily"}, "confirm": True})
    assert r.status_code == 200
    assert r.json()["stage"] == "created"
    # List chores
    r = client.get("/chores")
    assert r.status_code == 200
    chores = r.json()
    assert any(c["chore_name"] == "Test Chore" for c in chores)

def test_meal_step_and_list():
    """
    Test the step-based meal creation and listing via API endpoints.
    This does not use the agent or prompt flows.
    """
    client = TestClient(app)
    today = str(date.today())
    # Step 1: meal_name
    r = client.post("/meal/step", json={"current_data": {}, "user_input": {"meal_name": "Test Meal"}})
    # Step 2: exist
    r = client.post("/meal/step", json={"current_data": {"meal_name": "Test Meal"}, "user_input": {"exist": True}})
    # Step 3: meal_kind
    r = client.post("/meal/step", json={"current_data": {"meal_name": "Test Meal", "exist": True}, "user_input": {"meal_kind": "lunch"}})
    # Step 4: meal_date
    r = client.post("/meal/step", json={"current_data": {"meal_name": "Test Meal", "exist": True, "meal_kind": "lunch"}, "user_input": {"meal_date": today}})
    # Step 5: confirm
    r = client.post("/meal/step", json={"current_data": {"meal_name": "Test Meal", "exist": True, "meal_kind": "lunch", "meal_date": today}, "confirm": True})
    assert r.status_code == 200
    assert r.json()["stage"] == "created"
    # List meals
    r = client.get("/meals")
    assert r.status_code == 200
    meals = r.json()
    assert any(m["meal_name"] == "Test Meal" for m in meals) 