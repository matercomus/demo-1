from pydantic_ai import Agent
from pydantic import BaseModel
from functools import lru_cache
import logging
import os
from backend.agents.prompt_watcher import watch_file_for_changes

class StageClassifierOutput(BaseModel):
    stage: str

ALLOWED_STAGES = {"collecting_info", "confirming_info", "created", "error"}

PROMPT_PATH = os.path.join(os.path.dirname(__file__), '../../prompts/stage_classifier_prompt.md')

def load_classifier_prompt():
    logger = logging.getLogger("stage_classifier")
    try:
        with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
            prompt = f.read()
            logger.info(f"Loaded stage classifier prompt from {PROMPT_PATH}")
            return prompt
    except Exception as e:
        logger.warning(f"Failed to load stage classifier prompt from {PROMPT_PATH}, using fallback. Error: {e}")
        # Fallback: minimal prompt
        return (
            "You are a classifier. Given an assistant reply, classify it into one of these stages: collecting_info, confirming_info, created, error.\n"
            "Only output the stage name, nothing else.\n"
            "Reply:\n\"\"\"\n{reply}\n\"\"\"\nStage:"
        )

# Add a reload function and watcher setup
_stage_classifier_prompt = load_classifier_prompt()

def reload_prompt():
    global _stage_classifier_prompt, stage_classifier_agent
    logger = logging.getLogger("stage_classifier")
    _stage_classifier_prompt = load_classifier_prompt()
    stage_classifier_agent.instructions = _stage_classifier_prompt
    logger.info("Stage classifier prompt reloaded and agent updated.")

watch_file_for_changes(PROMPT_PATH, reload_prompt, logger_name="stage_classifier.prompt_watcher")

stage_classifier_agent = Agent(
    'openai:gpt-3.5-turbo',
    output_type=StageClassifierOutput,
    instructions=_stage_classifier_prompt
)

@lru_cache(maxsize=128)
def classify_stage_llm(reply: str) -> str:
    logger = logging.getLogger("stage_classifier")
    try:
        reply_lower = reply.lower()
        if any(kw in reply_lower for kw in ["successfully created", "has been created", "has been successfully", "added", "created", "was created", "has been added"]):
            logger.info(f"[STAGE OVERRIDE] Detected strong 'created' signal in reply: {reply}")
            return "created"
        logger.info(f"[STAGE PROMPT] Classifying reply: {reply}")
        result = stage_classifier_agent.run_sync({"reply": reply})
        stage = result.output.stage.strip().lower()
        logger.info(f"[STAGE LLM] LLM output: '{stage}' for reply: {reply}")
        if stage not in ALLOWED_STAGES:
            logger.warning(f"[STAGE LLM] LLM returned unknown stage '{stage}' for reply: {reply}")
            stage = "unknown"
        return stage
    except Exception as e:
        logger.warning(f"[STAGE FALLBACK] LLM failed, using heuristic. Error: {e}")
        reply_lower = reply.lower()
        if any(word in reply_lower for word in ["what would you like", "please provide", "could you", "need", "missing", "specify", "details", "information"]):
            return 'collecting_info'
        elif any(word in reply_lower for word in ["confirm", "summary", "does this look", "type 'done'", "edit"]):
            return 'confirming_info'
        elif any(word in reply_lower for word in ["created", "success", "added", "complete", "done", "has been added", "successfully added", "added as a", "has been successfully"]):
            return 'created'
        elif any(word in reply_lower for word in ["error", "not found", "invalid"]):
            return 'error'
        return 'unknown'

async def classify_stage_llm_async(reply: str) -> str:
    logger = logging.getLogger("stage_classifier")
    try:
        reply_lower = reply.lower()
        if any(kw in reply_lower for kw in ["successfully created", "has been created", "has been successfully", "added", "created", "was created", "has been added"]):
            logger.info(f"[STAGE OVERRIDE] Detected strong 'created' signal in reply: {reply}")
            return "created"
        logger.info(f"[STAGE PROMPT] Classifying reply: {reply}")
        result = await stage_classifier_agent.run(reply=reply)
        stage = result.output.stage.strip().lower()
        logger.info(f"[STAGE LLM] LLM output: '{stage}' for reply: {reply}")
        if stage not in ALLOWED_STAGES:
            logger.warning(f"[STAGE LLM] LLM returned unknown stage '{stage}' for reply: {reply}")
            stage = "unknown"
        return stage
    except Exception as e:
        logger.warning(f"[STAGE FALLBACK] LLM failed, using heuristic. Error: {e}")
        reply_lower = reply.lower()
        if any(word in reply_lower for word in ["what would you like", "please provide", "could you", "need", "missing", "specify", "details", "information"]):
            return 'collecting_info'
        elif any(word in reply_lower for word in ["confirm", "summary", "does this look", "type 'done'", "edit"]):
            return 'confirming_info'
        elif any(word in reply_lower for word in ["created", "success", "added", "complete", "done", "has been added", "successfully added", "added as a", "has been successfully"]):
            return 'created'
        elif any(word in reply_lower for word in ["error", "not found", "invalid"]):
            return 'error'
        return 'unknown' 