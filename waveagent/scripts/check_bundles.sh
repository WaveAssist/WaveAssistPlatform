#!/usr/bin/env bash
#
# check_bundles.sh — parity guard for the WaveAgent skill/example bundles.
#
# Verifies that the two bundled copies of the skill + golden example stay in
# sync with the authoritative source:
#   source skill    -> skill/
#   source example  -> examples/clickup-weekly/
#   bundle (Claude) -> plugin/skills/waveassist-build-deploy/
#   bundle (Cursor) -> cursor/skills/waveassist-build-deploy/
#
# All bundled files must be byte-identical to source, with ONE exception:
# SKILL.md ships the example as a CHILD dir of the skill, so the bundled
# copies reference `./examples/clickup-weekly/` while the source references
# `../examples/clickup-weekly/`. We normalize that single token before diffing.
#
# Exits 0 and prints "BUNDLES IN SYNC" when everything matches; otherwise
# prints the diffs and exits 1.

set -u

# Resolve repo root from this script's location (scripts/ lives at repo root).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

SKILL_FILES=(
  "SKILL.md"
  "waveassist-sdk.md"
  "prompt-writing-with-call-llm.md"
  "email-html-design.md"
  "integrations-without-composio.md"
)
EXAMPLE_FILES=(
  "config.yaml"
  "fetch_clickup.py"
  "email_summary.py"
)
BUNDLES=(
  "plugin/skills/waveassist-build-deploy"
  "cursor/skills/waveassist-build-deploy"
)

status=0

# Normalize the ../examples vs ./examples token so SKILL.md can be compared
# byte-for-byte on everything else.
normalize() {
  sed 's#\.\./examples/clickup-weekly/#./examples/clickup-weekly/#g' "$1"
}

for bundle in "${BUNDLES[@]}"; do
  # --- skill .md files ---
  for f in "${SKILL_FILES[@]}"; do
    src="skill/$f"
    dst="$bundle/$f"
    if [ ! -f "$dst" ]; then
      echo "MISSING: $dst"
      status=1
      continue
    fi
    if [ "$f" = "SKILL.md" ]; then
      # Allowed to differ ONLY by the ../examples vs ./examples line.
      if ! diff -u <(normalize "$src") <(normalize "$dst") >/tmp/check_bundles.diff 2>&1; then
        echo "DRIFT (beyond the allowed examples-path line): $dst"
        cat /tmp/check_bundles.diff
        status=1
      fi
    else
      if ! diff -u "$src" "$dst" >/tmp/check_bundles.diff 2>&1; then
        echo "DRIFT: $dst"
        cat /tmp/check_bundles.diff
        status=1
      fi
    fi
  done

  # --- example files ---
  for f in "${EXAMPLE_FILES[@]}"; do
    src="examples/clickup-weekly/$f"
    dst="$bundle/examples/clickup-weekly/$f"
    if [ ! -f "$dst" ]; then
      echo "MISSING: $dst"
      status=1
      continue
    fi
    if ! diff -u "$src" "$dst" >/tmp/check_bundles.diff 2>&1; then
      echo "DRIFT: $dst"
      cat /tmp/check_bundles.diff
      status=1
    fi
  done
done

# --- bundled MCP server: plugin/mcp must match the authoritative mcp/ ---
# (the Claude Code plugin runs its OWN bundled copy via uvx --from
#  ${CLAUDE_PLUGIN_ROOT}/mcp, so a stale plugin/mcp ships old server code).
if ! diff -rq --exclude=__pycache__ --exclude='*.egg-info' --exclude='*.pyc' \
       mcp/src plugin/mcp/src >/tmp/check_bundles.diff 2>&1; then
  echo "DRIFT: plugin/mcp/src differs from mcp/src"
  cat /tmp/check_bundles.diff
  status=1
fi
if ! diff -u mcp/pyproject.toml plugin/mcp/pyproject.toml >/tmp/check_bundles.diff 2>&1; then
  echo "DRIFT: plugin/mcp/pyproject.toml differs from mcp/pyproject.toml"
  cat /tmp/check_bundles.diff
  status=1
fi

# --- the guide bundled INTO the server package must match the source skill/ ---
for f in "${SKILL_FILES[@]}"; do
  if ! diff -u "skill/$f" "mcp/src/waveassist_mcp/_skill/$f" >/tmp/check_bundles.diff 2>&1; then
    echo "DRIFT: mcp/src/waveassist_mcp/_skill/$f differs from skill/$f"
    cat /tmp/check_bundles.diff
    status=1
  fi
done

rm -f /tmp/check_bundles.diff

if [ "$status" -eq 0 ]; then
  echo "BUNDLES IN SYNC"
fi
exit "$status"
