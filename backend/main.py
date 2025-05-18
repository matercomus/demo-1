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

# Initialize the household assistant agent
household_agent = HouseholdAssistantAgent()

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
        print('Chore step error:', e)
        traceback.print_exc()
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
        print('Meal step error:', e)
        traceback.print_exc()
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
    from backend.main import household_agent, openai_to_model_messages
    import re
    import logging
    message = data.get("message", "")
    raw_message_history = data.get("message_history", [])
    message_history = openai_to_model_messages(raw_message_history)
    deps = AssistantDeps(db=db)
    logger = logging.getLogger("chat_endpoint")
    def normalize_marker(reply):
        marker_match = re.search(r"<!-- stage: (\w+) -->", reply)
        if marker_match:
            marker = marker_match.group(0)
            reply_wo_marker = re.sub(r"<!-- stage: (\w+) -->", "", reply).strip()
            return f"{marker}\n{reply_wo_marker}"
        return reply
    try:
        agent = household_agent.agent
        if hasattr(agent, "run") and callable(getattr(agent, "run")):
            result = await agent.run(message, deps=deps, message_history=message_history)
        else:
            result = agent.run_sync(message, deps=deps, message_history=message_history)
        reply = result.output if hasattr(result, 'output') else str(result)
        reply = normalize_marker(reply)
        if not re.match(r"^<!-- stage: (\w+) -->", reply):
            if hasattr(agent, "run") and callable(getattr(agent, "run")):
                result2 = await agent.run(message, deps=deps, message_history=message_history)
            else:
                result2 = agent.run_sync(message, deps=deps, message_history=message_history)
            reply2 = result2.output if hasattr(result2, 'output') else str(result2)
            reply2 = normalize_marker(reply2)
            if re.match(r"^<!-- stage: (\w+) -->", reply2):
                reply = reply2
            else:
                reply = "<!-- stage: error -->\n**Assistant error:** No stage marker in reply. Please try again or contact support."
        return JSONResponse({"reply": reply, "message_history": raw_message_history})
    except Exception as e:
        logger.exception("Error in /chat/ endpoint")
        return JSONResponse({"reply": "<!-- stage: error -->\n**Assistant error:** Internal server error: {}".format(str(e)), "message_history": raw_message_history}, status_code=200)
