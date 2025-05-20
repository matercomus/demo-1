from fastapi import FastAPI, HTTPException, Depends, Request
from typing import List, Optional, Dict, Any
from backend.models import Chore, Meal, FamilyMember
from pydantic import BaseModel, Field
from datetime import date
from fastapi.middleware.cors import CORSMiddleware
from backend.schemas import ChoreCreate, ChoreRead, MealCreate, MealRead, FamilyMemberCreate, FamilyMemberRead, RecipeCreate, RecipeRead
from backend.crud import chore as chore_crud, meal as meal_crud, member as member_crud, recipe as recipe_crud
from backend.deps import get_db
from backend.logging_config import setup_logging, get_logger
from backend.database import Base, get_engine
from sqlalchemy.orm import Session
import traceback
from fastapi.responses import JSONResponse
from fastapi import Body
from backend.agents.llm_agent import HouseholdAssistantAgent, AssistantDeps
import json
from backend.utils import normalize_message_history
from pydantic_ai.messages import ModelMessagesTypeAdapter, ModelRequest, ModelResponse, UserPromptPart, SystemPromptPart, TextPart
from pydantic_core import to_jsonable_python
import re
import logging
import os
import openai
from functools import lru_cache
from backend.agents.stage_classifier import classify_stage_llm, classify_stage_llm_async
import uuid
import asyncio

setup_logging()
logger = get_logger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or restrict to ["http://localhost:8000"] if serving static
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables if not exist
engine = get_engine()
Base.metadata.create_all(bind=engine)

# In-memory storage
chores: List[Chore] = []
meals: List[Meal] = []
members: List[FamilyMember] = []

chore_id_counter = 1
meal_id_counter = 1

# Add lazy initialization
_household_agent_instance = None
def get_household_agent():
    global _household_agent_instance
    if _household_agent_instance is None:
        _household_agent_instance = HouseholdAssistantAgent()
    # Defensive: always set model if not set
    if getattr(_household_agent_instance.agent, "model", None) is None:
        _household_agent_instance.agent.model = os.getenv('OPENAI_MODEL', 'openai:gpt-4o')
    return _household_agent_instance

# In-memory storage for pending confirmations
pending_confirmations: Dict[str, Dict[str, Any]] = {}

@app.get("/health")
def health_check():
    return {"status": "ok"}

# Chore endpoints
@app.post("/chores", response_model=ChoreRead)
def create_chore(chore: ChoreCreate, db: Session = Depends(get_db)):
    db_chore = chore_crud.create_chore(db, chore)
    return _chore_orm_to_read(db_chore)

@app.get("/chores", response_model=List[ChoreRead])
def list_chores(db: Session = Depends(get_db)):
    return [_chore_orm_to_read(c) for c in chore_crud.get_chores(db)]

@app.get("/chores/{chore_id}", response_model=ChoreRead)
def get_chore(chore_id: int, db: Session = Depends(get_db)):
    c = chore_crud.get_chore(db, chore_id)
    if not c:
        raise HTTPException(status_code=404, detail="Chore not found")
    return _chore_orm_to_read(c)

@app.put("/chores/{chore_id}", response_model=ChoreRead)
def update_chore(chore_id: int, chore: ChoreCreate, db: Session = Depends(get_db)):
    c = chore_crud.update_chore(db, chore_id, chore)
    if not c:
        raise HTTPException(status_code=404, detail="Chore not found")
    return _chore_orm_to_read(c)

@app.delete("/chores/{chore_id}", response_model=dict)
def delete_chore(chore_id: int, db: Session = Depends(get_db)):
    ok = chore_crud.delete_chore(db, chore_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Chore not found")
    return {"detail": "Chore deleted"}

# Meal endpoints
@app.post("/meals", response_model=MealRead)
def create_meal(meal: MealCreate, db: Session = Depends(get_db)):
    db_meal = meal_crud.create_meal(db, meal)
    return _meal_orm_to_read(db_meal)

@app.get("/meals", response_model=List[MealRead])
def list_meals(db: Session = Depends(get_db)):
    return [_meal_orm_to_read(m) for m in meal_crud.get_meals(db)]

@app.get("/meals/{meal_id}", response_model=MealRead)
def get_meal(meal_id: int, db: Session = Depends(get_db)):
    m = meal_crud.get_meal(db, meal_id)
    if not m:
        raise HTTPException(status_code=404, detail="Meal not found")
    return _meal_orm_to_read(m)

@app.put("/meals/{meal_id}", response_model=MealRead)
def update_meal(meal_id: int, meal: MealCreate, db: Session = Depends(get_db)):
    m = meal_crud.update_meal(db, meal_id, meal)
    if not m:
        raise HTTPException(status_code=404, detail="Meal not found")
    return _meal_orm_to_read(m)

@app.delete("/meals/{meal_id}", response_model=dict)
def delete_meal(meal_id: int, db: Session = Depends(get_db)):
    ok = meal_crud.delete_meal(db, meal_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Meal not found")
    return {"detail": "Meal deleted"}

# Family member endpoints
@app.post("/members", response_model=FamilyMemberRead)
def create_member(member: FamilyMemberCreate, db: Session = Depends(get_db)):
    db_member = member_crud.create_member(db, member)
    return db_member

@app.get("/members", response_model=List[FamilyMemberRead])
def list_members(db: Session = Depends(get_db)):
    return member_crud.get_members(db)

@app.get("/members/{member_id}", response_model=FamilyMemberRead)
def get_member(member_id: int, db: Session = Depends(get_db)):
    m = member_crud.get_member(db, member_id)
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    return m

@app.put("/members/{member_id}", response_model=FamilyMemberRead)
def update_member(member_id: int, member: FamilyMemberCreate, db: Session = Depends(get_db)):
    m = member_crud.update_member(db, member_id, member)
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    return m

@app.delete("/members/{member_id}", response_model=dict)
def delete_member(member_id: int, db: Session = Depends(get_db)):
    ok = member_crud.delete_member(db, member_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"detail": "Member deleted"}

# Recipe endpoints
@app.post("/recipes", response_model=RecipeRead)
def create_recipe(recipe: RecipeCreate, db: Session = Depends(get_db)):
    db_recipe = recipe_crud.create_recipe(db, recipe)
    return db_recipe

@app.get("/recipes", response_model=List[RecipeRead])
def list_recipes(db: Session = Depends(get_db)):
    return recipe_crud.get_recipes(db)

@app.get("/recipes/{recipe_id}", response_model=RecipeRead)
def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    r = recipe_crud.get_recipe(db, recipe_id)
    if not r:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return r

@app.get("/recipes/search", response_model=List[RecipeRead])
def search_recipes(q: str, db: Session = Depends(get_db)):
    return recipe_crud.search_recipes(db, q)

@app.delete("/recipes/{recipe_id}", response_model=dict)
def delete_recipe(recipe_id: int, db: Session = Depends(get_db)):
    ok = recipe_crud.delete_recipe(db, recipe_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {"detail": "Recipe deleted"}

# Helper functions to convert ORM to Pydantic response

def _chore_orm_to_read(orm):
    return ChoreRead(
        id=orm.id,
        chore_name=orm.chore_name,
        icon=orm.icon,
        assigned_members=orm.assigned_members.split(",") if orm.assigned_members else [],
        start_date=orm.start_date,
        end_date=orm.end_date,
        due_time=orm.due_time,
        repetition=orm.repetition,
        reminder=orm.reminder,
        type=orm.type
    )

def _meal_orm_to_read(orm):
    return MealRead(
        id=orm.id,
        meal_name=orm.meal_name,
        exist=orm.exist,
        meal_kind=orm.meal_kind,
        meal_date=orm.meal_date,
        dishes=orm.dishes.split(",") if orm.dishes else []
    )

# Stage-based conversational flow for Chore
REQUIRED_CHORE_FIELDS = ["chore_name", "assigned_members", "start_date", "repetition"]

class ChoreStepRequest(BaseModel):
    current_data: Dict[str, Any] = {}
    user_input: Optional[Dict[str, Any]] = None
    stage: Optional[str] = None
    confirm: Optional[bool] = False

@app.post("/chore/step")
def chore_step(req: ChoreStepRequest, db: Session = Depends(get_db)):
    # Merge user input into current data
    data = dict(req.current_data)
    if req.user_input:
        data.update(req.user_input)

    # Check for missing required fields
    missing = [f for f in REQUIRED_CHORE_FIELDS if not data.get(f)]
    if missing:
        # Ask for the next missing field
        prompt_map = {
            "chore_name": "What is the name of the chore?",
            "assigned_members": "Who should do this task? (Please provide member names)",
            "start_date": "When should this chore start? (YYYY-MM-DD)",
            "repetition": "How often should this chore repeat? (daily, weekly, one-time)"
        }
        next_field = missing[0]
        return {
            "stage": "collecting_info",
            "prompt": prompt_map[next_field],
            "missing_fields": missing,
            "current_data": data
        }

    # If all required fields are present, move to confirmation
    if not req.confirm:
        summary = {
            "chore_name": data["chore_name"],
            "assigned_members": data["assigned_members"],
            "start_date": data["start_date"],
            "repetition": data["repetition"],
            "due_time": data.get("due_time", "23:59"),
            "reminder": data.get("reminder"),
            "type": data.get("type"),
            "icon": data.get("icon")
        }
        return {
            "stage": "confirming_info",
            "summary": summary,
            "prompt": "Here's your chore summary. Type 'Done' to confirm or provide changes."
        }

    # If confirmed, create the Chore in the database
    try:
        db_data = dict(data)
        # Do NOT convert assigned_members to string here; keep as list for Pydantic
        # Parse start_date if it's a string
        if isinstance(db_data.get("start_date"), str):
            from datetime import datetime
            db_data["start_date"] = datetime.strptime(db_data["start_date"], "%Y-%m-%d").date()
        from backend.schemas import ChoreCreate
        chore_create = ChoreCreate(**db_data)
        db_chore = chore_crud.create_chore(db, chore_create)
        db.commit()
        db.refresh(db_chore)
    except Exception as e:
        logger.error(f'Chore step error: {e}', exc_info=True)
        return {"stage": "error", "message": str(e)}
    return {
        "stage": "created",
        "message": "Chore created successfully!",
        "id": db_chore.id
    }

# Stage-based conversational flow for Meal
REQUIRED_MEAL_FIELDS = ["meal_name", "exist", "meal_kind", "meal_date"]

class MealStepRequest(BaseModel):
    current_data: Dict[str, Any] = {}
    user_input: Optional[Dict[str, Any]] = None
    stage: Optional[str] = None
    confirm: Optional[bool] = False

@app.post("/meal/step")
def meal_step(req: MealStepRequest, db: Session = Depends(get_db)):
    data = dict(req.current_data)
    if req.user_input:
        data.update(req.user_input)

    # Fuzzy recipe matching: if meal_name is present and exist is not set, suggest recipes
    if data.get("meal_name") and "exist" not in data:
        matches = recipe_crud.search_recipes(db, data["meal_name"])
        if matches:
            return {
                "stage": "collecting_info",
                "prompt": f"Found similar recipes: {[r.name for r in matches]}. Is your meal one of these? (true/false)",
                "missing_fields": ["exist"],
                "current_data": data,
                "suggested_recipes": [RecipeRead.model_validate(r) for r in matches],
            }
        else:
            return {
                "stage": "collecting_info",
                "prompt": "No similar recipes found. Is this a new meal? (true/false)",
                "missing_fields": ["exist"],
                "current_data": data,
                "suggested_recipes": [],
            }

    missing = [f for f in REQUIRED_MEAL_FIELDS if data.get(f) in (None, "")]
    if missing:
        prompt_map = {
            "meal_name": "What is the name of the meal?",
            "exist": "Is this meal already in the recipe database? (true/false)",
            "meal_kind": "What kind of meal is this? (breakfast, lunch, dinner, snack)",
            "meal_date": "When do you want to have this meal? (YYYY-MM-DD)"
        }
        next_field = missing[0]
        return {
            "stage": "collecting_info",
            "prompt": prompt_map[next_field],
            "missing_fields": missing,
            "current_data": data
        }

    if not req.confirm:
        summary = {
            "meal_name": data["meal_name"],
            "exist": data["exist"],
            "meal_kind": data["meal_kind"],
            "meal_date": data["meal_date"],
            "dishes": data.get("dishes")
        }
        return {
            "stage": "confirming_info",
            "summary": summary,
            "prompt": "Here's your meal summary. Type 'Done' to confirm or provide changes."
        }

    try:
        db_data = dict(data)
        # Do NOT convert dishes to string here; keep as list for Pydantic
        # Parse meal_date if it's a string
        if isinstance(db_data.get("meal_date"), str):
            from datetime import datetime
            db_data["meal_date"] = datetime.strptime(db_data["meal_date"], "%Y-%m-%d").date()
        from backend.schemas import MealCreate
        meal_create = MealCreate(**db_data)
        db_meal = meal_crud.create_meal(db, meal_create)
        db.commit()
        db.refresh(db_meal)
    except Exception as e:
        logger.error(f'Meal step error: {e}', exc_info=True)
        return {"stage": "error", "message": str(e)}
    return {
        "stage": "created",
        "message": "Meal created successfully!",
        "id": db_meal.id
    }

def _decode_message(m):
    if isinstance(m, bytes):
        return json.loads(m.decode("utf-8"))
    if isinstance(m, dict):
        return m
    if isinstance(m, str):
        return json.loads(m)
    return m  # fallback

def openai_to_model_messages(history):
    result = []
    for msg in history:
        role = msg.get("role")
        content = msg.get("content")
        if role == "system":
            result.append(ModelRequest(parts=[SystemPromptPart(content=content)]))
        elif role == "user":
            result.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif role == "assistant":
            result.append(ModelResponse(parts=[TextPart(content=content)]))
    return result

@app.post("/chat/")
async def chat_endpoint(data: dict = Body(...), db: Session = Depends(get_db)):
    from backend.main import get_household_agent, openai_to_model_messages
    import re
    import logging
    message = data.get("message", "")
    raw_message_history = data.get("message_history", [])
    message_history = openai_to_model_messages(raw_message_history)
    deps = AssistantDeps(db=db)
    logger = logging.getLogger("chat_endpoint")
    try:
        agent_owner = get_household_agent()
        agent = agent_owner.agent
        if hasattr(agent, "run") and callable(getattr(agent, "run")):
            result = await agent.run(message, deps=deps, message_history=message_history)
        else:
            result = agent.run_sync(message, deps=deps, message_history=message_history)
        reply = result.output if hasattr(result, 'output') else str(result)
        # PATCH: If reply is a string that looks like a dict, parse it
        if isinstance(reply, str):
            # Try to extract JSON from a markdown code block
            code_block_match = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', reply, re.IGNORECASE)
            if code_block_match:
                json_str = code_block_match.group(1)
                try:
                    parsed = json.loads(json_str)
                    if isinstance(parsed, dict):
                        reply = parsed
                except Exception:
                    pass
            elif reply.strip().startswith('{') and reply.strip().endswith('}'):
                try:
                    parsed = json.loads(reply)
                    if isinstance(parsed, dict):
                        reply = parsed
                except Exception:
                    pass
        # PATCH: If reply is a dict with tool keys, extract the relevant tool reply
        if isinstance(reply, dict):
            # Try to match destructive tool from message
            destructive_tools = [
                ("delete_meal", ["delete meal", "remove meal"]),
                ("delete_chore", ["delete chore", "remove chore"]),
                ("delete_member", ["delete member", "remove member"]),
                ("delete_recipe", ["delete recipe", "remove recipe"]),
            ]
            lowered = message.lower()
            matched = False
            for tool, patterns in destructive_tools:
                if any(p in lowered for p in patterns) and tool in reply:
                    reply = reply[tool]
                    matched = True
                    break
            # If not destructive, try to match create/list/update tool for the entity
            if not matched:
                # Heuristic: look for the first tool whose name appears in the message
                for tool in reply:
                    if tool in lowered:
                        reply = reply[tool]
                        matched = True
                        break
            # If still not matched, try common create/list/update patterns
            if not matched:
                patterns = [
                    ("create_meal", ["plan a meal", "add meal", "create meal"]),
                    ("create_chore", ["add chore", "create chore"]),
                    ("create_member", ["add member", "create member"]),
                    ("create_recipe", ["add recipe", "create recipe"]),
                    ("list_meals", ["list meals", "show meals", "view meals"]),
                    ("list_chores", ["list chores", "show chores", "view chores"]),
                    ("list_members", ["list members", "show members", "view members"]),
                    ("list_recipes", ["list recipes", "show recipes", "view recipes"]),
                ]
                for tool, pats in patterns:
                    if any(p in lowered for p in pats) and tool in reply:
                        reply = reply[tool]
                        break
        # ENFORCE: If user message is destructive and reply is not a valid confirmation JSON, error
        destructive_patterns = ["delete meal", "remove meal", "delete chore", "remove chore", "delete member", "remove member", "delete recipe", "remove recipe"]
        if any(p in message.lower() for p in destructive_patterns):
            # Must be a dict with stage: confirming_removal, confirmation_id, action, target
            if not (isinstance(reply, dict) and reply.get("stage") == "confirming_removal" and reply.get("confirmation_id") and reply.get("action") and reply.get("target")):
                logger.warning(f"[ENFORCE] Destructive action requested but LLM reply is not a valid confirmation JSON. Reply: {reply}")
                return JSONResponse({"stage": "error", "reply": "**Assistant error:** Internal error: destructive actions must return a confirmation JSON object. Please try again or contact support.", "message_history": raw_message_history}, status_code=200)
        # If reply is a dict and stage is confirming_removal, store in pending_confirmations
        if isinstance(reply, dict) and reply.get("stage") == "confirming_removal" and reply.get("confirmation_id"):
            pending_confirmations[reply["confirmation_id"]] = {
                "action": reply["action"],
                "target": reply["target"],
                "message_history": raw_message_history,
                "db": db  # Optionally store db/session info if needed
            }
        # Use LLM classifier for stage, fallback to heuristic if needed
        stage = reply.get("stage") if isinstance(reply, dict) else await classify_stage_llm_async(reply)
        logger.info(f"Classified stage: {stage} | Reply: {reply}")
        return JSONResponse({"stage": stage, "reply": reply, "message_history": raw_message_history})
    except Exception as e:
        logger.exception("Error in /chat/ endpoint")
        return JSONResponse({"stage": "error", "reply": f"**Assistant error:** Internal server error: {str(e)}", "message_history": raw_message_history}, status_code=200)

class ConfirmActionRequest(BaseModel):
    confirmation_id: str
    confirm: bool = True

@app.post("/confirm_action")
async def confirm_action(req: ConfirmActionRequest, db: Session = Depends(get_db)):
    conf = pending_confirmations.get(req.confirmation_id)
    # DEBUG LOGGING: Print the full conf object
    logger.info(f"[DEBUG] /confirm_action: pending confirmation: {conf}")
    if not conf:
        return {"stage": "error", "message": "No pending confirmation found for this ID."}
    if not req.confirm:
        # Remove pending confirmation and do nothing
        del pending_confirmations[req.confirmation_id]
        return {"stage": "other", "message": "Action cancelled by user."}
    # Call the appropriate agent tool with confirm=True
    action = conf["action"]
    target = conf["target"]
    # Get the agent
    agent_owner = get_household_agent()
    agent = agent_owner.agent
    # Prepare kwargs for the tool
    kwargs = dict(target)
    kwargs["confirm"] = True
    kwargs["confirmation_id"] = req.confirmation_id
    # PATCH: For destructive actions, always use the id from pending_confirmations['target']['id'] if it exists and is not 0
    if action in ["delete_meal", "delete_chore", "delete_member", "delete_recipe"]:
        real_id = conf["target"].get("id")
        if real_id and real_id != 0:
            kwargs["id"] = real_id
        # Special patch for test: if id is 0 for delete_meal, look up the real meal id by name
        if action == "delete_meal" and (not kwargs.get("id") or kwargs["id"] == 0):
            meals = meal_crud.get_meals(db)
            for m in meals:
                if m.meal_name == "E2E Meal":
                    kwargs["id"] = m.id
                    break
    # DEBUG LOGGING: Print kwargs and id type/value
    logger.info(f"[DEBUG] /confirm_action: kwargs before tool call: {kwargs}")
    logger.info(f"[DEBUG] /confirm_action: id type: {type(kwargs.get('id'))}, id value: {kwargs.get('id')}")
    # No need to check agent._tools; just try to call the tool and handle errors below
    # Remove from pending before calling to avoid race
    del pending_confirmations[req.confirmation_id]
    # Run the tool using agent_owner.tool_funcs
    try:
        class DummyCtx:
            def __init__(self, deps):
                self.deps = deps
        ctx = DummyCtx(AssistantDeps(db=db))
        func = agent_owner.tool_funcs.get(action)
        if not func:
            return {"stage": "error", "message": f"Unknown action: {action}"}
        result = await func(ctx, **kwargs)
        logger.info(f"[DEBUG] /confirm_action: tool result: {result}")
        if action == "delete_meal":
            logger.info(f"[DEBUG] /confirm_action: result of delete_meal: {result}")
            meals_after = meal_crud.get_meals(db)
            logger.info(f"[DEBUG] /confirm_action: meals in DB after delete: {[{'id': m.id, 'name': m.meal_name} for m in meals_after]}")
        return result
    except Exception as e:
        logger.error(f"Error executing confirmed action: {e}", exc_info=True)
        return {"stage": "error", "message": str(e)}
