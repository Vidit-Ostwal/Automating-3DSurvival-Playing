import asyncio
from agent.browser import BrowserManager
from agent.planner import GoalMakerLLM, PlannerLLM
from agent.executor import Executor
from agent.loop import AgentLoop
from memory.memory import MemoryManager
import config


async def main():
    browser = BrowserManager()
    goal_maker = GoalMakerLLM()
    planner = PlannerLLM()
    executor = Executor(browser)
    memory = MemoryManager()
    loop = AgentLoop(browser, goal_maker, planner, executor, memory)

    await browser.start(headless=False)
    await browser.navigate(config.GAME_URL)

    print("Waiting 55s for game to load...")
    await asyncio.sleep(50)
    print("Starting in 5 seconds...")
    await asyncio.sleep(5)

    try:
        await loop.run()
    except KeyboardInterrupt:
        pass
    finally:
        await browser.close()
        print("\nAgent stopped.")


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()
