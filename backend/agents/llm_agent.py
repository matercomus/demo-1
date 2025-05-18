import os
from dataclasses import dataclass
from typing import Optional
from pydantic_ai import Agent
from pydantic_ai.tools import RunContext
from dotenv import load_dotenv
from backend.crud import chore as chore_crud, meal as meal_crud, member as member_crud, recipe as recipe_crud
from backend.schemas import ChoreCreate, MealCreate, FamilyMemberCreate, RecipeCreate
from backend.models import Chore, Meal, FamilyMember
import threading
import time
import logging
from backend.agents.prompt_watcher import watch_file_for_changes

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

PROMPT_PATH = os.path.join(os.path.dirname(__file__), '../../prompts/household_agent_system.md')

def load_system_prompt():
    try:
        with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        logging.warning("Failed to load system prompt from %s, using fallback prompt.", PROMPT_PATH, exc_info=True)
        # Fallback to the old prompt if file missing
        return (
            'You are a smart household assistant. Use the full conversation history to understand the user\'s intent and fill in missing information. '
            'If the user provides information over multiple messages, combine them to determine the user\'s request. '
            'You can manage chores, meals, family members, and recipes. '
            'You have access to the following tools and should use them directly whenever the user requests a change, including renaming or updating any field. '
            'For example, if the user says "rename chore 1 to Updated Chore", call update_chore(id=1, chore_name="Updated Chore").\n'
            'Tools:\n'
            '- create_chore(...): create a new chore.\n'
            '- list_chores(): list all chores.\n'
            '- update_chore(id, ...): update any field of a chore by ID, including the name. Example: update_chore(id=1, chore_name="Updated Chore").\n'
            '- delete_chore(id): delete a chore by ID.\n'
            '- create_meal(...): create a new meal.\n'
            '- list_meals(): list all meals.\n'
            '- update_meal(id, ...): update any field of a meal by ID.\n'
            '- delete_meal(id): delete a meal by ID.\n'
            '- create_member(...): add a family member.\n'
            '- list_members(): list all family members.\n'
            '- update_member(id, ...): update any field of a member by ID.\n'
            '- delete_member(id): delete a member by ID.\n'
            '- create_recipe(...): add a new recipe.\n'
            '- list_recipes(): list all recipes.\n'
            '- update_recipe(id, ...): update any field of a recipe by ID.\n'
            '- delete_recipe(id): delete a recipe by ID.\n'
            'Always use the appropriate tool for the user request, and extract all possible fields from the prompt.'
        )

@dataclass
class AssistantDeps:
    db: object  # SQLAlchemy session

class HouseholdAssistantAgent:
    def __init__(self):
        load_dotenv()
        self.system_prompt = load_system_prompt()
        self.agent = Agent[
            AssistantDeps, str
        ](
            os.getenv('OPENAI_MODEL', 'openai:gpt-4o'),
            deps_type=AssistantDeps,
            output_type=str,
            system_prompt=self.system_prompt,
        )
        self._register_tools()
        self._start_prompt_watcher()

    def reload_prompt(self):
        self.system_prompt = load_system_prompt()
        self.agent.system_prompt = self.system_prompt

    def _start_prompt_watcher(self):
        watch_file_for_changes(PROMPT_PATH, self.reload_prompt, logger_name="llm_agent.prompt_watcher")

    def _register_tools(self):
        @self.agent.tool
        async def create_chore(ctx: RunContext[AssistantDeps], chore_name: str = None, assigned_members: list = None, start_date: str = None, repetition: str = None, due_time: Optional[str] = None, reminder: Optional[str] = None, type: Optional[str] = None):
            db = ctx.deps.db
            # If any required info is missing, ask for it with collecting_info marker
            missing = []
            if not chore_name:
                missing.append("chore_name")
            if not assigned_members:
                missing.append("assigned_members")
            if not start_date:
                missing.append("start_date")
            if not repetition:
                missing.append("repetition")
            if missing:
                prompts = {
                    "chore_name": "📝 **Let's create a new chore!**\nWhat should we call this chore? (e.g., `Laundry`, `Take out trash`)",
                    "assigned_members": "👤 **Who should do this chore?**\nType one or more names (e.g., `Alex, Jamie`).",
                    "start_date": "📅 **When should this chore start?**\nFormat: YYYY-MM-DD (e.g., `2023-12-01`).",
                    "repetition": "🔁 **How often should this chore repeat?**\nChoose one: `daily`, `weekly`, `one-time`."
                }
                next_field = missing[0]
                # Show summary of collected so far
                summary = []
                if chore_name: summary.append(f"📝 Name: `{chore_name}`")
                if assigned_members: summary.append(f"👤 Assigned: {', '.join(str(m) for m in assigned_members)}")
                if start_date: summary.append(f"📅 Start: `{start_date}`")
                if repetition: summary.append(f"🔁 Repeats: `{repetition}`")
                summary_md = "\n".join(summary)
                return f"<!-- stage: collecting_info -->\n{prompts[next_field]}" + (f"\n\n**So far:**\n{summary_md}" if summary_md else "")
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
                return (
                    "<!-- stage: created -->\n"
                    "🎉 **Chore Created!**\n\n"
                    f"📝 **Name:** `{chore_name}`\n"
                    f"👤 **Assigned:** {', '.join(str(m) for m in assigned_members)}\n"
                    f"📅 **Start Date:** `{start_date}`\n"
                    f"🔁 **Repetition:** `{repetition}`\n"
                    f"⏰ **Due Time:** `{due_time or '23:59'}`\n"
                    f"🏷️ **Type:** `{type or ''}`\n"
                    f"🔔 **Reminder:** `{reminder or 'None'}`\n"
                    f"\nChore ID: `{db_chore.id}`"
                )
            except Exception as e:
                return f"**Error creating chore:** `{e}`"

        @self.agent.tool
        async def list_chores(ctx: RunContext[AssistantDeps]):
            db = ctx.deps.db
            chores = chore_crud.get_chores(db)
            if not chores:
                return "<!-- stage: confirming_info -->\nNo chores found."
            # Markdown table
            header = '| ID | Chore Name | Assigned Members | Repetition | Due Time | Type |\n|---|---|---|---|---|---|'
            rows = [
                f"| {c.id} | {c.chore_name} | {', '.join(str(m) for m in c.assigned_members)} | {c.repetition} | {c.due_time} | {c.type or ''} |"
                for c in chores
            ]
            return f"<!-- stage: confirming_info -->\n**Chores**\n\n{header}\n" + "\n".join(rows)

        @self.agent.tool
        async def update_chore(ctx: RunContext[AssistantDeps], id: int, **kwargs):
            """
            Update any field of a chore by ID, including the name. Example: update_chore(id=1, chore_name="Updated Chore").
            You can also update assigned_members, repetition, due_time, reminder, type, etc. Extract all possible fields from the user's request and call this tool directly.
            """
            db = ctx.deps.db
            c = chore_crud.get_chore(db, id)
            if not c:
                return f"<!-- stage: error -->\nChore with ID `{id}` not found. Please provide a valid chore ID."
            import re
            new_name = kwargs.get("chore_name")
            if not new_name:
                for k, v in kwargs.items():
                    if k in ["name", "new_name", "to", "called", "as"] and isinstance(v, str):
                        new_name = v
                        break
                if not new_name and hasattr(ctx, "input") and ctx.input:
                    m = re.search(r"(?:to be called|to have name|to|called|as) ['\"]?([\w\s-]+)['\"]?", ctx.input, re.IGNORECASE)
                    if m:
                        new_name = m.group(1).strip()
            # Merge old values with updates
            data = {k: kwargs[k] for k in kwargs if k in ChoreCreate.model_fields and kwargs[k] is not None}
            if new_name:
                data["chore_name"] = new_name
            merged = {**c.__dict__, **data}
            assigned = merged.get("assigned_members")
            if isinstance(assigned, str):
                assigned = assigned.split(",") if "," in assigned else [assigned]
            merged["assigned_members"] = data.get("assigned_members", assigned)
            merged.pop("_sa_instance_state", None)
            # If at least one field is being updated, apply the update immediately
            if data:
                chore = ChoreCreate(**merged)
                updated = chore_crud.update_chore(db, id, chore)
                return (
                    "<!-- stage: confirming_info -->\n"
                    f"✅ **Chore Updated!**\n\n"
                    f"📝 **Name:** `{chore.chore_name}`\n"
                    f"👤 **Assigned:** {', '.join(str(m) for m in chore.assigned_members)}\n"
                    f"🔁 **Repetition:** `{chore.repetition}`\n"
                    f"⏰ **Due Time:** `{chore.due_time}`\n"
                    f"🏷️ **Type:** `{chore.type or ''}`\n"
                    f"🔔 **Reminder:** `{chore.reminder or 'None'}`\n\n"
                    "Update complete!"
                )
            # Otherwise, ask for missing info
            return (
                "<!-- stage: collecting_info -->\n"
                "I need more information to update this chore. Please specify what you want to change.\n\n"
                f"Current values:\n- Name: `{c.chore_name}`\n- Assigned: {', '.join(str(m) for m in c.assigned_members)}\n- Repetition: `{c.repetition}`\n- Due Time: `{c.due_time}`\n- Type: `{c.type or ''}`\n- Reminder: `{c.reminder or 'None'}`"
            )

        @self.agent.tool
        async def delete_chore(ctx: RunContext[AssistantDeps], id: int, confirm: bool = False):
            db = ctx.deps.db
            if not confirm:
                return "<!-- stage: confirming_removal -->\nAre you sure you want to delete this chore? This action cannot be undone. Type 'Yes' to confirm."
            ok = chore_crud.delete_chore(db, id)
            return f"Chore {id} deleted." if ok else f"<!-- stage: error -->\nChore {id} not found."

        @self.agent.tool
        async def create_meal(ctx: RunContext[AssistantDeps], meal_name: str = None, exist: bool = None, meal_kind: str = None, meal_date: str = None, dishes: str = None):
            db = ctx.deps.db
            missing = []
            if not meal_name:
                missing.append("meal_name")
            if exist is None:
                # Try to infer from context
                if hasattr(ctx, "input") and ctx.input:
                    if any(word in ctx.input.lower() for word in ["new meal", "plan a meal", "create a meal", "add a meal"]):
                        exist = False
                if exist is None:
                    # If all other fields are present, default to False
                    if meal_name and meal_kind and meal_date:
                        exist = False
                if exist is None:
                    missing.append("exist")
            if not meal_kind:
                missing.append("meal_kind")
            if not meal_date:
                missing.append("meal_date")
            if not dishes:
                missing.append("dishes")
            if missing:
                prompts = {
                    "meal_name": "🍽️ **Let's plan a meal!**\nWhat would you like to call this meal? (e.g., `Pasta Night`)",
                    "exist": "📖 **Is this meal already in the recipe database?**\nType `true` or `false`. If you see your meal in the suggestions, select it. Otherwise, let me know if this is a new meal.",
                    "meal_kind": "🍳 **What kind of meal is this?**\nChoose one: `breakfast`, `lunch`, `dinner`, `snack`.",
                    "meal_date": "📅 **When do you want to have this meal?**\nFormat: YYYY-MM-DD (e.g., `2023-12-01`).",
                    "dishes": "🍲 **What dishes are included in this meal?**\nList one or more dishes (e.g., `Fish Soup, Salad`)."
                }
                next_field = missing[0]
                summary = f"\n**So far:**\n- Name: `{meal_name or '—'}`\n- Kind: `{meal_kind or '—'}`\n- Date: `{meal_date or '—'}`\n- Dishes: `{dishes or '—'}`"
                return f"<!-- stage: collecting_info -->\n{prompts[next_field]}{summary}"
            # All info present, create meal
            dishes_list = dishes
            if isinstance(dishes, str):
                # Split on commas, strip whitespace
                dishes_list = [d.strip() for d in dishes.split(",") if d.strip()]
            meal = MealCreate(
                meal_name=meal_name,
                exist=exist,
                meal_kind=meal_kind,
                meal_date=meal_date,
                dishes=dishes_list
            )
            m = meal_crud.create_meal(db, meal)
            return (
                "<!-- stage: created -->\n"
                f"🎉 **Meal Created!**\n\n"
                f"🍽️ **Name:** `{m.meal_name}`\n"
                f"🗓️ **Date:** `{m.meal_date}`\n"
                f"🍳 **Kind:** `{m.meal_kind}`\n"
                f"🍲 **Dishes:** `{', '.join(m.dishes) if m.dishes else '—'}`\n"
                f"📖 **Exists in DB:** `{m.exist}`\n"
                "Meal planning complete!"
            )

        @self.agent.tool
        async def list_meals(ctx: RunContext[AssistantDeps]):
            db = ctx.deps.db
            meals = meal_crud.get_meals(db)
            if not meals:
                return "<!-- stage: confirming_info -->\nNo meals found."
            header = '| ID | Meal Name | Kind | Date | Dishes |\n|---|---|---|---|---|'
            rows = [
                f"| {m.id} | {m.meal_name} | {m.meal_kind} | {m.meal_date} | {', '.join(m.dishes) if m.dishes else ''} |"
                for m in meals
            ]
            return f"<!-- stage: confirming_info -->\n**Meals**\n\n{header}\n" + "\n".join(rows)

        @self.agent.tool
        async def update_meal(ctx: RunContext[AssistantDeps], id: int, **kwargs):
            db = ctx.deps.db
            m = meal_crud.get_meal(db, id)
            if not m:
                return f"<!-- stage: error -->\nMeal with ID `{id}` not found. Please provide a valid meal ID."
            data = {k: kwargs[k] for k in kwargs if k in MealCreate.model_fields}
            if "dishes" in data and isinstance(data["dishes"], str):
                data["dishes"] = [data["dishes"]]
            meal = MealCreate(**{**m.__dict__, **data})
            updated = meal_crud.update_meal(db, id, meal)
            return (
                "<!-- stage: confirming_info -->\n"
                f"✅ **Meal Updated!**\n\n"
                f"🍽️ **Name:** `{m.meal_name}`\n"
                f"🍳 **Kind:** `{m.meal_kind}`\n"
                f"📅 **Date:** `{m.meal_date}`\n"
                f"🥗 **Dishes:** {', '.join(m.dishes or [])}\n\n"
                "If everything looks good, type **Done** to confirm or **Edit** to change anything."
            )

        @self.agent.tool
        async def delete_meal(ctx: RunContext[AssistantDeps], id: int, confirm: bool = False):
            db = ctx.deps.db
            if not confirm:
                return "<!-- stage: confirming_removal -->\nAre you sure you want to delete this meal? This action cannot be undone. Type 'Yes' to confirm."
            ok = meal_crud.delete_meal(db, id)
            return f"Meal {id} deleted." if ok else f"<!-- stage: error -->\nMeal {id} not found."

        @self.agent.tool
        async def create_member(ctx: RunContext[AssistantDeps], name: str = None, gender: Optional[str] = None, avatar: Optional[str] = None):
            db = ctx.deps.db
            if not name:
                return "<!-- stage: collecting_info -->\n👤 **Let's add a new family member!**\nWhat is their name? (e.g., `Jamie`)"
            member = FamilyMemberCreate(name=name, gender=gender, avatar=avatar)
            db_member = member_crud.create_member(db, member)
            return (
                "<!-- stage: created -->\n"
                "🎉 **Family Member Added!**\n\n"
                f"👤 **Name:** `{name}`\n"
                f"⚧️ **Gender:** `{gender or ''}`\n"
                f"🖼️ **Avatar:** `{avatar or ''}`\n"
                f"\nMember ID: `{db_member.id}`"
            )

        @self.agent.tool
        async def list_members(ctx: RunContext[AssistantDeps]):
            db = ctx.deps.db
            members = member_crud.get_members(db)
            if not members:
                return "<!-- stage: confirming_info -->\nNo family members found."
            header = '| ID | Name | Gender | Avatar |\n|---|---|---|---|'
            rows = [
                f"| {m.id} | {m.name} | {m.gender or ''} | {m.avatar or ''} |"
                for m in members
            ]
            return f"<!-- stage: confirming_info -->\n**Family Members**\n\n{header}\n" + "\n".join(rows)

        @self.agent.tool
        async def update_member(ctx: RunContext[AssistantDeps], id: int, **kwargs):
            db = ctx.deps.db
            m = member_crud.get_member(db, id)
            if not m:
                return f"<!-- stage: error -->\nMember with ID `{id}` not found. Please provide a valid member ID."
            data = {k: kwargs[k] for k in kwargs if k in FamilyMemberCreate.model_fields}
            member = FamilyMemberCreate(**{**m.__dict__, **data})
            updated = member_crud.update_member(db, id, member)
            return (
                "<!-- stage: confirming_info -->\n"
                f"✅ **Member Updated!**\n\n"
                f"👤 **Name:** `{member.name}`\n"
                f"⚧️ **Gender:** `{member.gender or ''}`\n"
                f"🖼️ **Avatar:** `{member.avatar or ''}`\n\n"
                "If everything looks good, type **Done** to confirm or **Edit** to change anything."
            )

        @self.agent.tool
        async def delete_member(ctx: RunContext[AssistantDeps], id: int, confirm: bool = False):
            db = ctx.deps.db
            if not confirm:
                return "<!-- stage: confirming_removal -->\nAre you sure you want to delete this member? This action cannot be undone. Type 'Yes' to confirm."
            ok = member_crud.delete_member(db, id)
            return f"Member {id} deleted." if ok else f"<!-- stage: error -->\nMember {id} not found."

        @self.agent.tool
        async def list_recipes(ctx: RunContext[AssistantDeps]):
            db = ctx.deps.db
            recipes = recipe_crud.get_recipes(db)
            if not recipes:
                return "<!-- stage: confirming_info -->\nNo recipes found."
            header = '| ID | Name | Kind | Description |\n|---|---|---|---|'
            rows = [
                f"| {r.id} | {r.name} | {r.kind} | {r.description or ''} |"
                for r in recipes
            ]
            return f"<!-- stage: confirming_info -->\n**Recipes**\n\n{header}\n" + "\n".join(rows)

        @self.agent.tool
        async def create_recipe(ctx: RunContext[AssistantDeps], name: str = None, kind: str = None, description: str = ""):
            db = ctx.deps.db
            if not name:
                return "<!-- stage: collecting_info -->\n🍲 **Let's add a new recipe!**\nWhat is the name of the recipe? (e.g., `Mapo Tofu`)"
            if not kind:
                return "<!-- stage: collecting_info -->\n🍲 **What kind of recipe is this?**\nChoose one: `breakfast`, `lunch`, `dinner`, `snack`."
            recipe = RecipeCreate(name=name, kind=kind, description=description)
            db_recipe = recipe_crud.create_recipe(db, recipe)
            return (
                "<!-- stage: created -->\n"
                "🎉 **Recipe Created!**\n\n"
                f"🍲 **Name:** `{name}`\n"
                f"🍳 **Kind:** `{kind}`\n"
                f"📝 **Description:** `{description}`\n"
                f"\nRecipe ID: `{db_recipe.id}`"
            )

        @self.agent.tool
        async def update_recipe(ctx: RunContext[AssistantDeps], id: int, **kwargs):
            db = ctx.deps.db
            r = recipe_crud.get_recipe(db, id)
            if not r:
                return f"<!-- stage: error -->\nRecipe with ID `{id}` not found. Please provide a valid recipe ID."
            data = {k: kwargs[k] for k in kwargs if k in RecipeCreate.model_fields}
            recipe = RecipeCreate(**{**r.__dict__, **data})
            updated = recipe_crud.update_recipe(db, id, recipe)
            return (
                "<!-- stage: confirming_info -->\n"
                f"✅ **Recipe Updated!**\n\n"
                f"🍲 **Name:** `{recipe.name}`\n"
                f"🍳 **Kind:** `{recipe.kind}`\n"
                f"📝 **Description:** `{recipe.description or ''}`\n\n"
                "If everything looks good, type **Done** to confirm or **Edit** to change anything."
            )

        @self.agent.tool
        async def delete_recipe(ctx: RunContext[AssistantDeps], id: int, confirm: bool = False):
            db = ctx.deps.db
            if not confirm:
                return "<!-- stage: confirming_removal -->\nAre you sure you want to delete this recipe? This action cannot be undone. Type 'Yes' to confirm."
            ok = recipe_crud.delete_recipe(db, id)
            return f"Recipe {id} deleted." if ok else f"<!-- stage: error -->\nRecipe {id} not found."