"""AI command endpoint — intent classification and action preview."""
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import anthropic

from app.core.config import settings
from app.core.security import decode_token

router = APIRouter()
bearer = HTTPBearer()

# All supported intents — sent as context to Haiku for classification
SUPPORTED_INTENTS = [
    "menu.create_item",
    "menu.update_item",
    "menu.bulk_price_change",
    "menu.toggle_availability",
    "menu.create_category",
    "menu.create_modifier_group",
    "printer.route",
    "printer.troubleshoot",
    "report.query",
    "staff.add_user",
    "staff.set_permissions",
    "inventory.set_threshold",
    "settings.business",
    "help.general",
]

INTENT_SYSTEM_PROMPT = """You are the intent classifier for SmartServe, a restaurant POS system.
Classify the user's request into exactly one of these intents and extract parameters.

Intents: {intents}

Return ONLY valid JSON in this exact format:
{{
  "intent": "<intent_name>",
  "confidence": <0.0-1.0>,
  "params": {{<extracted parameters as key-value pairs>}},
  "preview": "<one sentence describing what will happen in Hebrew or English matching the user's language>"
}}

Examples:
- "Add margherita pizza for 58 NIS" → intent: menu.create_item, params: {{name: "Margherita Pizza", price: 58, currency: "ILS"}}
- "הגדל את כל מחירי הפסטה ב-10%" → intent: menu.bulk_price_change, params: {{category_hint: "פסטה", change_pct: 10}}
- "Send pasta orders to the kitchen printer" → intent: printer.route, params: {{category_hint: "pasta", printer_hint: "kitchen"}}
"""


class CommandRequest(BaseModel):
    message: str
    context: dict


class ConfirmRequest(BaseModel):
    execution_id: str


# In-memory pending executions store (replace with Redis in step/02)
_pending: dict[str, dict] = {}


@router.post("/command")
async def ai_command(
    body: CommandRequest,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    decode_token(credentials.credentials)  # validates JWT

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not configured (set ANTHROPIC_API_KEY)",
        )

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    system = INTENT_SYSTEM_PROMPT.format(intents=", ".join(SUPPORTED_INTENTS))

    message = client.messages.create(
        model=settings.AI_INTENT_MODEL,
        max_tokens=256,
        system=system,
        messages=[{"role": "user", "content": body.message}],
    )

    try:
        result = json.loads(message.content[0].text)
    except (json.JSONDecodeError, IndexError, KeyError):
        # Fallback to Sonnet when Haiku produces malformed output
        message = client.messages.create(
            model=settings.AI_COMPLEX_MODEL,
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": body.message}],
        )
        result = json.loads(message.content[0].text)

    confidence: float = result.get("confidence", 0)

    # If confidence is low, use Sonnet for a more careful classification
    if confidence < settings.AI_INTENT_CONFIDENCE_THRESHOLD:
        message = client.messages.create(
            model=settings.AI_COMPLEX_MODEL,
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": body.message}],
        )
        result = json.loads(message.content[0].text)

    execution_id = str(uuid.uuid4())
    _pending[execution_id] = {
        "intent": result.get("intent"),
        "params": result.get("params", {}),
        "context": body.context,
    }

    return {
        "intent": result.get("intent"),
        "confidence": result.get("confidence"),
        "params": result.get("params", {}),
        "preview": result.get("preview", ""),
        "requiresConfirmation": True,
        "executionId": execution_id,
    }


@router.post("/confirm")
async def ai_confirm(
    body: ConfirmRequest,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    decode_token(credentials.credentials)

    pending = _pending.pop(body.execution_id, None)
    if not pending:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found or already confirmed")

    # TODO: dispatch to the appropriate service based on intent (implemented in step/08)
    return {"success": True, "message": f"Action '{pending['intent']}' queued for execution"}
