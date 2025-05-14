import os
from dataclasses import dataclass
from typing import Optional
from pydantic_ai import Agent
from pydantic_ai.tools import RunContext
from dotenv import load_dotenv
from backend.crud import chore as chore_crud, meal as meal_crud, member as member_crud
from backend.schemas import ChoreCreate, MealCreate, FamilyMemberCreate
from backend.models import Chore, Meal, FamilyMember

@dataclass
class AssistantDeps:
    db: object  # SQLAlchemy session

class HouseholdAssistantAgent:
    def __init__(self):
        load_dotenv()
        self.agent = Agent[
            AssistantDeps, str
        ](
            os.getenv('OPENAI_MODEL', 'openai:gpt-4o'),
            deps_type=AssistantDeps,
            output_type=str,
            system_prompt=(
                'You are a smart household assistant. You can help users manage chores, meals, and family members.\n'
                'You have the following tools:\n'
                '- create_chore(chore_name, assigned_members, start_date, repetition, due_time, reminder, type): create a new chore.\n'
                '- list_chores(): list all chores.\n'
                '- update_chore(id, ...): update a chore by ID.\n'
                '- delete_chore(id): delete a chore by ID.\n'
                '- create_meal(meal_name, exist, meal_kind, meal_date, dishes): create a new meal.\n'
                '- list_meals(): list all meals.\n'
                '- update_meal(id, ...): update a meal by ID.\n'
                '- delete_meal(id): delete a meal by ID.\n'
                '- create_member(name, gender, avatar): add a family member.\n'
                '- list_members(): list all family members.\n'
                '- update_member(id, ...): update a member by ID.\n'
                '- delete_member(id): delete a member by ID.\n'
                'Always use these tools to perform actions.\n'
                'Summarize actions for the user.\n'
                'If the user asks for help, explain what you can do.\n'
            ),
        )
        self._register_tools()

    def _register_tools(self):
        @self.agent.tool
        async def create_chore(ctx: RunContext[AssistantDeps], chore_name: str, assigned_members: list, start_date: str, repetition: str, due_time: Optional[str] = None, reminder: Optional[str] = None, type: Optional[str] = None):
            db = ctx.deps.db
            try:
                chore = ChoreCreate(
                    chore_name=chore_name,
                    assigned_members=assigned_members,
                    start_date=start_date,
                    repetition=repetition,
                    due_time=due_time or "23:59",
                    reminder=reminder,
                    type=type,
                    icon=None
                )
                db_chore = chore_crud.create_chore(db, chore)
                return f"Chore '{chore_name}' created with ID {db_chore.id}."
            except Exception as e:
                return f"Error creating chore: {e}"

        @self.agent.tool
        async def list_chores(ctx: RunContext[AssistantDeps]):
            db = ctx.deps.db
            chores = chore_crud.get_chores(db)
            if not chores:
                return "No chores found."
            return "Chores:\n" + "\n".join(f"[{c.id}] {c.chore_name} (assigned: {c.assigned_members})" for c in chores)

        @self.agent.tool
        async def update_chore(ctx: RunContext[AssistantDeps], id: int, **kwargs):
            db = ctx.deps.db
            c = chore_crud.get_chore(db, id)
            if not c:
                return f"Chore with ID {id} not found."
            data = {k: kwargs[k] for k in kwargs if k in ChoreCreate.__fields__}
            chore = ChoreCreate(**{**c.__dict__, **data})
            updated = chore_crud.update_chore(db, id, chore)
            return f"Chore {id} updated."

        @self.agent.tool
        async def delete_chore(ctx: RunContext[AssistantDeps], id: int):
            db = ctx.deps.db
            ok = chore_crud.delete_chore(db, id)
            return f"Chore {id} deleted." if ok else f"Chore {id} not found."

        @self.agent.tool
        async def create_meal(ctx: RunContext[AssistantDeps], meal_name: str, exist: bool, meal_kind: str, meal_date: str, dishes: Optional[list] = None):
            db = ctx.deps.db
            try:
                meal = MealCreate(
                    meal_name=meal_name,
                    exist=exist,
                    meal_kind=meal_kind,
                    meal_date=meal_date,
                    dishes=dishes or []
                )
                db_meal = meal_crud.create_meal(db, meal)
                return f"Meal '{meal_name}' created with ID {db_meal.id}."
            except Exception as e:
                return f"Error creating meal: {e}"

        @self.agent.tool
        async def list_meals(ctx: RunContext[AssistantDeps]):
            db = ctx.deps.db
            meals = meal_crud.get_meals(db)
            if not meals:
                return "No meals found."
            return "Meals:\n" + "\n".join(f"[{m.id}] {m.meal_name} ({m.meal_kind})" for m in meals)

        @self.agent.tool
        async def update_meal(ctx: RunContext[AssistantDeps], id: int, **kwargs):
            db = ctx.deps.db
            m = meal_crud.get_meal(db, id)
            if not m:
                return f"Meal with ID {id} not found."
            data = {k: kwargs[k] for k in kwargs if k in MealCreate.__fields__}
            meal = MealCreate(**{**m.__dict__, **data})
            updated = meal_crud.update_meal(db, id, meal)
            return f"Meal {id} updated."

        @self.agent.tool
        async def delete_meal(ctx: RunContext[AssistantDeps], id: int):
            db = ctx.deps.db
            ok = meal_crud.delete_meal(db, id)
            return f"Meal {id} deleted." if ok else f"Meal {id} not found."

        @self.agent.tool
        async def create_member(ctx: RunContext[AssistantDeps], name: str, gender: Optional[str] = None, avatar: Optional[str] = None):
            db = ctx.deps.db
            try:
                member = FamilyMemberCreate(name=name, gender=gender, avatar=avatar)
                db_member = member_crud.create_member(db, member)
                return f"Member '{name}' created with ID {db_member.id}."
            except Exception as e:
                return f"Error creating member: {e}"

        @self.agent.tool
        async def list_members(ctx: RunContext[AssistantDeps]):
            db = ctx.deps.db
            members = member_crud.get_members(db)
            if not members:
                return "No family members found."
            return "Members:\n" + "\n".join(f"[{m.id}] {m.name} ({m.gender})" for m in members)

        @self.agent.tool
        async def update_member(ctx: RunContext[AssistantDeps], id: int, **kwargs):
            db = ctx.deps.db
            m = member_crud.get_member(db, id)
            if not m:
                return f"Member with ID {id} not found."
            data = {k: kwargs[k] for k in kwargs if k in FamilyMemberCreate.__fields__}
            member = FamilyMemberCreate(**{**m.__dict__, **data})
            updated = member_crud.update_member(db, id, member)
            return f"Member {id} updated."

        @self.agent.tool
        async def delete_member(ctx: RunContext[AssistantDeps], id: int):
            db = ctx.deps.db
            ok = member_crud.delete_member(db, id)
            return f"Member {id} deleted." if ok else f"Member {id} not found."