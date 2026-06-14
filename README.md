# Automating 3D Survival Playing

An autonomous vision-language agent that plays **Survival 3D** on [YouTube Playables](https://www.youtube.com/playables). It watches the game through screenshots, sets goals from the UI, plans movement, and executes keyboard actions in a loop.

**Demo:** [Watch `Demovideo_1.mp4`](https://github.com/Vidit-Ostwal/Automating-3DSurvival-Playing/blob/main/demovideo/Demovideo_1.mp4)

## How it works

Each cycle:

1. **Screenshot** — capture the current game state
2. **GoalMaker** — read the primary goal, progress counter, and top-right inventory; pick a compass heading toward the nearest target
3. **Planner** — turn that goal into 1–2 concrete moves (NORTH/SOUTH/EAST/WEST)
4. **Executor** — send key presses to the browser
5. **Memory** — persist discoveries, mechanics, and failed strategies for later cycles

```
Screenshot → GoalMaker → Planner → Executor → Memory
                ↑                      ↓
                └──────── next cycle ──┘
```

### Architecture

| Component | Role |
|-----------|------|
| `GoalMakerLLM` | Reads game UI (goal, progress, inventory) and suggests the fastest heading |
| `PlannerLLM` | Follows GoalMaker and outputs movement steps |
| `MemoryManager` | JSON store of game mechanics, discoveries, and failed strategies |
| `RunLogger` | Saves per-cycle screenshots and `run.json` under `outputs/` |

LLM provider is set per component in code (`openai` or `ollama` via `create_llm_client()` in `agent/planner/helpers.py`).

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Google Chrome (Playwright uses the Chrome channel)
- OpenAI API key and/or a local Ollama vision model

## Setup

```bash
git clone https://github.com/Vidit-Ostwal/Automating-3DSurvival-Playing.git
cd Automating-3DSurvival-Playing

uv sync
uv run playwright install chrome
cp .env.example .env
```

Edit `.env` with your API keys and model settings:

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
MODEL_NAME=llama3.2-vision
OLLAMA_BASE_URL=http://localhost:11434/v1
GAME_URL=https://www.youtube.com/playables/...
```

### One-time YouTube login

The agent reuses a persistent browser profile so you stay logged in:

```bash
uv run setup-browser
```

Log in to YouTube in the window that opens, then close it.

## Run

```bash
uv run python main.py
```

The agent waits **55 seconds** for the game to load (prints `Starting in 5 seconds...` at the end), then begins the autonomous loop. Press `Ctrl+C` to stop.

## Project layout

```
agent/
  browser.py        # Playwright browser + screenshots
  loop.py           # Main agent cycle
  executor.py       # Keyboard action execution
  run_logger.py     # Run logs and screenshots
  planner/
    goal_maker.py   # Goal + heading from UI
    planner_llm.py  # Movement planning
    helpers.py      # LLM client + vision helpers
memory/
  memory.json       # Persistent game knowledge
outputs/            # Per-run logs (gitignored)
demovideo/          # Demo recordings (Demovideo_1.mp4)
```

## Demo

The agent playing Survival 3D autonomously — reading goals from the UI, planning movement, and collecting resources.

**[Watch Demovideo_1.mp4 on GitHub](https://github.com/Vidit-Ostwal/Automating-3DSurvival-Playing/blob/main/demovideo/Demovideo_1.mp4)**

After cloning, you can also open `demovideo/Demovideo_1.mp4` locally.

## License

MIT (or your preferred license — update as needed)
