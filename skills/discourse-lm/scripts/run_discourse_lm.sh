#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${SKILL_DIR}/../.." && pwd)"

if [[ -d "${REPO_ROOT}/src/discourse_lm" ]]; then
  export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
  exec python3 -m discourse_lm.cli "$@"
fi

if command -v discourse-lm >/dev/null 2>&1; then
  exec discourse-lm "$@"
fi

echo "discourse-lm is not installed and the repository source tree was not found." >&2
echo "Install the project first, then retry." >&2
exit 1
