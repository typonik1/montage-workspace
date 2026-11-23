#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
mode=${1:-install}

verify_ffmpeg() {
  command -v ffmpeg >/dev/null
  command -v ffprobe >/dev/null
  local filters version filter
  version=$(ffmpeg -version | awk 'NR==1 {print $3}')
  if [[ ! $version =~ ^([0-9]+)\.([0-9]+) ]] ||
      (( BASH_REMATCH[1] < 6 || (BASH_REMATCH[1] == 6 && BASH_REMATCH[2] < 1) )); then
    printf 'Нужен FFmpeg 6.1 или новее. Обнаружена версия %s\n' "$version" >&2
    return 1
  fi
  filters=$(ffmpeg -hide_banner -filters 2>/dev/null)
  for filter in ass subtitles loudnorm xfade zscale; do
    if ! awk -v filter="$filter" '$2 == filter {found = 1} END {exit !found}' <<< "$filters"; then
      printf 'Отсутствует фильтр FFmpeg %s\n' "$filter" >&2
      return 1
    fi
  done
  printf 'FFmpeg %s и фильтры ass, subtitles, loudnorm, xfade, zscale доступны.\n' "$version"
}

install_skills() {
  local from=$1 to=$2 skill target
  mkdir -p "$to"
  for skill in "$from"/*; do
    [ -f "$skill/SKILL.md" ] || continue
    target="$to/${skill##*/}"
    if [ ! -e "$target" ] && [ ! -L "$target" ]; then
      cp -a -- "$skill" "$target"
    else
      printf 'Существующая версия скилла сохранена: %s\n' "$target"
    fi
  done
}

case "$mode" in
  --check)
    verify_ffmpeg
    exit 0
    ;;
  --openmotion)
    exec bash "$root/portable/setup-openmotion.sh"
    ;;
  install) ;;
  *) printf 'Использование: bash setup.sh [--check|--openmotion]\n' >&2; exit 2 ;;
esac

if [[ $(uname -s) != Linux ]]; then
  printf 'Открой папку в Codespaces или в Linux-контейнере.\n' >&2
  exit 1
fi

if ! verify_ffmpeg || ! command -v fc-match >/dev/null || ! command -v git-lfs >/dev/null || ! command -v xdg-open >/dev/null; then
  sudo apt-get update
  sudo apt-get install -y ffmpeg git-lfs fontconfig fonts-noto-core libcairo2 \
    libglib2.0-0t64 libgl1 libnss3 libatk1.0-0t64 libatk-bridge2.0-0t64 \
    libcups2t64 libdrm2 libgbm1 libasound2t64 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libxcb1 xdg-utils
  verify_ffmpeg
fi
if [ -e "$root/.git" ]; then
  git -C "$root" lfs install --local
  if git -C "$root" remote get-url origin >/dev/null 2>&1; then
    git -C "$root" lfs pull origin
  fi
fi

command -v node >/dev/null
command -v npm >/dev/null
node -e 'if (+process.versions.node.split(".")[0] < 22) process.exit(1)'
python3 -m venv "$root/.venv"
"$root/.venv/bin/python" -m pip install -r "$root/portable/requirements.txt"
npm install --prefix "$root/portable/.runtime/hyperframes" --save-exact hyperframes@0.9.65
source "$root/portable/env.sh"

install_skills "$root/portable/skills/home-agents" "$HOME/.agents/skills"
install_skills "$root/portable/skills/home-codex" "$HOME/.codex/skills"
install_skills "$root/.agents/skills" "$HOME/.agents/skills"
install_skills "$root/portable/skills/openmotion" "$HOME/.agents/skills"
font_dir="${XDG_DATA_HOME:-$HOME/.local/share}/fonts/montage-workspace"
mkdir -p "$font_dir" "$root/build25/scenes" "$root/build25/chunks" "$root/build25/work"
if [ ! -e "$font_dir/Unbounded-SemiBold.ttf" ]; then
  cp -- "$root/build25/fonts/Unbounded-SemiBold.ttf" "$font_dir/"
  fc-cache -f "$font_dir"
fi
if [ ! -e "$root/agent-desktop/.claude" ] && [ ! -L "$root/agent-desktop/.claude" ]; then
  ln -s .agents "$root/agent-desktop/.claude"
fi
hyperframes --version
python -c 'import av, cv2, numpy, onnxruntime, PIL; print("Основные Python-библиотеки доступны.")'
printf 'Готово. Для новой сессии Bash: source portable/env.sh\n'
