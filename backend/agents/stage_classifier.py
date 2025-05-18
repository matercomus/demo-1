from pydantic_ai import Agent
from pydantic import BaseModel
from functools import lru_cache
import logging

class StageClassifierOutput(BaseModel):
    stage: str

stage_classifier_agent = Agent(
    'openai:gpt-3.5-turbo',
    output_type=StageClassifierOutput,
    system_prompt=(
        "You are a classifier. Given an assistant reply, classify it into one of these stages: collecting_info, confirming_info, created, error.\n"
        "Examples:\n"
        "Reply: 'Could you please provide more details about the chore?'\nStage: collecting_info\n"
        "Reply: 'Here is a summary of your new chore. Does this look correct?'\nStage: confirming_info\n"
        "Reply: 'The chore \'Laundry\' has been successfully created.'\nStage: created\n"
        "Reply: 'Sorry, I couldn't find that member.'\nStage: error\n"
        "Reply: {reply}\nStage:"
    )
)

@lru_cache(maxsize=128)
def classify_stage_llm(reply: str) -> str:
    logger = logging.getLogger("stage_classifier")
    try:
        # Post-processing override for strong signals
        reply_lower = reply.lower()
        if any(kw in reply_lower for kw in ["successfully created", "has been created", "has been successfully", "added", "created", "was created", "has been added"]):
            logger.info(f"[STAGE OVERRIDE] Detected strong 'created' signal in reply: {reply}")
            return "created"
        # Use Pydantic AI Agent
        result = stage_classifier_agent.run_sync({"reply": reply})
        stage = result.output.stage.strip().lower()
        if stage not in {"collecting_info", "confirming_info", "created", "error"}:
            logger.info(f"[STAGE LLM] LLM returned unknown stage '{stage}' for reply: {reply}")
            stage = "unknown"
        else:
            logger.info(f"[STAGE LLM] LLM classified stage as '{stage}' for reply: {reply}")
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
        # Use Pydantic AI Agent async API
        result = await stage_classifier_agent.run(reply=reply)
        stage = result.output.stage.strip().lower()
        if stage not in {"collecting_info", "confirming_info", "created", "error"}:
            logger.info(f"[STAGE LLM] LLM returned unknown stage '{stage}' for reply: {reply}")
            stage = "unknown"
        else:
            logger.info(f"[STAGE LLM] LLM classified stage as '{stage}' for reply: {reply}")
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