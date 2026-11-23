#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
runtime="$root/portable/.runtime"
repo="$runtime/openmotion"
revision=c12b13b142262a521ea2c90b99c14dea9d1a3eaf
mkdir -p "$runtime"
if [ ! -d "$repo/.git" ]; then
  git init "$repo"
  git -C "$repo" remote add origin https://github.com/nexu-io/openmotion.git
  git -C "$repo" fetch --depth=1 origin "$revision"
  GIT_LFS_SKIP_SMUDGE=1 git -C "$repo" checkout --detach FETCH_HEAD
fi
if [ "$(git -C "$repo" rev-parse HEAD)" != "$revision" ]; then
  printf 'Ожидался OpenMotion %s в %s\n' "$revision" "$repo" >&2
  exit 1
fi
npm install --prefix "$runtime/node26" --save-exact node@26.11.1
export PATH="$runtime/node26/node_modules/.bin:$PATH"
cd "$repo"
npm ci
npm run build:studio
printf 'OpenMotion собран. Команда запуска указана в README.md.\n'
