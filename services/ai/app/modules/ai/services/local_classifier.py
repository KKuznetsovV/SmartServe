"""First-tier local intent classifier using the quantized GGUF model.

Wraps llama-cpp-python so the router sees only classify() → dict | None,
matching the shape returned by the Haiku path. Returns None when the model
is not loaded (LOCAL_MODEL_PATH unset or load failed) so the router falls
through to Haiku/Sonnet transparently — no behaviour change when disabled.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

_llm = None  # loaded once at service startup; None = feature disabled

# Map the local model's flat intent names to the namespaced intent strings
# the dispatch layer (and the rest of the Haiku pipeline) already understands.
_INTENT_MAP: dict[str, str] = {
    "update_price": "menu.update_item",
    "create_item": "menu.create_item",
    "delete_item": "menu.move_to_trash",
    "update_description": "menu.update_item",
    "update_item_name": "menu.update_item",
    "route_printer": "printer.route",
    "update_stock": "menu.toggle_availability",
}

# Rename slot keys that differ from the param keys the dispatch layer expects.
_SLOT_RENAMES: dict[str, str] = {
    "item_ref": "item_hint",
    "item_name": "name",
    "target_ref": "target_hint",
    "printer_ref": "printer_hint",
}

_STOCK_IN = {"in_stock", "available", "true", "yes", "1"}

_INSTRUCTION = (
    "You classify a restaurant manager's message into a structured action "
    "for a POS system. "
    "Respond with ONLY a JSON object, no prose, no markdown fences:\n"
    '{"intent": "<one of: update_price, create_item, delete_item, '
    "update_description, update_item_name, route_printer, update_stock, unclear>"
    ', "confidence": <float 0-1>, "slots": {"<slot_name>": "<value>"}}'
)


def _map_slots(local_intent: str, slots: dict) -> dict:
    params: dict = {}
    for k, v in slots.items():
        params[_SLOT_RENAMES.get(k, k)] = v
    # Normalise stock_status string → in_stock bool for menu.toggle_availability
    if local_intent == "update_stock" and "stock_status" in slots:
        params["in_stock"] = str(slots["stock_status"]).lower().strip() in _STOCK_IN
        params.pop("stock_status", None)
    return params


def load_model(path: str) -> None:
    """Load the GGUF model once at service startup.

    Failure is non-fatal: a missing/corrupt model file logs a warning and
    leaves _llm=None so classify() returns None and the router falls through
    to Haiku as if the local tier were not configured at all.
    """
    global _llm
    try:
        # Import inside the function so the package is only required when a
        # LOCAL_MODEL_PATH is actually set; CI without llama-cpp-python still works.
        from llama_cpp import Llama  # type: ignore[import-untyped]

        _llm = Llama(model_path=path, n_ctx=1024, n_threads=4, verbose=False)
        logger.info("local classifier loaded from %s", path)
    except Exception as exc:
        logger.warning("local classifier unavailable (%s) — falling through to Haiku", exc)
        _llm = None


def classify(message: str) -> dict | None:
    """Classify *message* with the local GGUF model.

    Returns a dict with the same keys the Haiku path produces
    (intent, confidence, params, preview, source) or None when the model is
    not loaded or the model itself signals uncertainty (intent == 'unclear').
    Returning None tells the router to fall through to the Haiku/Sonnet pipeline.
    """
    if _llm is None:
        return None

    prompt = f"### Instruction:\n{_INSTRUCTION}\n\n### Input:\n{message}\n\n### Response:\n"
    try:
        output = _llm(prompt, max_tokens=200, stop=["###"], temperature=0.0)
        text = output["choices"][0]["text"].strip()  # type: ignore[index]
        parsed = json.loads(text)
    except Exception as exc:
        logger.debug("local classifier inference/parse error: %s", exc)
        return None

    local_intent: str = str(parsed.get("intent", "unclear"))
    confidence: float = float(parsed.get("confidence", 0.0))
    slots: dict = parsed.get("slots") or {}

    if local_intent == "unclear":
        return None  # model signals uncertainty → escalate to Haiku

    mapped_intent = _INTENT_MAP.get(local_intent)
    if mapped_intent is None:
        return None  # unknown intent name → escalate

    return {
        "intent": mapped_intent,
        "confidence": confidence,
        "params": _map_slots(local_intent, slots),
        # Haiku generates a localised preview string; local model omits it.
        # The confirm dialog still works — it just shows an empty preview line.
        "preview": "",
        "source": "local_model",
    }
