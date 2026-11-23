#!/usr/bin/env bash
# Подключить командой source portable/env.sh из Bash.
_montage_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
export PATH="$_montage_root/.venv/bin:$_montage_root/portable/.runtime/hyperframes/node_modules/.bin:$PATH"
export HYPERFRAMES_CACHE_DIR="${HYPERFRAMES_CACHE_DIR:-$HOME/.cache/montage-hyperframes}"
unset _montage_root
