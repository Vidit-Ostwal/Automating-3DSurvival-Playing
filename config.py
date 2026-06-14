from dotenv import load_dotenv
import os

load_dotenv()

MODEL_NAME: str = os.getenv("MODEL_NAME", "llama3.2-vision")
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
GAME_URL: str = os.getenv("GAME_URL", "https://www.youtube.com/playables/UgkxBpf7p6DuWrVah-IadvyGG2-p2t73Kosy")
BROWSER_PROFILE_DIR: str = os.getenv("BROWSER_PROFILE_DIR", "./browser_profile")
ACTION_DELAY_SECONDS: float = float(os.getenv("ACTION_DELAY_SECONDS", "1.0"))
ACTION_MULTIPLIER: int = int(os.getenv("ACTION_MULTIPLIER", "5"))
PLAN_ACTIONS_COUNT: int = int(os.getenv("PLAN_ACTIONS_COUNT", "4"))
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "8192"))
THINKING_ENABLED: bool = os.getenv("THINKING_ENABLED", "false").lower() == "true"
