# Pepper — Hermes Agent Scheduler Plugin

**Pepper's scheduling brain** — an [MCP](https://modelcontextprotocol.io) server backed by a SQLite database that gives the Pepper agent (built on the **Hermes** framework, reached via Telegram) a dedicated "region of mind" for time. It captures schedule-relevant items, ranks them by priority, re-flows the day when reality slips, and learns the user's time habits.

## Design principle: *the algorithm computes; the LLM only chooses*

A deterministic **reflex** does the constant, exact work — classification, priority scoring, cascade re-flow, learning. **Deliberate reasoning** (the LLM, referred to as *Hermes* in the specs) is spent only at genuine judgment points.

At an LLM-judgment step — disambiguating an uncertain classification, or resolving a cascade `escalate`/`impossible` — the reflex does **not** silently auto-decide. It returns a structured payload (the feasible `options`, or a `conflicts` report) describing the situation. Hermes reasons over that payload, clarifies with the user if needed, and enacts the choice through ordinary tools.

## Requirements

- **Python 3.11+**
- The first real classification/embedding call lazily pulls `fastembed` + `onnxruntime` (heavy). These are never imported by the test suite.
- **The embedding model is *not* vendored in the repo** — `fastembed` downloads `BAAI/bge-small-en-v1.5` from the Hugging Face Hub on first use. See [Embedding model](#embedding-model) below.

## Setup

### Instant setup (recommended)

```bash
git clone git@github.com:IanTheMitten/Pepper_Hermes_Agent_Scheduler.git
cd Pepper_Hermes_Agent_Scheduler
./setup.sh
```

`setup.sh` checks Python 3.11+, creates `.venv`, installs Pepper, runs a smoke test
against a throwaway DB, and prints the exact MCP config block to paste into your
agent — plug and play. Flags: `--dev` adds pytest/ruff; `--warm` pre-downloads the
embedding model (~130 MB) so the first classification is instant. Windows: use the
manual steps below (the script is bash, macOS/Linux).

### Manual setup

```bash
# 1. Clone the repo
git clone git@github.com:IanTheMitten/Pepper_Hermes_Agent_Scheduler.git
cd Pepper_Hermes_Agent_Scheduler
# (HTTPS instead of SSH: git clone https://github.com/IanTheMitten/Pepper_Hermes_Agent_Scheduler.git)

# 2. Create & activate a virtual environment (Python 3.11+)
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install (editable, with dev extras)
pip install -e ".[dev]"

# 4. Run the MCP server — bootstrap() migrates the DB on startup
python -m pepper

# Override the SQLite path (default: ~/.pepper/pepper.db)
PEPPER_DB_PATH=/tmp/x.db python -m pepper
```

> **Dependencies.** `pyproject.toml` is the canonical source. `requirements.txt`
> (runtime) and `requirements-dev.txt` (runtime + test/lint tooling) mirror it for
> environments that prefer `pip install -r`. Either way you still need the package
> itself on the path — `pip install -e .` (above) handles both at once.
>
> ```bash
> pip install -r requirements-dev.txt   # deps only; pair with `pip install -e .`
> ```

### Embedding model

Pepper classifies captured items by embedding their titles and matching against learned
type centroids. The embedder (`src/pepper/ml/embedder.py`) uses **`fastembed`** with the
**`BAAI/bge-small-en-v1.5`** model.

**The model weights are not in the repo.** `pip install` only installs the `fastembed`
*library*; the model artifact (~130 MB of ONNX weights + tokenizer) is fetched from the
Hugging Face Hub the **first time an embedding is actually computed** — i.e. the first
real classification where at least one learned type already exists. It is then cached
locally (default: fastembed's cache directory, e.g. `~/.cache/fastembed/`), so subsequent
runs need no network.

Nothing extra is required if the machine has internet on first use — it just works. The
notes below matter for **offline or air-gapped** deployments and for avoiding a slow
first request in production.

```bash
# Warm the cache ahead of time (downloads + caches the model now, while online).
# Run once after install; safe to re-run (no-op if already cached).
python -c "from pepper.ml.embedder import get_embed_fn; get_embed_fn()('warmup')"
```

```python
# Pin the cache location explicitly (e.g. to bake the model into a Docker image
# or ship it to an offline host). fastembed reads this when it constructs the model.
from fastembed import TextEmbedding
TextEmbedding(model_name="BAAI/bge-small-en-v1.5", cache_dir="/opt/pepper/models")
```

**Offline / air-gapped setup:** warm the cache on a machine *with* network (snippet
above), then copy the resulting cache directory to the target host before first use.
Once the weights are present locally, no Hugging Face access is needed at runtime.

> ⚠️ A slow first classification (several seconds + network traffic) is expected and
> normal — that's the one-time model download. It is **not** the same regression as the
> test suite slowing down; tests inject a fake `embed_fn` and must never download anything.

### Development

```bash
python -m pytest -q          # full suite, runs in ~1–3s
ruff check src tests         # lint — must be clean before committing

# Run a single test
python -m pytest tests/test_engine.py::test_infeasible_day_drops_lowest_protection -v
```

ruff config: **E402 is ON** (imports must live at module top), **E501 (line length) is OFF**.

> ⚠️ If the suite jumps from ~1–2s to ~10s+, the embedding model is being loaded unintentionally — a regression. Tests inject a deterministic fake `embed_fn` and must never call `get_embed_fn()`.

## Architecture

Strict layering — dependencies point **downward only**:

| Layer | Responsibility | Rules |
|-------|----------------|-------|
| `domain/` | Frozen dataclasses (`Item`, `Item.from_row`) | **No I/O** |
| `repositories/` | SQL only | Parameterized queries; `conn.commit()` after writes; rows via `sqlite3.Row` |
| `services/` | Orchestration across repos + pure modules | **No raw SQL** |
| `mcp/server.py` | Transport + validation | Returns `{"success", "data", "error"}` via `_ok()`/`_err()` |
| `ml/` `learning/` `priority/` `cascade/` | Pure computation | **No I/O** (the embedder seam is the one exception) |

### The reflex pipelines

- **Capture** — `pepper_add_event`/`pepper_add_task` → `schedule_service` (persist) → `classification_service.classify_and_assign` (embed title → match type centroid → set `type_id`) → `priority_service.recompute_scores` (Rigidity / Protection). The row is re-read so the response carries freshly computed fields.

- **Learning loop** — `pepper_mark_progress` → `learning_service.record_completion` → append an immutable Layer-1 `observations` row → `recompute` rebuilds Layer-2 `type_stats` (EWMA mean/spread/confidence) → update factor-keyed `user_bias`. `learning.bias.estimate_minutes` is the single back-off entry point (confident `type_stats` → seed × personal-bias → fallback). **`pepper_mark_progress` is the only path that writes a learning observation** (requires `actual_minutes > 0`). To drop an item as a deliberate decision use `pepper_cancel_item` (sets status `cancelled`, writes **no** observation) — never abuse `mark_progress` for a cancellation.

- **Cascade re-flow** (`cascade/`, pure) — items → integer-minute `Block`s → `engine.solve` (anchors fragment the day; movable blocks re-placed via the lever ladder **absorb → compress → shift → split → drop** under hard `constraints`, ranked by `cost`, bounded branch-and-bound) → `gate.decide` → one of four actions:
  - `noop` (<2 blocks) and `apply` (single clear best) **mutate** the schedule.
  - `escalate` (close call) and `impossible` (no feasible arrangement without sacrificing a protected/fixed item) **leave the schedule untouched** and return `options` (each `{cost, moves}`) or a `conflicts` report for Hermes to resolve.

  Cascade is invoked **explicitly** (`pepper_resolve_conflict`, `pepper_reschedule`, `pepper_delay_item`) — never auto-fired inside capture.

### Database & migrations

- `db/connection.py` — `get_connection()` sets `row_factory = sqlite3.Row` and `PRAGMA foreign_keys = ON`.
- `db/migrations.py` — `migrate(conn)` applies every `src/pepper/db/migrations/NNN_*.sql` not yet recorded in `schema_migrations`, in sorted filename order. **To add a table, drop in the next `NNN_*.sql` file** — it's auto-discovered, no code change needed. `bootstrap()` runs `migrate()` at startup.
- Migrations to date: `001_core`, `002_classification`, `003_memory`, `004_persons_priority`, `005_cascade`, `006_planner_recurrence`, `007_intelligence`.
- Tests get a fresh migrated DB from the `conn` fixture in `tests/conftest.py`, so any new migration is automatically exercised.

## MCP tools

| Tool | Purpose |
|------|---------|
| `pepper_onboard` | Initialize a user's scheduling context |
| `pepper_add_event` / `pepper_add_task` | Capture a schedule-relevant item (triggers classify + score) |
| `pepper_add_project` | Create a project to group items |
| `pepper_add_recurrence` / `pepper_edit_recurrence` | Define / edit a recurring item |
| `pepper_add_rule` | Add a scheduling rule |
| `pepper_set_objective` | Set a goal/objective |
| `pepper_get_schedule` | Read the current schedule |
| `pepper_briefing` | Proactive day digest: schedule + overlaps, at-risk deadlines, estimate drift, looming unscheduled tasks |
| `pepper_suggest_slot` | Rank a day's free slots for an item by learned time-of-day habit + learned duration (read-only) |
| `pepper_mark_progress` | Record completion (only path that writes a learning observation; `actual_minutes > 0`) |
| `pepper_cancel_item` | Cancel an item (status `cancelled`, no observation) |
| `pepper_set_deadline` | Set/adjust an item deadline |
| `pepper_set_priority_factors` | Set priority factors on an item |
| `pepper_set_item_type` | Override an item's classified type |
| `pepper_reschedule` / `pepper_delay_item` | Trigger cascade re-flow |
| `pepper_resolve_conflict` | Resolve a surfaced `escalate`/`impossible` situation |
| `pepper_resolve_person` | Resolve a person reference |

All tools return the envelope `{"success", "data", "error"}`.

## Adding the skill to the Hermes Agent

`SKILL.md` (in the repo root) is the agent-facing skill that teaches Hermes *when* and *how* to drive Pepper's tools — capture flow, the learning-loop rules, and how to handle the cascade `options`/`conflicts` payloads. Two pieces are needed: the **tools** (this MCP server) and the **skill** (the behavioral doc).

### 1. Register Pepper as an MCP server

The server speaks MCP over stdio (`python -m pepper`). Add it to Hermes's MCP server config so the `pepper_*` tools become available:

```json
{
  "mcpServers": {
    "pepper": {
      "command": "python",
      "args": ["-m", "pepper"],
      "env": { "PEPPER_DB_PATH": "/home/hermes/.pepper/pepper.db" }
    }
  }
}
```

Make sure Pepper is installed in the same environment Hermes launches (`pip install -e .` from this repo, or `pip install .`). `bootstrap()` migrates the DB on first start, so no manual DB setup is required.

### 2. Install the skill

Drop `SKILL.md` where Hermes discovers skills, then let its skill loader pick it up:

```bash
# Example — adjust to your Hermes skills directory
mkdir -p <hermes>/skills/pepper-scheduler
cp SKILL.md <hermes>/skills/pepper-scheduler/SKILL.md
```

The skill's frontmatter (`name: pepper-scheduler`, `description: …`) is what Hermes matches against — it triggers whenever the user mentions anything time-bound (events, tasks, deadlines, "when am I free", "I'm running late", recurrences, how long something took). Once installed, Hermes routes all time/calendar reasoning through Pepper's tools instead of reasoning about the calendar itself.

> The skill references the `pepper_*` tool names directly, so step 1 (the MCP server) must be wired for the skill to be actionable.

### 3. (Optional) Wire the Hermes seams

If you want Pepper to send messages, schedule cron jobs, or read Hermes memory, inject the gateways at startup via `pepper.integration.hermes`:

```python
from pepper.integration import hermes
hermes.set_gateway(my_gateway)   # send(message)
hermes.set_cron(my_cron)         # schedule(job_id, when_iso, payload)
hermes.set_memory(my_memory)     # query(key)
```

These are `Protocol`s with `Fake*` implementations for testing; they're only required for features that use them.

## Conventions & gotchas

- **`(str, Enum)` + `str()` trap** — on Python 3.11+, `str(SomeEnum.member)` yields `"SomeEnum.member"`, not `"member"`, which breaks SQL `CHECK` constraints. Use `item_repo._text(value)` (returns `.value` for Enums) when writing categorical columns. This has bitten the project twice — preserve the `_text()` normalization in `add_item` and `set_factors`.
- **Keep the embedding model out of tests** — `ml/embedder.get_embed_fn()` is cheap; the heavy `fastembed` model loads lazily on first real embed. `ml/classifier.classify` short-circuits to `"new"` when there are no types yet, so capture with an empty type set never loads the model.
- **Error contract** — repositories return `None` (not raise) on missing rows; services validate and raise `ValueError`; MCP tools catch `ValueError` → `_err`. Validate at the boundary.

## Project layout

```
src/pepper/
├── domain/        # frozen dataclasses, no I/O
├── repositories/  # SQL only
├── services/      # orchestration
├── mcp/           # server.py (transport), schemas.py (pydantic)
├── db/            # connection, migrations, migrations/*.sql
├── ml/            # embedder, classifier, vec_math, adaptation
├── learning/      # bias, seeds, estimator
├── priority/      # scores
├── cascade/       # engine, gate, constraints, cost, block
├── planner/       # slots, allocation, projection
├── recurrence/    # expand, materializer
├── persons/ rules/ objectives/ load/ integration/
└── __main__.py    # python -m pepper
```

