import os
from dataclasses import dataclass
from typing import Optional, Union
from pydantic_ai import Agent, Tool
from pydantic_ai.tools import RunContext
from dotenv import load_dotenv
from backend.crud import chore as chore_crud, meal as meal_crud, member as member_crud, recipe as recipe_crud
from backend.schemas import ChoreCreate, MealCreate, FamilyMemberCreate, RecipeCreate
from backend.models import Chore, Meal, FamilyMember
import threading
import time
import logging
from backend.agents.prompt_watcher import watch_file_for_changes
import uuid
from pydantic import BaseModel
from pydantic_ai import ModelRetry
from enum import Enum

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

class StageEnum(str, Enum):
    collecting_info = "collecting_info"
    confirming_info = "confirming_info"
    created = "created"
    error = "error"
    greeting = "greeting"
    confirming_removal = "confirming_removal"

class ConfirmationOutput(BaseModel):
    stage: StageEnum
    confirmation_id: str
    action: str
    target: dict
    message: str

    @classmethod
    def validate_strict(cls, value):
        obj = cls.model_validate(value)
        if obj.stage != StageEnum.confirming_removal:
            raise ValueError("stage must be 'confirming_removal'")
        if not obj.confirmation_id or not isinstance(obj.confirmation_id, str):
            raise ValueError("confirmation_id must be a non-empty string")
        if not obj.action or not isinstance(obj.action, str):
            raise ValueError("action must be a non-empty string")
        if not obj.target or not isinstance(obj.target, dict) or "id" not in obj.target:
            raise ValueError("target must be a dict with an 'id' field")
        if not obj.message or not isinstance(obj.message, str):
            raise ValueError("message must be a non-empty string")
        return obj

class InfoOutput(BaseModel):
    stage: StageEnum
    message: str

    @classmethod
    def validate_strict(cls, value):
        obj = cls.model_validate(value)
        if obj.stage not in {
            StageEnum.collecting_info,
            StageEnum.confirming_info,
            StageEnum.created,
            StageEnum.error,
            StageEnum.greeting,
        }:
            raise ValueError(f"stage must be one of info stages, got {obj.stage}")
        if not obj.message or not isinstance(obj.message, str):
            raise ValueError("message must be a non-empty string")
        return obj

def agent_output_validator(output, ctx):
    # Initialize error history on the retry context if not present
    if hasattr(ctx, "retry"):
        if not hasattr(ctx.retry, "errors"):
            ctx.retry.errors = []
    else:
        ctx.retry = type("Retry", (), {"errors": []})()

    # For destructive confirmation, require target to be a dict with an 'id' key
    if isinstance(output, dict) and output.get("stage") == "confirming_removal":
        target = output.get("target")
        if not isinstance(target, dict) or "id" not in target:
            error_msg = (
                "The 'target' field must be an object with an 'id' field, e.g., {'id': 1}. If multiple items match, ask the user to specify a single ID before confirming deletion. Only confirm one item at a time."
            )
            ctx.retry.errors.append(error_msg)
            history_text = "\n".join(f"Attempt {i+1}: {msg}" for i, msg in enumerate(ctx.retry.errors))
            raise ModelRetry(
                f"Previous failed attempts:\n{history_text}\n\nCurrent error: {error_msg}\nPlease correct the output."
            )
    # Handle the case where the user replies with a number after being prompted for an ID
    if ctx and hasattr(ctx, "message_history") and ctx.message_history:
        last_assistant = None
        for m in reversed(ctx.message_history):
            if hasattr(m, "parts"):
                for part in m.parts:
                    if hasattr(part, "content") and isinstance(part.content, str) and "confirming_removal" in part.content:
                        last_assistant = part.content
                        break
            if last_assistant:
                break
        if last_assistant and ctx.message and ctx.message.strip().isdigit():
            id_val = int(ctx.message.strip())
            return {
                "stage": "confirming_removal",
                "confirmation_id": str(uuid.uuid4()),
                "action": "delete_chore",  # Default to delete_chore; you may want to infer action from context
                "target": {"id": id_val},
                "message": f"Are you sure you want to delete item {id_val}? This action cannot be undone."
            }
    # Try strict confirmation output
    try:
        return ConfirmationOutput.validate_strict(output)
    except Exception as e:
        if hasattr(ctx, "retry"):
            ctx.retry.errors.append(str(e))
            history_text = "\n".join(f"Attempt {i+1}: {msg}" for i, msg in enumerate(ctx.retry.errors))
            raise ModelRetry(
                f"Previous failed attempts:\n{history_text}\n\nCurrent error: {str(e)}\nPlease correct the output."
            )
        else:
            raise ModelRetry(str(e))
    # Try strict info output
    try:
        return InfoOutput.validate_strict(output)
    except Exception as e:
        if hasattr(ctx, "retry"):
            ctx.retry.errors.append(str(e))
            history_text = "\n".join(f"Attempt {i+1}: {msg}" for i, msg in enumerate(ctx.retry.errors))
            raise ModelRetry(
                f"Previous failed attempts:\n{history_text}\n\nCurrent error: {str(e)}\nPlease correct the output."
            )
        else:
            raise ModelRetry(str(e))
    raise ModelRetry("Output is not a valid structured response. Please return a valid JSON object for the requested action, with correct stage and fields.")

# --- Dedicated DeleteMealAgent ---
class DeleteMealConfirmationOutput(BaseModel):
    stage: StageEnum
    confirmation_id: str
    action: str
    target: dict
    message: str

    @classmethod
    def validate_strict(cls, value):
        obj = cls.model_validate(value)
        if obj.stage != StageEnum.confirming_removal:
            raise ValueError("stage must be 'confirming_removal'")
        if not obj.confirmation_id or not isinstance(obj.confirmation_id, str):
            raise ValueError("confirmation_id must be a non-empty string")
        if not obj.action or not isinstance(obj.action, str):
            raise ValueError("action must be a non-empty string")
        if not obj.target or not isinstance(obj.target, dict) or "id" not in obj.target:
            raise ValueError("target must be a dict with an 'id' field")
        if not obj.message or not isinstance(obj.message, str):
            raise ValueError("message must be a non-empty string")
        return obj

def delete_meal_output_validator(output, ctx):
    if hasattr(ctx, "retry"):
        if not hasattr(ctx.retry, "errors"):
            ctx.retry.errors = []
    else:
        ctx.retry = type("Retry", (), {"errors": []})()
    if isinstance(output, dict) and output.get("stage") == "confirming_removal":
        target = output.get("target")
        if not isinstance(target, dict) or "id" not in target:
            error_msg = "You must specify a single ID for deletion."
            ctx.retry.errors.append(error_msg)
            history_text = "\n".join(f"Attempt {i+1}: {msg}" for i, msg in enumerate(ctx.retry.errors))
            raise ModelRetry(f"Previous failed attempts:\n{history_text}\n\nCurrent error: {error_msg}\nPlease correct the output.")
    return output

class DeleteMealAgent:
    def __init__(self, meal_crud):
        self.meal_crud = meal_crud
        self.agent = Agent[
            AssistantDeps, DeleteMealConfirmationOutput
        ](
            os.getenv('OPENAI_MODEL', 'openai:gpt-4o'),
            deps_type=AssistantDeps,
            output_type=DeleteMealConfirmationOutput,
            system_prompt=(
                "You are responsible for deleting a single meal. "
                "When confirming deletion, you must return a JSON object with the following fields: "
                "stage (must be 'confirming_removal'), confirmation_id (string), action (string), "
                "target (object with an 'id' field), and message (string). "
                "If any field is missing, retry and include all required fields. "
                "The 'target' field is required, but you may include additional optional fields if needed. "
                "Never delete multiple items at once. Never omit the target or id."
            ),
            tools=[
                Tool(self.delete_meal, takes_ctx=True, name="delete_meal"),
            ],
            output_validator=delete_meal_output_validator,
            retries=3,
        )

    async def delete_meal(self, ctx: RunContext[AssistantDeps], id: int, force_delete: bool = False, confirmation_id: str = None):
        db = ctx.deps.db
        logger = logging.getLogger("DeleteMealAgent.delete_meal")
        logger.info(f"[DEBUG] DeleteMealAgent.delete_meal CALLED: id={id}, force_delete={force_delete}, confirmation_id={confirmation_id}, db={db} (type={type(db)})")
        if force_delete and not confirmation_id:
            raise Exception("Force delete is only allowed after explicit user confirmation.")
        try:
            if not force_delete:
                confirmation_id = confirmation_id or str(uuid.uuid4())
                return {
                    "stage": "confirming_removal",
                    "confirmation_id": confirmation_id,
                    "action": "delete_meal",
                    "target": {"id": id},
                    "message": "Are you sure you want to delete this meal? This action cannot be undone."
                }
            ok = self.meal_crud.delete_meal(db, id)
            logger.info(f"[DEBUG] DeleteMealAgent.delete_meal: result of delete_meal: {ok}")
            return {"stage": "created", "message": f"Meal {id} deleted."} if ok else {"stage": "error", "message": f"Meal {id} not found."}
        except Exception as e:
            logger.exception(f"[DEBUG] Exception in DeleteMealAgent.delete_meal: {e}")
            return {"stage": "error", "message": str(e)}

# --- Dedicated DeleteChoreAgent ---
class DeleteChoreConfirmationOutput(BaseModel):
    stage: StageEnum
    confirmation_id: str
    action: str
    target: dict
    message: str

    @classmethod
    def validate_strict(cls, value):
        obj = cls.model_validate(value)
        if obj.stage != StageEnum.confirming_removal:
            raise ValueError("stage must be 'confirming_removal'")
        if not obj.confirmation_id or not isinstance(obj.confirmation_id, str):
            raise ValueError("confirmation_id must be a non-empty string")
        if not obj.action or not isinstance(obj.action, str):
            raise ValueError("action must be a non-empty string")
        if not obj.target or not isinstance(obj.target, dict) or "id" not in obj.target:
            raise ValueError("target must be a dict with an 'id' field")
        if not obj.message or not isinstance(obj.message, str):
            raise ValueError("message must be a non-empty string")
        return obj

def delete_chore_output_validator(output, ctx):
    if hasattr(ctx, "retry"):
        if not hasattr(ctx.retry, "errors"):
            ctx.retry.errors = []
    else:
        ctx.retry = type("Retry", (), {"errors": []})()
    if isinstance(output, dict) and output.get("stage") == "confirming_removal":
        target = output.get("target")
        if not isinstance(target, dict) or "id" not in target:
            error_msg = "You must specify a single ID for deletion."
            ctx.retry.errors.append(error_msg)
            history_text = "\n".join(f"Attempt {i+1}: {msg}" for i, msg in enumerate(ctx.retry.errors))
            raise ModelRetry(f"Previous failed attempts:\n{history_text}\n\nCurrent error: {error_msg}\nPlease correct the output.")
    return output

class DeleteChoreAgent:
    def __init__(self, chore_crud):
        self.chore_crud = chore_crud
        self.agent = Agent[
            AssistantDeps, DeleteChoreConfirmationOutput
        ](
            os.getenv('OPENAI_MODEL', 'openai:gpt-4o'),
            deps_type=AssistantDeps,
            output_type=DeleteChoreConfirmationOutput,
            system_prompt=(
                "You are responsible for deleting a single chore. "
                "When confirming deletion, you must return a JSON object with the following fields: "
                "stage (must be 'confirming_removal'), confirmation_id (string), action (string), "
                "target (object with an 'id' field), and message (string). "
                "If any field is missing, retry and include all required fields. "
                "The 'target' field is required, but you may include additional optional fields if needed. "
                "Never delete multiple items at once. Never omit the target or id."
            ),
            tools=[
                Tool(self.delete_chore, takes_ctx=True, name="delete_chore"),
            ],
            output_validator=delete_chore_output_validator,
            retries=3,
        )

    async def delete_chore(self, ctx: RunContext[AssistantDeps], id: int, force_delete: bool = False, confirmation_id: str = None):
        db = ctx.deps.db
        logger = logging.getLogger("DeleteChoreAgent.delete_chore")
        logger.info(f"[DEBUG] DeleteChoreAgent.delete_chore CALLED: id={id}, force_delete={force_delete}, confirmation_id={confirmation_id}, db={db} (type={type(db)})")
        if force_delete and not confirmation_id:
            raise Exception("Force delete is only allowed after explicit user confirmation.")
        try:
            if not force_delete:
                confirmation_id = confirmation_id or str(uuid.uuid4())
                return {
                    "stage": "confirming_removal",
                    "confirmation_id": confirmation_id,
                    "action": "delete_chore",
                    "target": {"id": id},
                    "message": "Are you sure you want to delete this chore? This action cannot be undone."
                }
            ok = self.chore_crud.delete_chore(db, id)
            logger.info(f"[DEBUG] DeleteChoreAgent.delete_chore: result of delete_chore: {ok}")
            return {"stage": "created", "message": f"Chore {id} deleted."} if ok else {"stage": "error", "message": f"Chore {id} not found."}
        except Exception as e:
            logger.exception(f"[DEBUG] Exception in DeleteChoreAgent.delete_chore: {e}")
            return {"stage": "error", "message": str(e)}

# --- Dedicated DeleteMemberAgent ---
class DeleteMemberConfirmationOutput(BaseModel):
    stage: StageEnum
    confirmation_id: str
    action: str
    target: dict
    message: str

    @classmethod
    def validate_strict(cls, value):
        obj = cls.model_validate(value)
        if obj.stage != StageEnum.confirming_removal:
            raise ValueError("stage must be 'confirming_removal'")
        if not obj.confirmation_id or not isinstance(obj.confirmation_id, str):
            raise ValueError("confirmation_id must be a non-empty string")
        if not obj.action or not isinstance(obj.action, str):
            raise ValueError("action must be a non-empty string")
        if not obj.target or not isinstance(obj.target, dict) or "id" not in obj.target:
            raise ValueError("target must be a dict with an 'id' field")
        if not obj.message or not isinstance(obj.message, str):
            raise ValueError("message must be a non-empty string")
        return obj

def delete_member_output_validator(output, ctx):
    if hasattr(ctx, "retry"):
        if not hasattr(ctx.retry, "errors"):
            ctx.retry.errors = []
    else:
        ctx.retry = type("Retry", (), {"errors": []})()
    if isinstance(output, dict) and output.get("stage") == "confirming_removal":
        target = output.get("target")
        if not isinstance(target, dict) or "id" not in target:
            error_msg = "You must specify a single ID for deletion."
            ctx.retry.errors.append(error_msg)
            history_text = "\n".join(f"Attempt {i+1}: {msg}" for i, msg in enumerate(ctx.retry.errors))
            raise ModelRetry(f"Previous failed attempts:\n{history_text}\n\nCurrent error: {error_msg}\nPlease correct the output.")
    return output

class DeleteMemberAgent:
    def __init__(self, member_crud):
        self.member_crud = member_crud
        self.agent = Agent[
            AssistantDeps, DeleteMemberConfirmationOutput
        ](
            os.getenv('OPENAI_MODEL', 'openai:gpt-4o'),
            deps_type=AssistantDeps,
            output_type=DeleteMemberConfirmationOutput,
            system_prompt=(
                "You are responsible for deleting a single family member. "
                "When confirming deletion, you must return a JSON object with the following fields: "
                "stage (must be 'confirming_removal'), confirmation_id (string), action (string), "
                "target (object with an 'id' field), and message (string). "
                "If any field is missing, retry and include all required fields. "
                "The 'target' field is required, but you may include additional optional fields if needed. "
                "Never delete multiple items at once. Never omit the target or id."
            ),
            tools=[
                Tool(self.delete_member, takes_ctx=True, name="delete_member"),
            ],
            output_validator=delete_member_output_validator,
            retries=3,
        )

    async def delete_member(self, ctx: RunContext[AssistantDeps], id: int, force_delete: bool = False, confirmation_id: str = None):
        db = ctx.deps.db
        logger = logging.getLogger("DeleteMemberAgent.delete_member")
        logger.info(f"[DEBUG] DeleteMemberAgent.delete_member CALLED: id={id}, force_delete={force_delete}, confirmation_id={confirmation_id}, db={db} (type={type(db)})")
        if force_delete and not confirmation_id:
            raise Exception("Force delete is only allowed after explicit user confirmation.")
        try:
            if not force_delete:
                confirmation_id = confirmation_id or str(uuid.uuid4())
                return {
                    "stage": "confirming_removal",
                    "confirmation_id": confirmation_id,
                    "action": "delete_member",
                    "target": {"id": id},
                    "message": "Are you sure you want to delete this member? This action cannot be undone."
                }
            ok = self.member_crud.delete_member(db, id)
            logger.info(f"[DEBUG] DeleteMemberAgent.delete_member: result of delete_member: {ok}")
            return {"stage": "created", "message": f"Member {id} deleted."} if ok else {"stage": "error", "message": f"Member {id} not found."}
        except Exception as e:
            logger.exception(f"[DEBUG] Exception in DeleteMemberAgent.delete_member: {e}")
            return {"stage": "error", "message": str(e)}

# --- Dedicated DeleteRecipeAgent ---
class DeleteRecipeConfirmationOutput(BaseModel):
    stage: StageEnum
    confirmation_id: str
    action: str
    target: dict
    message: str

    @classmethod
    def validate_strict(cls, value):
        obj = cls.model_validate(value)
        if obj.stage != StageEnum.confirming_removal:
            raise ValueError("stage must be 'confirming_removal'")
        if not obj.confirmation_id or not isinstance(obj.confirmation_id, str):
            raise ValueError("confirmation_id must be a non-empty string")
        if not obj.action or not isinstance(obj.action, str):
            raise ValueError("action must be a non-empty string")
        if not obj.target or not isinstance(obj.target, dict) or "id" not in obj.target:
            raise ValueError("target must be a dict with an 'id' field")
        if not obj.message or not isinstance(obj.message, str):
            raise ValueError("message must be a non-empty string")
        return obj

def delete_recipe_output_validator(output, ctx):
    if hasattr(ctx, "retry"):
        if not hasattr(ctx.retry, "errors"):
            ctx.retry.errors = []
    else:
        ctx.retry = type("Retry", (), {"errors": []})()
    if isinstance(output, dict) and output.get("stage") == "confirming_removal":
        target = output.get("target")
        if not isinstance(target, dict) or "id" not in target:
            error_msg = "You must specify a single ID for deletion."
            ctx.retry.errors.append(error_msg)
            history_text = "\n".join(f"Attempt {i+1}: {msg}" for i, msg in enumerate(ctx.retry.errors))
            raise ModelRetry(f"Previous failed attempts:\n{history_text}\n\nCurrent error: {error_msg}\nPlease correct the output.")
    return output

class DeleteRecipeAgent:
    def __init__(self, recipe_crud):
        self.recipe_crud = recipe_crud
        self.agent = Agent[
            AssistantDeps, DeleteRecipeConfirmationOutput
        ](
            os.getenv('OPENAI_MODEL', 'openai:gpt-4o'),
            deps_type=AssistantDeps,
            output_type=DeleteRecipeConfirmationOutput,
            system_prompt=(
                "You are responsible for deleting a single recipe. "
                "When confirming deletion, you must return a JSON object with the following fields: "
                "stage (must be 'confirming_removal'), confirmation_id (string), action (string), "
                "target (object with an 'id' field), and message (string). "
                "If any field is missing, retry and include all required fields. "
                "The 'target' field is required, but you may include additional optional fields if needed. "
                "Never delete multiple items at once. Never omit the target or id."
            ),
            tools=[
                Tool(self.delete_recipe, takes_ctx=True, name="delete_recipe"),
            ],
            output_validator=delete_recipe_output_validator,
            retries=3,
        )

    async def delete_recipe(self, ctx: RunContext[AssistantDeps], id: int, force_delete: bool = False, confirmation_id: str = None):
        db = ctx.deps.db
        logger = logging.getLogger("DeleteRecipeAgent.delete_recipe")
        logger.info(f"[DEBUG] DeleteRecipeAgent.delete_recipe CALLED: id={id}, force_delete={force_delete}, confirmation_id={confirmation_id}, db={db} (type={type(db)})")
        if force_delete and not confirmation_id:
            raise Exception("Force delete is only allowed after explicit user confirmation.")
        try:
            if not force_delete:
                confirmation_id = confirmation_id or str(uuid.uuid4())
                return {
                    "stage": "confirming_removal",
                    "confirmation_id": confirmation_id,
                    "action": "delete_recipe",
                    "target": {"id": id},
                    "message": "Are you sure you want to delete this recipe? This action cannot be undone."
                }
            ok = self.recipe_crud.delete_recipe(db, id)
            logger.info(f"[DEBUG] DeleteRecipeAgent.delete_recipe: result of delete_recipe: {ok}")
            return {"stage": "created", "message": f"Recipe {id} deleted."} if ok else {"stage": "error", "message": f"Recipe {id} not found."}
        except Exception as e:
            logger.exception(f"[DEBUG] Exception in DeleteRecipeAgent.delete_recipe: {e}")
            return {"stage": "error", "message": str(e)}

class HouseholdAssistantAgent:
    def __init__(self):
        print("DEBUG: ALLOW_MODEL_REQUESTS =", os.environ.get("ALLOW_MODEL_REQUESTS"))
        load_dotenv()
        self.system_prompt = load_system_prompt()
        
        # Create tools list and store as self.tools
        self.delete_meal_agent = DeleteMealAgent(meal_crud)
        self.delete_chore_agent = DeleteChoreAgent(chore_crud)
        self.delete_member_agent = DeleteMemberAgent(member_crud)
        self.delete_recipe_agent = DeleteRecipeAgent(recipe_crud)
        self.sub_agents = [self.delete_meal_agent, self.delete_chore_agent, self.delete_member_agent, self.delete_recipe_agent]
        self.tools = [
            Tool(self._create_chore, takes_ctx=True, name="create_chore"),
            Tool(self._list_chores, takes_ctx=True, name="list_chores"),
            Tool(self._update_chore, takes_ctx=True, name="update_chore"),
            Tool(self._delete_chore_delegate, takes_ctx=True, name="delete_chore"),
            Tool(self._create_meal, takes_ctx=True, name="create_meal"),
            Tool(self._list_meals, takes_ctx=True, name="list_meals"),
            Tool(self._update_meal, takes_ctx=True, name="update_meal"),
            Tool(self._delete_meal_delegate, takes_ctx=True, name="delete_meal"),
            Tool(self._create_member, takes_ctx=True, name="create_member"),
            Tool(self._list_members, takes_ctx=True, name="list_members"),
            Tool(self._update_member, takes_ctx=True, name="update_member"),
            Tool(self._delete_member_delegate, takes_ctx=True, name="delete_member"),
            Tool(self._create_recipe, takes_ctx=True, name="create_recipe"),
            Tool(self._list_recipes, takes_ctx=True, name="list_recipes"),
            Tool(self._update_recipe, takes_ctx=True, name="update_recipe"),
            Tool(self._delete_recipe_delegate, takes_ctx=True, name="delete_recipe"),
        ]
        # Map tool names to internal functions for backend invocation
        self.tool_funcs = {
            "create_chore": self._create_chore,
            "list_chores": self._list_chores,
            "update_chore": self._update_chore,
            "delete_chore": self._delete_chore_delegate,
            "create_meal": self._create_meal,
            "list_meals": self._list_meals,
            "update_meal": self._update_meal,
            "delete_meal": self._delete_meal_delegate,
            "create_member": self._create_member,
            "list_members": self._list_members,
            "update_member": self._update_member,
            "delete_member": self._delete_member_delegate,
            "create_recipe": self._create_recipe,
            "list_recipes": self._list_recipes,
            "update_recipe": self._update_recipe,
            "delete_recipe": self._delete_recipe_delegate,
        }
        # Pass self.tools to Agent
        self.agent = Agent[
            AssistantDeps, Union[ConfirmationOutput, InfoOutput]
        ](
            os.getenv('OPENAI_MODEL', 'openai:gpt-4o'),
            deps_type=AssistantDeps,
            output_type=Union[ConfirmationOutput, InfoOutput],
            system_prompt=self.system_prompt,
            tools=self.tools,
            output_validator=agent_output_validator,
            retries=3,  # Allow up to 3 retries for the agent as a whole
        )
        # self.agent.model = os.getenv('OPENAI_MODEL', 'openai:gpt-4o')  # Ensure model is always set
        self._start_prompt_watcher()
        # If a model is already set, propagate to sub-agents
        if getattr(self.agent, "model", None) is not None:
            self.propagate_model_override(self.agent.model)

    def propagate_model_override(self, model):
        """
        Set the .model attribute of the main agent and all sub-agents to the given model.
        Call this in tests to ensure all agents use the same test/dummy model.
        Extend self.sub_agents with new sub-agents as needed.
        """
        self.agent.model = model
        for sub in self.sub_agents:
            if hasattr(sub, "agent"):
                sub.agent.model = model

    def reload_prompt(self):
        self.system_prompt = load_system_prompt()
        self.agent.system_prompt = self.system_prompt

    def _start_prompt_watcher(self):
        watch_file_for_changes(PROMPT_PATH, self.reload_prompt, logger_name="llm_agent.prompt_watcher")

    # Tool implementations
    async def _create_chore(self, ctx: RunContext[AssistantDeps], chore_name: str = None, assigned_members: list = None, start_date: str = None, repetition: str = None, due_time: Optional[str] = None, reminder: Optional[str] = None, type: Optional[str] = None):
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

    async def _list_chores(self, ctx: RunContext[AssistantDeps]):
        db = ctx.deps.db
        chores = chore_crud.get_chores(db)
        if not chores:
            return "<!-- stage: confirming_info -->\nNo chores found."
        header = '| ID | Chore Name | Assigned Members | Repetition | Due Time | Type |\n|---|---|---|---|---|---|'
        rows = [
            f"| {c.id} | {c.chore_name} | {', '.join(str(m) for m in c.assigned_members)} | {c.repetition} | {c.due_time} | {c.type or ''} |"
            for c in chores
        ]
        return f"<!-- stage: confirming_info -->\n**Chores**\n\n{header}\n" + "\n".join(rows)

    async def _update_chore(self, ctx: RunContext[AssistantDeps], id: int, **kwargs):
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

    # Delegating tool for chore deletion
    async def _delete_chore_delegate(self, ctx: RunContext[AssistantDeps], id: int, force_delete: bool = False, confirmation_id: str = None):
        if force_delete:
            return await self.delete_chore_agent.delete_chore(ctx, id=id, force_delete=True, confirmation_id=confirmation_id)
        else:
            prompt = f"Delete chore {id}"
            return await self.delete_chore_agent.agent.run(
                prompt,
                deps=ctx.deps,
                usage=ctx.usage,
            )

    # Delegating tool for member deletion
    async def _delete_member_delegate(self, ctx: RunContext[AssistantDeps], id: int, force_delete: bool = False, confirmation_id: str = None):
        if force_delete:
            return await self.delete_member_agent.delete_member(ctx, id=id, force_delete=True, confirmation_id=confirmation_id)
        else:
            prompt = f"Delete member {id}"
            return await self.delete_member_agent.agent.run(
                prompt,
                deps=ctx.deps,
                usage=ctx.usage,
            )

    # Delegating tool for recipe deletion
    async def _delete_recipe_delegate(self, ctx: RunContext[AssistantDeps], id: int, force_delete: bool = False, confirmation_id: str = None):
        if force_delete:
            return await self.delete_recipe_agent.delete_recipe(ctx, id=id, force_delete=True, confirmation_id=confirmation_id)
        else:
            prompt = f"Delete recipe {id}"
            return await self.delete_recipe_agent.agent.run(
                prompt,
                deps=ctx.deps,
                usage=ctx.usage,
            )

    # Delegating tool for meal deletion
    async def _delete_meal_delegate(self, ctx: RunContext[AssistantDeps], id: int, force_delete: bool = False, confirmation_id: str = None):
        # For confirmation, call the destructive tool directly (not via agent)
        if force_delete:
            # Call the DeleteMealAgent's delete_meal method directly
            return await self.delete_meal_agent.delete_meal(ctx, id=id, force_delete=True, confirmation_id=confirmation_id)
        else:
            # Normal delegation to the sub-agent
            prompt = f"Delete meal {id}"
            return await self.delete_meal_agent.agent.run(
                prompt,
                deps=ctx.deps,
                usage=ctx.usage,
            )

    async def _create_meal(self, ctx: RunContext[AssistantDeps], meal_name: str = None, exist: bool = None, meal_kind: str = None, meal_date: str = None, dishes: str = None):
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
            "🎉 **Meal Created!**\n\n"
            f"🍽️ **Name:** `{m.meal_name}`\n"
            f"🗓️ **Date:** `{m.meal_date}`\n"
            f"🍳 **Kind:** `{m.meal_kind}`\n"
            f"🍲 **Dishes:** `{', '.join(m.dishes) if m.dishes else '—'}`\n"
            f"📖 **Exists in DB:** `{m.exist}`\n"
            "Meal planning complete!"
        )

    async def _list_meals(self, ctx: RunContext[AssistantDeps]):
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

    async def _update_meal(self, ctx: RunContext[AssistantDeps], id: int, **kwargs):
        db = ctx.deps.db
        m = meal_crud.get_meal(db, id)
        if not m:
            return f"<!-- stage: error -->\nMeal with ID `{id}` not found. Please provide a valid meal ID."
        data = {k: kwargs[k] for k in kwargs if k in MealCreate.model_fields}
        # Fix: ensure dishes is a list
        dishes = m.dishes
        if isinstance(dishes, str):
            dishes = [d.strip() for d in dishes.split(',') if d.strip()]
        if "dishes" in data and isinstance(data["dishes"], str):
            data["dishes"] = [d.strip() for d in data["dishes"].split(',') if d.strip()]
        meal = MealCreate(**{**m.__dict__, **data, "dishes": data.get("dishes", dishes)})
        updated = meal_crud.update_meal(db, id, meal)
        return (
            "<!-- stage: confirming_info -->\n"
            f"✅ **Meal Updated!**\n\n"
            f"🍽️ **Name:** `{meal.meal_name}`\n"
            f"🍳 **Kind:** `{meal.meal_kind}`\n"
            f"📅 **Date:** `{meal.meal_date}`\n"
            f"🥗 **Dishes:** {', '.join(meal.dishes or [])}\n\n"
            "If everything looks good, type **Done** to confirm or **Edit** to change anything."
        )

    async def _create_member(self, ctx: RunContext[AssistantDeps], name: str = None, gender: Optional[str] = None, avatar: Optional[str] = None):
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

    async def _list_members(self, ctx: RunContext[AssistantDeps]):
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

    async def _update_member(self, ctx: RunContext[AssistantDeps], id: int, **kwargs):
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

    async def _list_recipes(self, ctx: RunContext[AssistantDeps]):
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

    async def _create_recipe(self, ctx: RunContext[AssistantDeps], name: str = None, kind: str = None, description: str = ""):
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

    async def _update_recipe(self, ctx: RunContext[AssistantDeps], id: int, **kwargs):
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