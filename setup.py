import asyncio
from playwright.async_api import async_playwright
import config


async def main():
    print("Opening browser for one-time login. Log in to YouTube, then close the browser window.")

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=config.BROWSER_PROFILE_DIR,
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        await page.goto("https://www.youtube.com")
        await page.wait_for_event("close", timeout=0)
        await browser.close()

    print("Login saved. Run `python main.py` to start the agent.")


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()
