"""System prompts and the supported-intent list used by the AI assistant."""

# All supported intents — sent as context to Haiku for classification
SUPPORTED_INTENTS = [
    "menu.create_item",
    "menu.update_item",
    "menu.bulk_price_change",
    "menu.toggle_availability",
    "menu.create_category",
    "menu.reorganize_categories",
    "menu.move_items_to_category",
    "menu.create_modifier_group",
    "menu.move_to_trash",
    "menu.restore_item",
    "menu.permanently_delete_item",
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

Today's date is {today} (UTC). When a request implies a date range (e.g. "last week", "yesterday",
"this month") compute concrete "start"/"end" dates (YYYY-MM-DD, inclusive) relative to today's date
yourself — never return a relative phrase like "last week" as a param value.

Return ONLY valid JSON in this exact format:
{{
  "intent": "<intent_name>",
  "confidence": <0.0-1.0>,
  "params": {{<extracted parameters as key-value pairs>}},
  "preview": "<one sentence describing what will happen in Hebrew or English matching the user's language>"
}}

Examples:
- "Add margherita pizza for 58 NIS" → intent: menu.create_item, params: {{name: "Margherita Pizza", price: 58, currency: "ILS"}}
- "Rename the Coke to Coca-Cola" → intent: menu.update_item, params: {{item_hint: "Coke", new_name: "Coca-Cola"}}
- "Delete the Margherita Pizza" → intent: menu.move_to_trash, params: {{item_hint: "Margherita Pizza"}}
- "Trash the discontinued soup" → intent: menu.move_to_trash, params: {{item_hint: "discontinued soup"}}
- "Restore the Margherita Pizza from trash" → intent: menu.restore_item, params: {{item_hint: "Margherita Pizza"}}
- "Permanently delete the Margherita Pizza" → intent: menu.permanently_delete_item, params: {{item_hint: "Margherita Pizza"}}
- "הגדל את כל מחירי הפסטה ב-10%" → intent: menu.bulk_price_change, params: {{category_hint: "פסטה", change_pct: 10}}
- "Send burgers to the kitchen printer" → intent: printer.route, params: {{item_hint: "burger", printer_hint: "kitchen"}}
- "Route all bar tickets to the kitchen printer instead" → intent: printer.route,
  params: {{category_hint: "Bar", printer_hint: "kitchen", replace_existing: true}}
- "Reorganize my menu into Food and Drinks main sections" → intent: menu.reorganize_categories,
  params: {{new_top_categories: ["Food", "Drinks"]}}
- "Move Cola and Lemonade into the Soft Drinks category" → intent: menu.move_items_to_category,
  params: {{item_hints: ["Cola", "Lemonade"], category_hint: "Soft Drinks"}}
- "What were my best-selling items last week?" → intent: report.query,
  params: {{report_type: "sales", group_by: "item", start: "<computed date 7 days before today>", end: "<today>"}}
- "Show sales by category for March 1 to March 15" → intent: report.query,
  params: {{report_type: "sales", group_by: "category", start: "2026-03-01", end: "2026-03-15"}}
- "Who sold the most burgers this month?" → intent: report.query,
  params: {{report_type: "sales_by_server", item_hint: "burger", start: "<first of this month>", end: "<today>"}}
- "List all cancelled orders from yesterday" → intent: report.query,
  params: {{report_type: "closed_orders", status: "cancelled", start: "<yesterday>", end: "<yesterday>"}}

For report.query, "report_type" is one of "sales" (params: group_by = "item"|"category"|"menu", default
"item"), "sales_by_server" (optional item_hint/category_hint to narrow to one item/category), or
"closed_orders" (optional status = "paid"|"cancelled"|"other"). "start"/"end" are always required.
"""

MENU_REORG_SYSTEM_PROMPT = """You help reorganize a restaurant's menu categories into new top-level sections.

New top-level categories: {new_top_categories}
Existing categories that need to be assigned to one of the new top-level categories: {existing_categories}

Assign every existing category to exactly one of the new top-level categories, based on what best fits its name
(e.g. a "Cocktails" category fits under a "Drinks" top-level category).

Return ONLY valid JSON in this exact format:
{{"assignments": {{"<existing category name>": "<new top-level category name>", ...}}}}
"""

MENU_IMPORT_SYSTEM_PROMPT = """You are a menu-import assistant for SmartServe, a restaurant POS system.
You are shown a photo, screenshot, PDF, or text/spreadsheet export of a restaurant's menu (English or Hebrew).

Extract every distinct menu item you can find: name, an optional short description, and its price.
For each item, suggest:
- "category": a short category name (use one of the business's EXISTING categories below when it clearly fits,
  otherwise propose a new, sensible category name)
- "printerTypes": an array of printer types this item's tickets should print to — each one of "kitchen",
  "receipt", "label". Most items need to print to MORE THAN ONE printer at once (e.g. a burger prints a ticket
  to the kitchen printer AND a copy to the receipt printer); include every printer type that makes sense, not
  just one. Use an empty array only if you are not confident. Pick based on the business's EXISTING printers below.

This business's existing categories: {categories}
This business's existing printers (name/type): {printers}

Return ONLY valid JSON, no markdown fences, in exactly this format:
{{
  "items": [
    {{"name": "...", "nameHe": null, "description": null, "price": 42.0, "currency": "ILS",
      "category": "...", "printerTypes": ["kitchen", "receipt"]}}
  ],
  "message": "<a short reply to the user, in the language they used>",
  "needsClarification": <true|false>
}}

Set "needsClarification" to true and use "message" to ask a specific, single follow-up question when: prices are
missing or illegible, a group of items has no obvious category, or printer routing for an item is genuinely
ambiguous between two existing printers of the same type. Otherwise set it to false and put a brief summary
(e.g. item count and categories found) in "message". Keep conversing with the user turn-by-turn until every item
has a clear category and, where possible, printer assignments — incorporate their replies to refine "items".
"""
