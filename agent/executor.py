import asyncio
from playwright.async_api import ElementHandle
from agent.browser import BrowserManager
import config

# Cardinal directions → single key
# Diagonal directions → two keys alternated each step
KEY_MAP: dict[str, list[str]] = {
    "NORTH":      ["ArrowUp"],
    "SOUTH":      ["ArrowDown"],
    "EAST":       ["ArrowRight"],
    "WEST":       ["ArrowLeft"],
    "NORTH-EAST": ["ArrowUp", "ArrowRight"],
    "NORTH-WEST": ["ArrowUp", "ArrowLeft"],
    "SOUTH-EAST": ["ArrowDown", "ArrowRight"],
    "SOUTH-WEST": ["ArrowDown", "ArrowLeft"],
}

# How long to hold each key down (seconds)
KEY_HOLD_SECONDS = 0.4


class Executor:
    def __init__(self, browser: BrowserManager):
        self._browser = browser
        self._canvas: ElementHandle | None = None

    async def _get_canvas(self) -> ElementHandle | None:
        page = self._browser.page
        for frame in page.frames:
            if frame == page.main_frame:
                continue
            canvas = await frame.query_selector("canvas")
            if canvas:
                print(f"[EXECUTOR] Found canvas in frame: {frame.url[:60]}")
                return canvas
        # Fallback: check main frame too
        canvas = await page.query_selector("canvas")
        if canvas:
            print("[EXECUTOR] Found canvas in main frame")
        else:
            print("[EXECUTOR] WARNING: canvas not found in any frame")
        return canvas

    async def _press_key(self, key: str):
        """Hold key down for KEY_HOLD_SECONDS then release — gives the game time to register movement."""
        page = self._browser.page
        await page.keyboard.down(key)
        await asyncio.sleep(KEY_HOLD_SECONDS)
        await page.keyboard.up(key)

    async def execute(self, actions: list[str]):
        if self._canvas is None:
            self._canvas = await self._get_canvas()

        if self._canvas is None:
            print("[EXECUTOR] No canvas found — skipping actions")
            return

        # Click canvas to ensure it has keyboard focus
        try:
            await self._canvas.click()
            print("[EXECUTOR] Canvas clicked (focused)")
        except Exception as e:
            print(f"[EXECUTOR] Canvas click failed ({e}), re-acquiring...")
            self._canvas = await self._get_canvas()
            if self._canvas:
                await self._canvas.click()

        for step in actions:
            direction = step.get("direction", "WAIT").upper()
            steps = max(1, int(step.get("steps", 1)))
            keys = KEY_MAP.get(direction)

            for i in range(steps):
                if direction == "WAIT" or keys is None:
                    await asyncio.sleep(config.ACTION_DELAY_SECONDS)
                else:
                    # For diagonals, alternate between the two keys each step
                    key = keys[i % len(keys)]
                    await self._press_key(key)
                    await asyncio.sleep(config.ACTION_DELAY_SECONDS - KEY_HOLD_SECONDS)

            print(f"[EXECUTOR] {direction} × {steps} done")
