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
    from backend.models import ChoreORM, MealORM, FamilyMemberORM, RecipeORM
    import asyncio
    agent = HouseholdAssistantAgent()
    deps = AssistantDeps(db=db_session)

    async def run_agent(prompt):
        result = await agent.agent.run(prompt, deps=deps)
        print(f"Prompt: {prompt}\nResult: {result}\n")
        return result

    # Chore: create, list, update, delete
    async def chore_flow():
        # Add a family member named Alex first
        await run_agent("Add a family member named Alex, gender male.")
        mem = db_session.query(FamilyMemberORM).filter_by(name="Alex").first()
        assert mem is not None
        # Now create the chore assigned to Alex
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

    # Recipe: create, list, update, delete
    async def recipe_flow():
        await run_agent("Add a recipe called Mapo Tofu for dinner. Description: Spicy tofu with pork.")
        r = db_session.query(RecipeORM).filter_by(name="Mapo Tofu").first()
        assert r is not None
        await run_agent(f"Update recipe {r.id} to be called Mapo Tofu (Vegetarian) and description to Spicy tofu with mushrooms.")
        r2 = db_session.query(RecipeORM).filter_by(id=r.id).first()
        assert "Vegetarian" in r2.name
        assert "mushrooms" in (r2.description or "")
        await run_agent(f"Delete recipe {r.id}.")
        r3 = db_session.query(RecipeORM).filter_by(id=r.id).first()
        assert r3 is None

    asyncio.run(chore_flow())
    asyncio.run(meal_flow())
    asyncio.run(member_flow())
    asyncio.run(recipe_flow())

# API tests for /recipes endpoints

def test_recipe_api(db_session):
    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    # Create
    resp = client.post("/recipes", json={"name": "Kung Pao Chicken", "kind": "dinner", "description": "Spicy stir-fried chicken with peanuts."})
    assert resp.status_code == 200
    data = resp.json()
    recipe_id = data["id"]
    assert data["name"] == "Kung Pao Chicken"
    # List
    resp2 = client.get("/recipes")
    assert resp2.status_code == 200
    recipes = resp2.json()
    assert any(r["name"] == "Kung Pao Chicken" for r in recipes)
    # Get
    resp3 = client.get(f"/recipes/{recipe_id}")
    assert resp3.status_code == 200
    assert resp3.json()["name"] == "Kung Pao Chicken"
    # Update (not in API, so skip)
    # Delete
    resp4 = client.delete(f"/recipes/{recipe_id}")
    assert resp4.status_code == 200
    # Confirm deleted
    resp5 = client.get(f"/recipes/{recipe_id}")
    assert resp5.status_code == 404

def test_fuzzy_recipe_matching(db_session):
    from backend.main import app
    from fastapi.testclient import TestClient
    from backend.schemas import RecipeCreate
    from backend.crud import recipe as recipe_crud
    client = TestClient(app)
    # Seed recipes
    r1 = RecipeCreate(name="Spaghetti Bolognese", kind="dinner", description="Classic Italian pasta.")
    r2 = RecipeCreate(name="Chicken Curry", kind="dinner", description="Spicy and savory.")
    recipe_crud.create_recipe(db_session, r1)
    recipe_crud.create_recipe(db_session, r2)
    db_session.commit()
    # Test fuzzy match (should find Spaghetti Bolognese)
    resp = client.post("/meal/step", json={"current_data": {"meal_name": "spaghetti"}})
    data = resp.json()
    assert data["stage"] == "collecting_info"
    assert "suggested_recipes" in data
    assert any("Spaghetti Bolognese" in r["name"] for r in data["suggested_recipes"])
    # Test no match
    resp2 = client.post("/meal/step", json={"current_data": {"meal_name": "Unicorn Pie"}})
    data2 = resp2.json()
    assert data2["stage"] == "collecting_info"
    assert data2["suggested_recipes"] == [] 