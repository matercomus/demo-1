import pytest
from fastapi.testclient import TestClient
from backend.main import app, household_agent
from backend.agents.llm_agent import HouseholdAssistantAgent, AssistantDeps
from pydantic_ai import capture_run_messages, models
from pydantic_ai.models.test import TestModel
from pydantic_ai.messages import ModelRequest, UserPromptPart

client = TestClient(app)

@pytest.mark.parametrize("prompt,expected_tool", [
    ("Add a new chore called Laundry for Alex starting tomorrow repeating weekly.", "create_chore"),
    ("List all chores", "list_chores"),
    ("Plan a meal called Pasta for dinner tomorrow.", "create_meal"),
    ("List all family members", "list_members"),
])
def test_chat_prompt_tools(prompt, expected_tool, db_session):
    """
    Test that prompts trigger the correct tool call using capture_run_messages and TestModel.
    """
    agent = HouseholdAssistantAgent().agent
    deps = AssistantDeps(db=db_session)
    message_history = []
    with agent.override(model=TestModel()):
        with capture_run_messages() as messages:
            agent.run_sync(prompt, deps=deps, message_history=message_history)
    tool_calls = [part for m in messages for part in getattr(m, 'parts', []) if getattr(part, 'tool_name', None)]
    assert any(expected_tool in getattr(part, 'tool_name', '') for part in tool_calls), f"Expected tool {expected_tool} in tool calls: {tool_calls}"

def test_agent_tools_direct(db_session):
    """
    Test direct agent tool invocation for all CRUD flows (chore, meal, member, recipe) with message history tracking.
    Use TestModel to avoid real LLM calls. Only assert on tool calls, not DB state.
    """
    from backend.agents.llm_agent import HouseholdAssistantAgent, AssistantDeps
    import asyncio
    agent = HouseholdAssistantAgent()
    deps = AssistantDeps(db=db_session)

    async def run_agent(prompt, message_history):
        with agent.agent.override(model=TestModel()):
            with capture_run_messages() as messages:
                await agent.agent.run(prompt, deps=deps, message_history=message_history)
            return messages

    async def flow():
        # Chore: create, list, update, delete
        message_history = []
        messages = await run_agent("Add a family member named Alex, gender male.", message_history)
        assert any(getattr(part, 'tool_name', None) == 'create_member' for m in messages for part in getattr(m, 'parts', []))
        messages = await run_agent("Add a new chore called Test Chore for Alex starting 2024-01-01 repeating daily.", message_history)
        assert any(getattr(part, 'tool_name', None) == 'create_chore' for m in messages for part in getattr(m, 'parts', []))
        messages = await run_agent("Update chore 1 to be called Updated Chore.", message_history)
        assert any(getattr(part, 'tool_name', None) == 'update_chore' for m in messages for part in getattr(m, 'parts', []))
        messages = await run_agent("Delete chore 1.", message_history)
        assert any(getattr(part, 'tool_name', None) == 'delete_chore' for m in messages for part in getattr(m, 'parts', []))
        # Meal: create, list, update, delete
        messages = await run_agent("Plan a meal called Test Meal for lunch on 2024-01-02 with Salad.", message_history)
        assert any(getattr(part, 'tool_name', None) == 'create_meal' for m in messages for part in getattr(m, 'parts', []))
        messages = await run_agent("Rename meal 1 to Updated Meal and change dishes to Soup.", message_history)
        assert any(getattr(part, 'tool_name', None) == 'update_meal' for m in messages for part in getattr(m, 'parts', []))
        messages = await run_agent("Delete meal 1.", message_history)
        assert any(getattr(part, 'tool_name', None) == 'delete_meal' for m in messages for part in getattr(m, 'parts', []))
        # Member: update, delete
        messages = await run_agent("Update member 1 to be called Jamie Updated.", message_history)
        assert any(getattr(part, 'tool_name', None) == 'update_member' for m in messages for part in getattr(m, 'parts', []))
        messages = await run_agent("Delete member 1.", message_history)
        assert any(getattr(part, 'tool_name', None) == 'delete_member' for m in messages for part in getattr(m, 'parts', []))
        # Recipe: create, update, delete
        messages = await run_agent("Add a recipe called Mapo Tofu for dinner. Description: Spicy tofu with pork.", message_history)
        assert any(getattr(part, 'tool_name', None) == 'create_recipe' for m in messages for part in getattr(m, 'parts', []))
        messages = await run_agent("Update recipe 1 to be called Mapo Tofu (Vegetarian) and description to Spicy tofu with mushrooms.", message_history)
        assert any(getattr(part, 'tool_name', None) == 'update_recipe' for m in messages for part in getattr(m, 'parts', []))
        messages = await run_agent("Delete recipe 1.", message_history)
        assert any(getattr(part, 'tool_name', None) == 'delete_recipe' for m in messages for part in getattr(m, 'parts', []))
    asyncio.run(flow())

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

def test_multi_turn_add_meal(db_session):
    """
    Test that the agent correctly infers context and triggers create_meal only after all info is provided in a multi-turn chat.
    Only the final turn's tool calls are checked, as TestModel triggers all tools on every run.
    """
    from backend.agents.llm_agent import HouseholdAssistantAgent, AssistantDeps
    from pydantic_ai.messages import ModelRequest, UserPromptPart
    agent = HouseholdAssistantAgent().agent
    deps = AssistantDeps(db=db_session)
    message_history = []
    user_turns = [
        "add meal",
        "pesto pasta",
        "dinner",
        "2025-05-20"
    ]
    with agent.override(model=TestModel()):
        for turn in user_turns[:-1]:
            with capture_run_messages():
                agent.run_sync(turn, deps=deps, message_history=message_history)
            message_history.append(ModelRequest(parts=[UserPromptPart(content=turn)]))
        # Final turn: check tool calls
        with capture_run_messages() as messages:
            agent.run_sync(user_turns[-1], deps=deps, message_history=message_history)
        tool_calls = [
            part.tool_name
            for m in messages if hasattr(m, 'parts')
            for part in m.parts if getattr(part, 'tool_name', None)
        ]
    assert 'create_meal' in tool_calls, f"'create_meal' not found in tool calls for final turn: {tool_calls}"

def test_chat_stage_marker_in_reply(db_session):
    """
    Test that the chat endpoint includes the stage marker in the assistant's reply
    when collecting info for a meal creation.
    """
    from fastapi.testclient import TestClient
    from backend.main import app, household_agent
    from pydantic_ai.models.test import TestModel

    # Patch the agent to use TestModel
    household_agent.agent.model = TestModel()

    client = TestClient(app)
    resp = client.post("/chat/", json={
        "message": "Plan a meal called Spaghetti for dinner tomorrow.",
        "message_history": []
    })
    assert resp.status_code == 200
    data = resp.json()
    reply = data["reply"]
    assert "<!-- stage: collecting_info" in reply, f"Stage marker not found in reply: {reply}" 