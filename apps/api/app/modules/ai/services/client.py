"""Thin wrapper around the Anthropic SDK: off-loop calls plus JSON reply parsing."""

import asyncio
import json

import anthropic
from fastapi import HTTPException, status


def parse_json_reply(message: anthropic.types.Message) -> dict:
    """Claude occasionally wraps JSON in ```json fences despite instructions — strip and retry."""
    # content blocks are always text for our prompts (SDK's union type doesn't reflect that)
    text = message.content[0].text  # type: ignore[union-attr]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        stripped = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(stripped)


def parse_menu_import_reply(message: anthropic.types.Message) -> dict:
    """Like parse_json_reply, but turns a truncated/invalid reply into a clean HTTP error
    instead of an unhandled 500 (large menus can exceed max_tokens and cut the JSON off mid-item)."""
    try:
        return parse_json_reply(message)
    except (json.JSONDecodeError, IndexError) as exc:
        if message.stop_reason == "max_tokens":
            detail = "The menu was too large for the AI to process in one go — try uploading fewer items at a time"
        else:
            detail = "AI returned an invalid response, please try again"
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail) from exc


async def create_message(client: anthropic.Anthropic, **kwargs) -> anthropic.types.Message:
    """Call the Anthropic API off the event loop, turning SDK errors into clean HTTP responses."""
    try:
        # SDK's overloaded create() signature doesn't line up with to_thread's expected callable type
        return await asyncio.to_thread(client.messages.create, **kwargs)  # type: ignore[arg-type]
    except anthropic.RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="AI service is busy, please try again shortly"
        ) from exc
    except anthropic.APIStatusError as exc:
        message = exc.body.get("error", {}).get("message") if isinstance(exc.body, dict) else str(exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI service error: {message}") from exc
    except anthropic.APIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI service error: {exc}") from exc
