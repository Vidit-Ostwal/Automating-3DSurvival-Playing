from playwright.async_api import async_playwright, Browser, Page
import config


class BrowserManager:
    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None
        self._page: Page | None = None

    async def start(self, headless: bool = False):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=config.BROWSER_PROFILE_DIR,
            headless=headless,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        self._page = self._browser.pages[0] if self._browser.pages else await self._browser.new_page()

    async def navigate(self, url: str):
        await self._page.goto(url, wait_until="networkidle")

    async def screenshot(self) -> bytes:
        # Game is inside an iframe — find the largest one (the game) and clip to it
        iframes = await self._page.query_selector_all("iframe")
        largest_box = None
        largest_area = 0
        for el in iframes:
            box = await el.bounding_box()
            if box:
                area = box["width"] * box["height"]
                if area > largest_area:
                    largest_area = area
                    largest_box = box

        if largest_box:
            return await self._page.screenshot(clip=largest_box, type="png")
        return await self._page.screenshot(full_page=False, type="png")

    @property
    def page(self) -> Page:
        return self._page

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
