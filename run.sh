#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Install Python 3.10+ and try again."
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "Creating venv..."
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi

# shellcheck disable=SC1091
source .venv/bin/activate

python main.py --check || {
  echo ""
  echo "Fix the issue above, then run: ./run.sh"
  exit 1
}

exec python main.py
