#!/usr/bin/env python3
import json, pathlib, subprocess
import numpy as np

BASE = pathlib.Path(__file__).parent
SRC = BASE.parent / "25_лет_вместе_только_исходники"
SFX = BASE.parent / "MONTAGE" / "SFX"
SR = 48000
TOTAL = 398.75
N = int(TOTAL * SR)

def dec(path, ss=None, t=None):
    cmd = ["ffmpeg", "-v", "error"]
    if ss is not None:
        cmd += ["-ss", str(ss)]
    cmd += ["-i", str(path)]
    if t is not None:
        cmd += ["-t", str(t)]
    cmd += ["-f", "f32le", "-ac", "2", "-ar", str(SR), "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()

mix = np.zeros((N, 2), np.float32)

def add(sig, t, gain):
    i = int(t * SR)
    n = min(len(sig), N - i)
    if n > 0:
        mix[i:i + n] += sig[:n] * gain

narr = dec(next(SRC.glob("originals/ElevenLabs*.mp3")))
add(narr, 23.55, 1.0)
print("narrator", len(narr) / SR)

intro_audio = dec(BASE / "intro.mp4") * 3.0
ni = len(intro_audio)
fade = np.ones(ni, np.float32)
nf = int(0.35 * SR)
fade[-nf:] = 0.5 + 0.5 * np.cos(np.pi * np.arange(nf) / nf)
add(intro_audio * fade[:, None], 0.0, 1.0)
print("intro audio", ni / SR)

mus = subprocess.run(
    ["ffmpeg", "-v", "error", "-i", str(SRC / "assets/audio/eternal_hope.mp3"),
     "-ss", "70", "-i", str(SRC / "assets/audio/eternal_hope.mp3"),
     "-filter_complex",
     "[0:a]atrim=0:190,asetpts=PTS-STARTPTS[a];[1:a]asetpts=PTS-STARTPTS[b];[a][b]acrossfade=d=6:c1=tri:c2=tri",
     "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
    capture_output=True, check=True).stdout
mus = np.frombuffer(mus, np.float32).reshape(-1, 2).copy()
print("music extended", len(mus) / SR)

t = np.arange(len(mus)) / SR + 22.92
env = np.zeros(len(mus), np.float32)
def ramp(a, b, va, vb):
    m = (t >= a) & (t < b)
    u = (t[m] - a) / (b - a)
    env[m] = va + (vb - va) * (0.5 - 0.5 * np.cos(np.pi * u))
ramp(22.92, 25.0, 0.0, 0.24)
m = (t >= 25.0) & (t < 82.3); env[m] = 0.24
ramp(82.3, 85.0, 0.24, 0.46)
m = (t >= 85.0) & (t < 386.0); env[m] = 0.46
ramp(386.0, 398.4, 0.46, 0.0)
add(mus * env[:, None], 22.92, 1.0)

timeline = json.loads((SRC / "timeline.json").read_text())
for s in timeline["scenes"]:
    if s.get("year") and "photo" in s:
        add(dec(SRC / "assets/audio/turn.mp3"), s["start"] - 0.15, 0.4)
for tt, g in ((336.35, 0.3), (340.85, 0.3)):
    add(dec(SFX / "[SMXTVNNIX] WHOOSH 2.mp3"), tt, g)
add(dec(SFX / "[SMXTVNNIX] FILM BURN 1.wav"), 387.55, 0.28)
add(dec(SFX / "[SMXTVNNIX] CAMERA SNAP.wav"), 388.6, 0.22)

peak = np.abs(mix).max()
print("peak before norm", peak)
if peak > 0.98:
    mix *= 0.98 / peak
wav = BASE / "work" / "mix_raw.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR),
                "-ac", "2", "-i", "-", "-c:a", "pcm_f32le", str(wav)],
               input=mix.astype("<f4", copy=False).tobytes(), check=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav),
                "-af", f"loudnorm=I=-16:TP=-1.5:LRA=11,aresample={SR},"
                       f"atrim=end_sample={N},asetpts=N/SR/TB",
                "-c:a", "aac", "-b:a", "192k", str(BASE / "mix.m4a")], check=True)
print("mix.m4a written")
