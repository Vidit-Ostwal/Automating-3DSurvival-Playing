import json
from pathlib import Path

MEMORY_FILE = Path(__file__).parent / "memory.json"

_SEED: dict = {
    "dangers": [],
    "discoveries": [],
    "tool_recipes": [],
    "area_knowledge": [],
    "failed_strategies": [],
    "health_management": [],
}


class MemoryManager:
    def load(self) -> dict:
        if not MEMORY_FILE.exists():
            return dict(_SEED)
        with MEMORY_FILE.open() as f:
            return json.load(f)

    def apply_update(self, patch: dict):
        result = self.load()
        stack = [(result, patch)]
        while stack:
            base, update = stack.pop()
            for key, value in update.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    stack.append((base[key], value))
                else:
                    base[key] = value

        with MEMORY_FILE.open("w") as f:
            json.dump(result, f, indent=2)
