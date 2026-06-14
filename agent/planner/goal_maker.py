import json

from agent.planner.helpers import (
    call_vision_llm,
    create_llm_client,
    extract_tag,
    log_response_warnings,
    vision_user_content,
)

GOAL_SYSTEM_PROMPT = """You are the goal-setting brain for an autonomous Survival 3D agent on YouTube Playables.
You receive a screenshot, your accumulated memory, and your last 5 goal+reasoning+heading responses.
Your job is to read the game UI, understand what is required vs what we already have, and give a direction hint so the movement planner can reach the goal in fewer moves.

Read the UI carefully every cycle:
- PRIMARY goal panel (left side): the active task text and its progress counter (e.g. "Collect some wood 0/5" means 0 collected, 5 required).
- Inventory (top-right corner): item icons and counts the player is currently carrying.

Before choosing a heading, compare goal requirements against inventory:
- If we are short on a resource, head toward the nearest source of the missing quantity.
- If we already have enough for the current step, head toward where that resource is used next (e.g. crafting machine).
- State clearly how much we have, how much is required, and how many more are still needed.

Use memory for game mechanics, discoveries, failed strategies, and area knowledge — let it inform your heading without overriding the PRIMARY goal shown in the UI.
Always anchor your heading to the player's current position in the screenshot — the player character is your reference point.
For every heading, pick the closest relevant target from where the player is standing right now. Do not send the player toward a distant object if a nearer one satisfies the same goal.
Estimate relative distance from the player: choose the compass direction that closes the gap to the nearest target in the fewest moves.
Do not change the goal or direction arbitrarily — continue the current plan unless the screenshot shows real progress or a clear reason to pivot.
When the goal is unchanged, keep the same heading as your previous response unless the player has moved closer to a different target or needs to correct course.
Pick the shortest sensible route from the player's current tile: state which compass direction moves toward the nearest target fastest, and mention any positioning rule (e.g. approach resources from SOUTH, then move NORTH into them).
Resources are collected by proximity. Dense vegetation blocks movement — uncleared vegetation must be cleared or routed around.
Review your previous headings before responding — stay consistent unless progress or the scene clearly requires a change.

Respond in EXACTLY this format — no extra text before or after:
<goal>
PRIMARY: [copy the exact goal text visible in the game UI]
</goal>
<goal_progress>
Active goal resource and progress as shown in the UI, e.g. wood: 2/5 (3 more needed)
</goal_progress>
<inventory>
Items visible in the top-right inventory with counts, e.g. wood: 0, stone: 0, scissors: 0. Use "none" if empty.
</inventory>
<heading>
One word or hyphenated compass direction from the player's current position toward the nearest relevant target: NORTH, SOUTH, EAST, WEST, NORTH-EAST, NORTH-WEST, SOUTH-EAST, or SOUTH-WEST.
</heading>
<reasoning>
Why this is the right goal right now. State what the goal requires, what we hold in inventory, and how many more are needed. Name the nearest target relative to the player and explain why your heading is the shortest path from the player's current position. Reference your previous heading if you are keeping or changing it.
</reasoning>"""

GOAL_HISTORY_MAX = 5


def format_goal_history(history: list[dict]) -> str:
    if not history:
        return "None (first cycle)"
    lines = []
    for i, entry in enumerate(history[-GOAL_HISTORY_MAX:], start=1):
        lines.append(f"--- Previous goal {i} ---")
        lines.append(f"Goal:\n{entry.get('goal', '')}")
        lines.append(f"Progress:\n{entry.get('goal_progress', '')}")
        lines.append(f"Inventory:\n{entry.get('inventory', '')}")
        lines.append(f"Heading:\n{entry.get('heading', '')}")
        lines.append(f"Reasoning:\n{entry.get('reasoning', '')}")
    return "\n".join(lines)


def build_goal_user_content(screenshot: bytes, history: list[dict], memory: dict) -> list[dict]:
    footer = (
        f"Your previous {GOAL_HISTORY_MAX} goals, headings, and reasoning:\n"
        f"{format_goal_history(history)}\n\n"
        f"Current memory:\n{json.dumps(memory, indent=2)}"
    )
    return vision_user_content(screenshot, footer)


def parse_goal_response(raw: str) -> dict:
    return {
        "goal": extract_tag("goal", raw),
        "goal_progress": extract_tag("goal_progress", raw),
        "inventory": extract_tag("inventory", raw),
        "heading": extract_tag("heading", raw).strip().upper(),
        "reasoning": extract_tag("reasoning", raw),
    }


class GoalMakerLLM:
    def __init__(self):
        self._provider = "openai"
        self._client, self._model = create_llm_client(self._provider)
        self._history: list[dict] = []

    async def make_goal(self, screenshot: bytes, memory: dict) -> dict:
        user_content = build_goal_user_content(screenshot, self._history, memory)
        raw, finish_reason = await call_vision_llm(
            self._client,
            self._model,
            GOAL_SYSTEM_PROMPT,
            user_content,
            provider=self._provider,
        )
        log_response_warnings(raw, finish_reason, expect="goal")

        result = parse_goal_response(raw)
        self._history.append(result)
        self._history = self._history[-GOAL_HISTORY_MAX:]
        return result
