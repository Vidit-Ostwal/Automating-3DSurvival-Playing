import json

from agent.planner.helpers import (
    call_vision_llm,
    create_llm_client,
    extract_tag,
    log_response_warnings,
    vision_user_content,
)

_RESPONSE_FORMAT = """
Respond in EXACTLY this format — no extra text before or after:
<interpretation>
What you observe in the screenshot relative to the active goal: current game state, whether your previous actions advanced the goal, what you learned about how to reach it.
</interpretation>
<reasoning>
Start from the active goal, GoalMaker heading hint, and GoalMaker reasoning — restate what you are trying to achieve this cycle. Then identify where the target is relative to the player. Align your heading and moves with GoalMaker's heading hint unless the screenshot clearly requires a correction. Explain how these moves advance the active goal in fewer steps and what state you expect to reach.
</reasoning>
<heading>
One word or hyphenated compass direction the player needs to travel overall: NORTH, SOUTH, EAST, WEST, NORTH-EAST, NORTH-WEST, SOUTH-EAST, or SOUTH-WEST.
</heading>
<memory_update>
{"key": "value"}  ← valid JSON to deep-merge into memory. Use {} if nothing new.
</memory_update>
<plan>
[{"direction": "NORTH", "steps": 3}, {"direction": "EAST", "steps": 2}]
← Exactly 1 or 2 move objects. RULE: move 1 must be NORTH or SOUTH, move 2 must be EAST or WEST.
Never pair NORTH+SOUTH or EAST+WEST — they cancel each other out.
direction is one of: NORTH, SOUTH, EAST, WEST. steps is 1-10.
</plan>"""

SYSTEM_PROMPT = f"""You are the movement planner for an autonomous Survival 3D agent on YouTube Playables.
GoalMaker decides WHAT to pursue — you decide HOW to get there. The active goal and GoalMaker reasoning are your top priority every cycle.
Your job is to read the screenshot, follow GoalMaker's direction, and output concrete moves that make measurable progress toward the active goal.
Your only controls are: UP, DOWN, LEFT, RIGHT, WAIT.
Resources are collected by proximity — walk near trees for wood, near rocks for stone.
IMPORTANT: To collect any resource (wood, stone, etc.), you must approach it from the SOUTH side and move NORTH into it. Position yourself south of the target, then move north — collection triggers as you enter from below.
Crafting is automatic — walk to the crafting machine with required items in inventory.
You receive one screenshot, the active goal and reasoning from GoalMaker, a text description of what you did last cycle, and your accumulated memory.
GoalMaker outranks memory and your own instincts — every plan must directly serve the active goal, GoalMaker reasoning, and GoalMaker heading hint. Do not invent a different objective or heading.
Follow GoalMaker's heading hint as your primary travel direction — pick moves that advance along that heading in the fewest steps.
Use memory only to avoid repeating failed approaches while still pursuing the same goal.
If the screenshot shows no progress after your last actions, you are stuck — try a different route or heading, but stay aligned with the active goal unless GoalMaker reasoning says to pivot.
Never repeat a strategy listed in failed_strategies in your memory.
Only use WAIT if you can see active progress on screen — a counter increasing, an animation playing, an item being collected. If nothing is visibly changing, WAIT has no value — move instead.
Plan rule: move 1 is always NORTH or SOUTH, move 2 is always EAST or WEST. Never use NORTH+SOUTH or EAST+WEST together — they cancel out and waste steps.
{_RESPONSE_FORMAT}"""

_NS = frozenset({"NORTH", "SOUTH"})
_EW = frozenset({"EAST", "WEST"})
_OPPOSITES = frozenset({
    ("NORTH", "SOUTH"), ("SOUTH", "NORTH"),
    ("EAST", "WEST"), ("WEST", "EAST"),
})

DEFAULT_PLAN = [{"direction": "NORTH", "steps": 1}]


def format_last_actions(actions: list[dict]) -> str:
    if not actions:
        return "None (first cycle)"
    return ", ".join(
        f"{a.get('direction', 'WAIT')} ×{a.get('steps', 1)}" for a in actions
    )


def build_user_content(
    screenshot: bytes,
    last_actions: list[dict],
    memory: dict,
    goal_result: dict,
) -> list[dict]:
    footer = (
        "=== GOALMAKER (highest priority — plan must advance this) ===\n"
        f"Active goal:\n{goal_result.get('goal', '')}\n\n"
        f"Goal progress:\n{goal_result.get('goal_progress', '')}\n\n"
        f"Current inventory:\n{goal_result.get('inventory', '')}\n\n"
        f"GoalMaker heading hint (follow this direction):\n{goal_result.get('heading', '')}\n\n"
        f"GoalMaker reasoning:\n{goal_result.get('reasoning', '')}\n\n"
        "=== CONTEXT (secondary) ===\n"
        f"Previous actions: {format_last_actions(last_actions)}\n"
        f"Current memory: {json.dumps(memory, indent=2)}"
    )
    return vision_user_content(screenshot, footer)


def sanitize_plan(plan: list[dict]) -> list[dict]:
    if not plan:
        return DEFAULT_PLAN

    plan = plan[:2]
    if len(plan) < 2:
        return plan

    d1 = plan[0]["direction"].upper()
    d2 = plan[1]["direction"].upper()

    if (d1, d2) in _OPPOSITES:
        return [plan[0]]
    if d1 in _EW and d2 in _NS:
        return [plan[1], plan[0]]
    if (d1 in _EW and d2 in _EW) or (d1 in _NS and d2 in _NS):
        return [plan[0]]

    return plan


def parse_plan(plan_text: str) -> list[dict]:
    try:
        plan = json.loads(plan_text)
        if not isinstance(plan, list) or not plan:
            raise ValueError
        for step in plan:
            if not isinstance(step, dict) or "direction" not in step or "steps" not in step:
                raise ValueError
        return sanitize_plan(plan)
    except (json.JSONDecodeError, ValueError):
        return DEFAULT_PLAN


def parse_memory_update(memory_update_text: str) -> dict:
    try:
        return json.loads(memory_update_text)
    except (json.JSONDecodeError, ValueError):
        return {}


def parse_llm_response(raw: str) -> dict:
    return {
        "interpretation": extract_tag("interpretation", raw),
        "reasoning": extract_tag("reasoning", raw),
        "heading": extract_tag("heading", raw).strip().upper(),
        "memory_update": parse_memory_update(extract_tag("memory_update", raw)),
        "plan": parse_plan(extract_tag("plan", raw)),
    }


class PlannerLLM:
    def __init__(self):
        self._provider = "openai"
        self._client, self._model = create_llm_client(self._provider)

    async def plan(
        self,
        screenshot: bytes,
        last_actions: list[dict],
        memory: dict,
        goal_result: dict,
    ) -> dict:
        user_content = build_user_content(
            screenshot, last_actions, memory, goal_result
        )
        raw, finish_reason = await call_vision_llm(
            self._client,
            self._model,
            SYSTEM_PROMPT,
            user_content,
            provider=self._provider,
        )
        log_response_warnings(raw, finish_reason, expect="interpretation")

        return parse_llm_response(raw)
