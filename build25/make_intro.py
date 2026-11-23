#!/usr/bin/env python3
import re, subprocess, pathlib

BASE = pathlib.Path(__file__).parent
SRC = BASE.parent / "25_лет_вместе_только_исходники"
VIDEO = SRC / "originals" / "Дипломат_Р_Я_СОЗДАВАЛ_41859195_456242654_1080p_.mp4"
W = BASE / "work"

def run(cmd):
    print("+", " ".join(str(c) for c in cmd)[:200])
    subprocess.run([str(c) for c in cmd], check=True)

segs = [(24.48, 29.20), (65.40, 83.80)]
parts = []
for i, (a, b) in enumerate(segs):
    out = W / f"seg{i}.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-ss", a, "-i", VIDEO, "-t", b - a,
         "-vf", "fps=60,setsar=1", "-c:v", "libx264", "-crf", "12", "-preset", "medium",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", out])
    parts.append(out)

lst = W / "segs.txt"
lst.write_text("".join(f"file '{p}'\n" for p in parts))
concat = W / "intro_raw.mp4"
run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
     "-c", "copy", concat])

def ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

srt = (SRC / "putin.srt").read_text(encoding="utf-8")
blocks = re.findall(r"(\d+)\n([\d:,]+) --> ([\d:,]+)\n(.+?)(?:\n\n|\Z)", srt, re.S)

def parse(t):
    h, m, rest = t.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Unbounded SemiBold,58,&H004DC2FF,&H00FFFFFF,&H281A1408,&H281A1408,0,0,0,0,100,100,0,0,3,12,0,2,80,80,58,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

lines = []
for _, a, b, text in blocks:
    a, b = parse(a), parse(b)
    text = " ".join(text.split())
    words = text.split(" ")
    weights = [len(w) + 1 for w in words]
    total = sum(weights)
    dur_cs = round((b - a) * 100)
    parts_cs = [round(dur_cs * w / total) for w in weights]
    parts_cs[-1] += dur_cs - sum(parts_cs)
    karaoke = " ".join(f"{{\\kf{cs}}}{w}" for w, cs in zip(words, parts_cs))
    lines.append(f"Dialogue: 0,{ts(a)},{ts(b)},Sub,,0,0,0,,\\h{karaoke}\\h")

ass = W / "intro.ass"
ass.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")

out = BASE / "intro.mp4"
run(["ffmpeg", "-v", "error", "-y", "-i", concat,
     "-vf", f"ass={ass}:fontsdir={BASE / 'fonts'}",
     "-c:v", "libx264", "-crf", "12", "-preset", "medium",
     "-c:a", "copy", out])
print("intro done:", out)