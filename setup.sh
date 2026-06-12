#!/usr/bin/env bash
# Pepper instant setup — plug and play.
#
#   ./setup.sh           install + verify, print the MCP config to paste
#   ./setup.sh --dev     also install test/lint tooling (pytest, ruff)
#   ./setup.sh --warm    also pre-download the embedding model (~130 MB, one-time)
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$REPO_DIR/.venv"
DEV=0
WARM=0
for arg in "$@"; do
  case "$arg" in
    --dev)  DEV=1 ;;
    --warm) WARM=1 ;;
    *) echo "unknown option: $arg (use --dev / --warm)"; exit 1 ;;
  esac
done

say()  { printf '\033[1;32m==>\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# 1. Python >= 3.11
PYTHON="${PYTHON:-python3}"
command -v "$PYTHON" >/dev/null 2>&1 || fail "python3 not found — install Python 3.11+ first"
"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' \
  || fail "Python 3.11+ required, found $("$PYTHON" -V 2>&1) — set PYTHON=/path/to/python3.11 and re-run"
say "Python OK: $("$PYTHON" -V 2>&1)"

# 2. Virtual environment (reused if it already exists)
if [ ! -x "$VENV/bin/python" ]; then
  say "Creating virtual environment at .venv"
  "$PYTHON" -m venv "$VENV"
else
  say "Reusing existing .venv"
fi
PY="$VENV/bin/python"

# 3. Install Pepper (editable). --dev adds pytest/ruff.
say "Installing Pepper$( [ "$DEV" -eq 1 ] && echo ' (with dev extras)')"
"$PY" -m pip install --quiet --upgrade pip
if [ "$DEV" -eq 1 ]; then
  "$PY" -m pip install --quiet -e "$REPO_DIR[dev]"
else
  "$PY" -m pip install --quiet -e "$REPO_DIR"
fi

# 4. Smoke test: migrate a throwaway DB and exercise one tool end-to-end.
say "Verifying install (migrations + one tool call against a temp DB)"
SMOKE_DB="$(mktemp -d)/smoke.db"
PEPPER_DB_PATH="$SMOKE_DB" "$PY" - <<'EOF'
from pepper.mcp.server import bootstrap, pepper_get_schedule
bootstrap()
out = pepper_get_schedule("2026-01-01T00:00:00+00:00", "2026-01-02T00:00:00+00:00")
assert out["success"] is True, out
print("    smoke test passed")
EOF
rm -f "$SMOKE_DB"

# 5. Optional: pre-download the embedding model so the first real
#    classification is instant (otherwise it downloads lazily on first use).
if [ "$WARM" -eq 1 ]; then
  say "Warming embedding model cache (~130 MB, one-time download)"
  "$PY" -c "from pepper.ml.embedder import get_embed_fn; get_embed_fn()('warmup')"
fi

# 6. Ready-to-paste wiring.
DB_PATH="${PEPPER_DB_PATH:-$HOME/.pepper/pepper.db}"
say "Done. Pepper is installed and verified."
cat <<EOF

Add Pepper to your agent's MCP server config (paste as-is):

  {
    "mcpServers": {
      "pepper": {
        "command": "$VENV/bin/python",
        "args": ["-m", "pepper"],
        "env": { "PEPPER_DB_PATH": "$DB_PATH" }
      }
    }
  }

Then install the skill so the agent knows how to drive the tools:

  cp "$REPO_DIR/SKILL.md" <your-agent>/skills/pepper-scheduler/SKILL.md

Run the server manually any time with:

  $VENV/bin/python -m pepper
EOF
