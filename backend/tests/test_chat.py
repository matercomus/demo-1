import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

@pytest.mark.parametrize("prompt,expected", [
    ("Add a new chore called Laundry for Alex starting tomorrow repeating weekly.", "chore"),
    ("List all chores", "Chores"),
    ("Plan a meal called Pasta for dinner tomorrow.", "meal"),
    ("List all family members", "Members"),
])
def test_chat_basic(prompt, expected):
    response = client.post("/chat/", json={"message": prompt})
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    # Just check the expected keyword is in the reply (case-insensitive)
    assert expected.lower() in data["reply"].lower() 