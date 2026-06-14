import time
import json
from dataclasses import dataclass
from datetime import datetime
from agent.browser import BrowserManager
from agent.planner import GoalMakerLLM, PlannerLLM
from agent.executor import Executor
from agent.run_logger import RunLogger
from memory.memory import MemoryManager


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


@dataclass
class CyclePlan:
    interpretation: str
    goal: str
    goal_progress: str
    goal_inventory: str
    goal_heading: str
    goal_reasoning: str
    reasoning: str
    heading: str
    memory_update: dict
    plan: list[dict]
    plan_summary: str


def _parse_plan_result(result: dict, goal_result: dict) -> CyclePlan:
    plan = result.get("plan", [{"direction": "NORTH", "steps": 1}])
    return CyclePlan(
        interpretation=result.get("interpretation", ""),
        goal=goal_result.get("goal", ""),
        goal_progress=goal_result.get("goal_progress", ""),
        goal_inventory=goal_result.get("inventory", ""),
        goal_heading=goal_result.get("heading", ""),
        goal_reasoning=goal_result.get("reasoning", ""),
        reasoning=result.get("reasoning", ""),
        heading=result.get("heading", ""),
        memory_update=result.get("memory_update", {}),
        plan=plan,
        plan_summary="  ".join(f"{s.get('direction')} ×{s.get('steps')}" for s in plan),
    )


class AgentLoop:
    def __init__(
        self,
        browser: BrowserManager,
        goal_maker: GoalMakerLLM,
        planner: PlannerLLM,
        executor: Executor,
        memory: MemoryManager,
    ):
        self._browser = browser
        self._goal_maker = goal_maker
        self._planner = planner
        self._executor = executor
        self._memory = memory

    def _begin_cycle(self, cycle: int):
        print(f"\n{'═' * 50}")
        print(f"  CYCLE {cycle}  [{_ts()}]")
        print(f"{'═' * 50}")

    async def _screenshot(self, label: str) -> bytes:
        image = await self._browser.screenshot()
        print(f"[SCREENSHOT] Captured {label}")
        return image

    async def _make_goal(self, screenshot: bytes, cycle_start: float) -> dict:
        print("[GOAL LLM] Calling goal maker... ", end="", flush=True)
        result = await self._goal_maker.make_goal(screenshot, self._memory.load())
        print(f"done in {time.time() - cycle_start:.1f}s")
        self._report_goal(result)
        return result

    def _report_goal(self, goal_result: dict):
        print(f"\n[GOAL MAKER]")
        print(f"  Goal: {goal_result.get('goal', '')}")
        print(f"  Progress: {goal_result.get('goal_progress', '')}")
        print(f"  Inventory: {goal_result.get('inventory', '')}")
        print(f"  Heading: {goal_result.get('heading', '')}")
        print(f"  Reasoning: {goal_result.get('reasoning', '')}\n")

    async def _plan(
        self,
        screenshot: bytes,
        last_actions: list[dict],
        goal_result: dict,
        cycle_start: float,
    ) -> CyclePlan:
        print("[LLM] Calling planner... ", end="", flush=True)
        result = await self._planner.plan(
            screenshot,
            last_actions,
            self._memory.load(),
            goal_result,
        )
        print(f"done in {time.time() - cycle_start:.1f}s")
        return _parse_plan_result(result, goal_result)

    def _report_plan(self, cycle_plan: CyclePlan):
        print(f"[INTERPRET]\n  {cycle_plan.interpretation}\n")
        print(f"[PLANNER HEADING] ► {cycle_plan.heading}")
        print(f"[PLANNER REASONING]\n  {cycle_plan.reasoning}\n")

    def _update_memory(self, cycle_plan: CyclePlan):
        if cycle_plan.memory_update:
            print(f"[MEMORY UPDATE]\n  {json.dumps(cycle_plan.memory_update, indent=2)}\n")
            self._memory.apply_update(cycle_plan.memory_update)
        else:
            print("[MEMORY UPDATE] none\n")

    async def _execute(self, cycle_plan: CyclePlan):
        print(f"[PLAN] {cycle_plan.plan_summary}")
        print(f"[EXECUTE] {len(cycle_plan.plan)} move(s): {cycle_plan.plan_summary}")
        await self._executor.execute(cycle_plan.plan)

    def _save_cycle_log(
        self,
        run_logger: RunLogger,
        cycle: int,
        cycle_plan: CyclePlan,
        screenshot: bytes,
        after: bytes,
        cycle_start: float,
    ):
        elapsed = time.time() - cycle_start
        run_logger.log_cycle(
            cycle=cycle,
            goal_maker={
                "goal": cycle_plan.goal,
                "goal_progress": cycle_plan.goal_progress,
                "inventory": cycle_plan.goal_inventory,
                "heading": cycle_plan.goal_heading,
                "reasoning": cycle_plan.goal_reasoning,
            },
            interpretation=cycle_plan.interpretation,
            reasoning=cycle_plan.reasoning,
            heading=cycle_plan.heading,
            memory_update=cycle_plan.memory_update,
            plan=cycle_plan.plan,
            before_screenshot=screenshot,
            after_screenshot=after,
            duration_seconds=elapsed,
        )
        print(f"[RUN LOG] cycle_{cycle:04d} saved → {run_logger.run_dir.name}/")
        print(f"[CYCLE DONE] {elapsed:.1f}s total")

    async def run(self):
        run_logger = RunLogger()
        cycle = 0
        last_actions: list[dict] = []

        while True:
            cycle += 1
            cycle_start = time.time()

            self._begin_cycle(cycle)
            screenshot = await self._screenshot("current state")
            goal_result = await self._make_goal(screenshot, cycle_start)
            cycle_plan = await self._plan(
                screenshot,
                last_actions,
                goal_result,
                cycle_start,
            )
            self._report_plan(cycle_plan)
            self._update_memory(cycle_plan)
            await self._execute(cycle_plan)
            after = await self._screenshot("after state")
            self._save_cycle_log(run_logger, cycle, cycle_plan, screenshot, after, cycle_start)

            last_actions = cycle_plan.plan
