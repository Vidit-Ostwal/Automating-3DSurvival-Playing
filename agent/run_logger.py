import json
from datetime import datetime
from pathlib import Path

OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"


class RunLogger:
    def __init__(self):
        run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
        self.run_dir = OUTPUTS_DIR / run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

        self._data = {
            "run_id": run_id,
            "started_at": datetime.now().isoformat(),
            "cycles": [],
        }
        self._flush()
        print(f"[RUN] Logging to {self.run_dir}")

    def log_cycle(
        self,
        cycle: int,
        goal_maker: dict,
        interpretation: str,
        reasoning: str,
        heading: str,
        memory_update: dict,
        plan: list[dict],
        before_screenshot: bytes,
        after_screenshot: bytes,
        duration_seconds: float,
    ):
        before_name = f"cycle_{cycle:04d}_before.png"
        after_name = f"cycle_{cycle:04d}_after.png"
        (self.run_dir / before_name).write_bytes(before_screenshot)
        (self.run_dir / after_name).write_bytes(after_screenshot)

        self._data["cycles"].append({
            "cycle": cycle,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "goal_maker": {
                "goal": goal_maker.get("goal", ""),
                "goal_progress": goal_maker.get("goal_progress", ""),
                "inventory": goal_maker.get("inventory", ""),
                "heading": goal_maker.get("heading", ""),
                "reasoning": goal_maker.get("reasoning", ""),
            },
            "interpretation": interpretation,
            "heading": heading,
            "reasoning": reasoning,
            "memory_update": memory_update,
            "plan": plan,
            "before_screenshot": before_name,
            "after_screenshot": after_name,
            "duration_seconds": round(duration_seconds, 2),
        })
        self._flush()

    def _flush(self):
        (self.run_dir / "run.json").write_text(
            json.dumps(self._data, indent=2), encoding="utf-8"
        )
