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

def test_agent_tools_direct(db_session):
    from backend.agents.llm_agent import HouseholdAssistantAgent, AssistantDeps
    from backend.models import ChoreORM, MealORM, FamilyMemberORM
    import asyncio
    agent = HouseholdAssistantAgent()
    deps = AssistantDeps(db=db_session)

    async def run_agent(prompt):
        return await agent.agent.run(prompt, deps=deps)

    # Chore: create, list, update, delete
    async def chore_flow():
        await run_agent("Add a new chore called Test Chore for Alex starting 2024-01-01 repeating daily.")
        c = db_session.query(ChoreORM).filter_by(chore_name="Test Chore").first()
        assert c is not None
        await run_agent(f"Update chore {c.id} to be called Updated Chore.")
        c2 = db_session.query(ChoreORM).filter_by(id=c.id).first()
        assert c2.chore_name == "Updated Chore"
        await run_agent(f"Delete chore {c.id}.")
        c3 = db_session.query(ChoreORM).filter_by(id=c.id).first()
        assert c3 is None

    # Meal: create, list, update, delete
    async def meal_flow():
        await run_agent("Plan a meal called Test Meal for lunch on 2024-01-02 with Salad.")
        m = db_session.query(MealORM).filter_by(meal_name="Test Meal").first()
        assert m is not None
        await run_agent(f"Rename meal {m.id} to Updated Meal and change dishes to Soup.")
        m2 = db_session.query(MealORM).filter_by(id=m.id).first()
        assert "Soup" in (m2.dishes or "")
        await run_agent(f"Delete meal {m.id}.")
        m3 = db_session.query(MealORM).filter_by(id=m.id).first()
        assert m3 is None

    # Member: create, list, update, delete
    async def member_flow():
        await run_agent("Add a family member named Jamie, gender other.")
        mem = db_session.query(FamilyMemberORM).filter_by(name="Jamie").first()
        assert mem is not None
        await run_agent(f"Update member {mem.id} to be called Jamie Updated.")
        mem2 = db_session.query(FamilyMemberORM).filter_by(id=mem.id).first()
        assert mem2.name == "Jamie Updated"
        await run_agent(f"Delete member {mem.id}.")
        mem3 = db_session.query(FamilyMemberORM).filter_by(id=mem.id).first()
        assert mem3 is None

    asyncio.run(chore_flow())
    asyncio.run(meal_flow())
    asyncio.run(member_flow()) 