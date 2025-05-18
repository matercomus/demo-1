from pydantic_ai import Agent
from pydantic import BaseModel
from functools import lru_cache
import logging
import os
from backend.agents.prompt_watcher import watch_file_for_changes
from backend.agents.stage_keywords import STAGE_KEYWORDS_PRIORITY
import re

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

def keyword_in_text(keyword, text):
    # Match as a whole word, ignoring case and punctuation
    # Remove punctuation and symbols from text for matching
    text_clean = re.sub(r'[^\w\s]', ' ', text)
    # Use word boundaries for keywords with only word characters, else fallback to simple case-insensitive search
    if re.match(r'^\w+$', keyword):
        return re.search(rf'\b{re.escape(keyword)}\b', text_clean, re.IGNORECASE) is not None
    else:
        return re.search(re.escape(keyword), text, re.IGNORECASE) is not None

@lru_cache(maxsize=128)
def classify_stage_llm(reply: str) -> str:
    logger = logging.getLogger("stage_classifier")
    try:
        reply_lower = reply.lower()
        for stage, keywords in STAGE_KEYWORDS_PRIORITY:
            for kw in keywords:
                if keyword_in_text(kw, reply_lower):
                    logger.info(f"[STAGE OVERRIDE] Detected strong '{stage}' signal in reply: {reply} (matched phrase: '{kw}')")
                    return stage
        logger.info(f"[STAGE PROMPT] Classifying reply: {reply}")
        result = stage_classifier_agent.run_sync({"reply": reply})
        stage = result.output.stage.strip().lower()
        logger.info(f"[STAGE LLM] Raw LLM output: '{stage}' for reply: {reply}")
        if stage not in ALLOWED_STAGES:
            if stage == "other":
                logger.info(f"[STAGE LLM] LLM returned 'other', mapping to 'collecting_info' for reply: {reply}")
                stage = "collecting_info"
            else:
                logger.warning(f"[STAGE LLM] LLM returned unknown stage '{stage}' for reply: {reply}")
                stage = "unknown"
        else:
            logger.info(f"[STAGE LLM] LLM output '{stage}' accepted for reply: {reply}")
        return stage
    except Exception as e:
        logger.warning(f"[STAGE FALLBACK] LLM failed, using heuristic. Error: {e}")
        reply_lower = reply.lower()
        for stage, keywords in STAGE_KEYWORDS_PRIORITY:
            for word in keywords:
                if keyword_in_text(word, reply_lower):
                    logger.info(f"[STAGE FALLBACK] Heuristic matched '{stage}' for reply: {reply} (matched phrase: '{word}')")
                    return stage
        logger.info(f"[STAGE FALLBACK] No heuristic match, returning 'unknown' for reply: {reply}")
        return 'unknown'

async def classify_stage_llm_async(reply: str) -> str:
    logger = logging.getLogger("stage_classifier")
    try:
        reply_lower = reply.lower()
        for stage, keywords in STAGE_KEYWORDS_PRIORITY:
            for kw in keywords:
                if keyword_in_text(kw, reply_lower):
                    logger.info(f"[STAGE OVERRIDE] Detected strong '{stage}' signal in reply: {reply} (matched phrase: '{kw}')")
                    return stage
        logger.info(f"[STAGE PROMPT] Classifying reply: {reply}")
        result = await stage_classifier_agent.run(reply=reply)
        stage = result.output.stage.strip().lower()
        logger.info(f"[STAGE LLM] Raw LLM output: '{stage}' for reply: {reply}")
        if stage not in ALLOWED_STAGES:
            if stage == "other":
                logger.info(f"[STAGE LLM] LLM returned 'other', mapping to 'collecting_info' for reply: {reply}")
                stage = "collecting_info"
            else:
                logger.warning(f"[STAGE LLM] LLM returned unknown stage '{stage}' for reply: {reply}")
                stage = "unknown"
        else:
            logger.info(f"[STAGE LLM] LLM output '{stage}' accepted for reply: {reply}")
        return stage
    except Exception as e:
        logger.warning(f"[STAGE FALLBACK] LLM failed, using heuristic. Error: {e}")
        reply_lower = reply.lower()
        for stage, keywords in STAGE_KEYWORDS_PRIORITY:
            for word in keywords:
                if keyword_in_text(word, reply_lower):
                    logger.info(f"[STAGE FALLBACK] Heuristic matched '{stage}' for reply: {reply} (matched phrase: '{word}')")
                    return stage
        logger.info(f"[STAGE FALLBACK] No heuristic match, returning 'unknown' for reply: {reply}")
        return 'unknown' 