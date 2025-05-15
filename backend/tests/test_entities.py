from fastapi.testclient import TestClient
from backend.main import app
from datetime import date
import pytest

client = TestClient(app)

def test_create_and_list_member():
    """
    Test member creation and listing via API endpoints (not agent prompt).
    """
    member = {"name": "Alex", "gender": "male", "avatar": "http://example.com/alex.png"}
    r = client.post("/members", json=member)
    assert r.status_code == 200
    assert r.json()["name"] == "Alex"
    r = client.get("/members")
    assert r.status_code == 200
    assert any(m["name"] == "Alex" for m in r.json())

def test_create_and_list_chore():
    """
    Test chore creation, update, and deletion via API endpoints (not agent prompt).
    """
    chore = {
        "chore_name": "Laundry",
        "icon": "🧺",
        "assigned_members": ["Alex"],
        "start_date": str(date.today()),
        "due_time": "23:59",
        "repetition": "weekly",
        "reminder": None,
        "type": "individual"
    }
    r = client.post("/chores", json=chore)
    assert r.status_code == 200
    data = r.json()
    assert data["chore_name"] == "Laundry"
    chore_id = data["id"]
    # Get by ID
    r = client.get(f"/chores/{chore_id}")
    assert r.status_code == 200
    assert r.json()["chore_name"] == "Laundry"
    # Update
    update = chore.copy()
    update["chore_name"] = "Laundry Updated"
    r = client.put(f"/chores/{chore_id}", json=update)
    assert r.status_code == 200
    assert r.json()["chore_name"] == "Laundry Updated"
    # Delete
    r = client.delete(f"/chores/{chore_id}")
    assert r.status_code == 200
    assert r.json()["detail"] == "Chore deleted"
    # 404 after delete
    r = client.get(f"/chores/{chore_id}")
    assert r.status_code == 404

def test_create_and_list_meal():
    """
    Test meal creation, update, and deletion via API endpoints (not agent prompt).
    """
    meal = {
        "meal_name": "Pasta",
        "exist": True,
        "meal_kind": "dinner",
        "meal_date": str(date.today()),
        "dishes": ["Spaghetti", "Salad"]
    }
    r = client.post("/meals", json=meal)
    assert r.status_code == 200
    data = r.json()
    assert data["meal_name"] == "Pasta"
    meal_id = data["id"]
    # Get by ID
    r = client.get(f"/meals/{meal_id}")
    assert r.status_code == 200
    assert r.json()["meal_name"] == "Pasta"
    # Update
    update = meal.copy()
    update["meal_name"] = "Pasta Updated"
    r = client.put(f"/meals/{meal_id}", json=update)
    assert r.status_code == 200
    assert r.json()["meal_name"] == "Pasta Updated"
    # Delete
    r = client.delete(f"/meals/{meal_id}")
    assert r.status_code == 200
    assert r.json()["detail"] == "Meal deleted"
    # 404 after delete
    r = client.get(f"/meals/{meal_id}")
    assert r.status_code == 404

def test_chore_not_found():
    """
    Test 404 responses for missing chores (not agent prompt).
    """
    r = client.get("/chores/9999")
    assert r.status_code == 404
    r = client.put("/chores/9999", json={
        "chore_name": "X", "icon": None, "assigned_members": [], "start_date": str(date.today()), "due_time": "23:59", "repetition": "one-time", "reminder": None, "type": None
    })
    assert r.status_code == 404
    r = client.delete("/chores/9999")
    assert r.status_code == 404

def test_meal_not_found():
    """
    Test 404 responses for missing meals (not agent prompt).
    """
    r = client.get("/meals/9999")
    assert r.status_code == 404
    r = client.put("/meals/9999", json={
        "meal_name": "X", "exist": False, "meal_kind": "dinner", "meal_date": str(date.today()), "dishes": []
    })
    assert r.status_code == 404
    r = client.delete("/meals/9999")
    assert r.status_code == 404

def test_chore_step_flow():
    """
    Test the step-based chore creation flow via API endpoints (not agent prompt).
    """
    # Start with empty data
    r = client.post("/chore/step", json={"current_data": {}})
    assert r.status_code == 200
    assert r.json()["stage"] == "collecting_info"
    # Provide chore_name
    r = client.post("/chore/step", json={"current_data": {}, "user_input": {"chore_name": "Laundry"}})
    assert r.json()["stage"] == "collecting_info"
    # Provide assigned_members
    r = client.post("/chore/step", json={"current_data": {"chore_name": "Laundry"}, "user_input": {"assigned_members": ["Alex"]}})
    assert r.json()["stage"] == "collecting_info"
    # Provide start_date
    today = str(date.today())
    r = client.post("/chore/step", json={"current_data": {"chore_name": "Laundry", "assigned_members": ["Alex"]}, "user_input": {"start_date": today}})
    assert r.json()["stage"] == "collecting_info"
    # Provide repetition (all required fields now present)
    r = client.post("/chore/step", json={"current_data": {"chore_name": "Laundry", "assigned_members": ["Alex"], "start_date": today}, "user_input": {"repetition": "weekly"}})
    assert r.json()["stage"] == "confirming_info"
    # Confirm
    r = client.post("/chore/step", json={"current_data": {"chore_name": "Laundry", "assigned_members": ["Alex"], "start_date": today, "repetition": "weekly"}, "confirm": True})
    assert r.json()["stage"] == "created"
    assert "id" in r.json()

def test_meal_step_flow():
    """
    Test the step-based meal creation flow via API endpoints (not agent prompt).
    """
    # Start with empty data
    r = client.post("/meal/step", json={"current_data": {}})
    assert r.status_code == 200
    assert r.json()["stage"] == "collecting_info"
    # Provide meal_name
    r = client.post("/meal/step", json={"current_data": {}, "user_input": {"meal_name": "Pasta"}})
    assert r.json()["stage"] == "collecting_info"
    # Provide exist
    r = client.post("/meal/step", json={"current_data": {"meal_name": "Pasta"}, "user_input": {"exist": True}})
    assert r.json()["stage"] == "collecting_info"
    # Provide meal_kind
    r = client.post("/meal/step", json={"current_data": {"meal_name": "Pasta", "exist": True}, "user_input": {"meal_kind": "dinner"}})
    assert r.json()["stage"] == "collecting_info"
    # Provide meal_date (all required fields now present)
    today = str(date.today())
    r = client.post("/meal/step", json={"current_data": {"meal_name": "Pasta", "exist": True, "meal_kind": "dinner"}, "user_input": {"meal_date": today}})
    assert r.json()["stage"] == "confirming_info"
    # Confirm
    r = client.post("/meal/step", json={"current_data": {"meal_name": "Pasta", "exist": True, "meal_kind": "dinner", "meal_date": today}, "confirm": True})
    assert r.json()["stage"] == "created"
    assert "id" in r.json() 