#!/usr/bin/env bash
set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
root=$(dirname -- "$here")
source "$root/portable/env.sh"
tools="$root/portable/skills/home-codex/ffmpeg-skill/scripts"
output_dir=${MONTAGE_EXPORT_DIR:-/workspaces/exports}
mkdir -p "$output_dir"
work=$(mktemp -d "${TMPDIR:-/tmp}/montage-news.XXXXXX")
export FONTCONFIG_FILE="$work/fonts.conf"
python3 - "$root/build25/fonts" "$FONTCONFIG_FILE" <<'PY'
from pathlib import Path
import sys
from xml.sax.saxutils import escape

fonts, config = sys.argv[1:]
Path(config).write_text(f'<fontconfig><include>/etc/fonts/fonts.conf</include><dir>{escape(fonts)}</dir></fontconfig>\n')
PY
python3 "$tools/background.py" --duration 4.12 --width 1280 --height 720 --fps 25 \
  --color 0x151E2A -o "$work/appeal-card.mp4"
python3 - "$here/project.json" "$work/project.json" "$output_dir" "$work/appeal-card.mp4" <<'PY'
from pathlib import Path
import json
import sys

original, rendered, output, card = [Path(x) for x in sys.argv[1:]]
project = json.loads(original.read_text())
for clip in project['clips']:
    clip['src'] = str(card if clip['src'].endswith('appeal-card.mp4') else (original.parent / clip['src']).resolve())
project['captions']['ass'] = str(original.parent / project['captions']['ass'])
project['output'] = str(output.resolve() / Path(project['output']).name)
rendered.write_text(json.dumps(project, ensure_ascii=False, indent=2) + '\n')
PY
insert="$output_dir/Поджоги_и_реальные_сроки_RUTUBE_и_YouTube.mp4"
if [ ! -e "$insert" ]; then
  python3 "$tools/render.py" "$work/project.json" --intermediate-preset veryfast
fi
python3 "$tools/join.py" "$root/Государств_Как_обезоп_138347372_456246039_1080p_.mp4" "$insert" \
  --transition none --width 1920 --height 1080 --fps 25 --preset veryfast --quality 17 \
  -o "$output_dir/Государств_Как_обезоп_с_финальной_вставкой.mp4"
