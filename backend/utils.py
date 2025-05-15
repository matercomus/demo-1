from typing import List, Any
from pydantic_ai.messages import UserPromptPart, SystemPromptPart

def normalize_message_history(history: List[Any]) -> List[Any]:
    """
    Convert a list of dicts or message-like objects into a list of UserPromptPart/SystemPromptPart objects.
    Ignores entries that do not have the required structure.
    """
    result = []
    for m in history:
        role = m.get('role') if isinstance(m, dict) else getattr(m, 'role', None)
        content = m.get('content') if isinstance(m, dict) else getattr(m, 'content', None)
        if role == "user":
            result.append(UserPromptPart(content=content))
        elif role == "system":
            result.append(SystemPromptPart(content=content))
        # Optionally handle "assistant" or other roles if needed
    return result 