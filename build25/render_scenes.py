#!/usr/bin/env python3
import json, math, pathlib, subprocess, sys, functools
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

BASE = pathlib.Path(__file__).parent
SRC = BASE.parent / "25_лет_вместе_только_исходники"
W, H = 1920, 1080
FPS = 60
HERO_W, HERO_H = 1800, 1012
M = 1.30
FONT = str(BASE / "fonts" / "Unbounded-SemiBold.ttf")

tl = json.loads((SRC / "timeline.json").read_text())
SCENES = [s for s in tl["scenes"] if "photo" in s]
ROWS = {p["id"]: p for p in json.loads((SRC / "photos.json").read_text())}

def sine(x):
    x = max(0.0, min(1.0, x))
    return (1 - math.cos(math.pi * x)) / 2

def out_ease(x, n=3):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** (n + 1)

@functools.lru_cache(maxsize=6)
def photo_assets(pid):
    img = cv2.imread(str(SRC / ROWS[pid]["file"]), cv2.IMREAD_COLOR)
    h, w = img.shape[:2]
    sc = min(HERO_W / w, HERO_H / h)
    hw, hh = round(w * sc), round(h * sc)
    hero = cv2.resize(img, (hw, hh), interpolation=cv2.INTER_AREA if sc < 1 else cv2.INTER_LANCZOS4)
    d = np.load(BASE / "work" / "depth" / f"{pid:03d}.npy").astype(np.float32)
    d = cv2.resize(d, (hw, hh), interpolation=cv2.INTER_AREA)
    d = cv2.GaussianBlur(d, (0, 0), 2.0)
    sw, sh = round(hw * M), round(hh * M)
    px, py = (sw - hw) // 2, (sh - hh) // 2
    S = cv2.copyMakeBorder(hero, py, sh - hh - py, px, sw - hw - px, cv2.BORDER_REFLECT_101)
    edge = S.copy()
    edge = cv2.GaussianBlur(edge, (0, 0), 18)
    mask = np.zeros((sh, sw), np.float32)
    mask[py:py + hh, px:px + hw] = 1
    mask = cv2.GaussianBlur(mask, (0, 0), 12)[:, :, None]
    S = (hero_pad := S) * mask + edge * (1 - mask)
    S = S.astype(np.float32)
    Dpad = cv2.copyMakeBorder(d, py, sh - hh - py, px, sw - hw - px, cv2.BORDER_REPLICATE)
    Dd = cv2.resize(d, (hw, hh), interpolation=cv2.INTER_AREA)
    cover = cv2.resize(img, (2304, 1296), interpolation=cv2.INTER_AREA)
    cover = cv2.GaussianBlur(cover, (0, 0), 40).astype(np.float32)
    cover = cover * 0.30 + np.array([29, 17, 7], np.float32) * 0.70
    bg = cover.astype(np.uint8)
    shadow = np.zeros((H, W), np.float32)
    hx, hy = (W - hw) // 2, (H - hh) // 2
    cv2.rectangle(shadow, (hx - 4, hy - 2), (hx + hw + 4, hy + hh + 8), 1.0, -1)
    shadow = cv2.GaussianBlur(shadow, (0, 0), 22) * 0.55
    return dict(S=S, Dpad=Dpad, Dd=Dd, hw=hw, hh=hh, sw=sw, sh=sh,
                bg=bg, hx=hx, hy=hy, shadow=shadow)

def motion(s, i, q):
    sid = s["id"]
    if sid == "founding-wide":
        return 1.01 + 0.07 * q, -4 + 8 * q, 3 - 6 * q, 0, 0
    if sid == "founding-close":
        return 1.34 + 0.14 * q, 6 - 12 * q, -4 + 8 * q, 0.04, -0.13
    if sid == "founding-return":
        return 1.05 + 0.10 * q, -8 + 16 * q, 10 - 20 * q, 0, 0.03
    pat = i % 5
    if pat == 0:
        return 1.05 + 0.09 * q, -6 + 12 * q, 4 - 8 * q, 0, 0
    if pat == 1:
        return 1.14 - 0.09 * q, 6 - 12 * q, -4 + 8 * q, 0, 0
    if pat == 2:
        return 1.10, -16 + 32 * q, 8 - 16 * q, 0, 0
    if pat == 3:
        return 1.10, 16 - 32 * q, -8 + 16 * q, 0, 0
    return 1.07 + 0.05 * q, 0, 14 - 28 * q, 0, 0

def render_scene(args):
    i, s = args
    a = photo_assets(s["photo"])
    hw, hh, sw, sh = a["hw"], a["hh"], a["sw"], a["sh"]
    Dd = a["Dd"]
    dur = s["duration"]
    n = round(dur * FPS)
    gx, gy = np.meshgrid((np.arange(hw, dtype=np.float32) - hw / 2) / hw,
                         (np.arange(hh, dtype=np.float32) - hh / 2) / hh)
    dep = (Dd - 0.45)
    year = s.get("year") or ""
    font = ImageFont.truetype(FONT, 105) if year else None
    out = BASE / "scenes" / f"{i:03d}_{s['id']}.mp4"
    if out.exists():
        return str(out)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-crf", "14", "-preset", "medium", "-threads", "2",
           "-pix_fmt", "yuv420p", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    bgx0, bgy0 = (2304 - W) // 2, (1296 - H) // 2
    for f in range(n):
        t = f / FPS
        q = sine(t / dur)
        z, dx, dy, fx, fy = motion(s, i, q)
        ze = z * (1 + 0.05 * dep)
        panx = fx * hw + dx * 0.35
        pany = fy * hh + dy * 0.35
        map_x = sw / 2 + panx + gx * hw / ze - dx * dep * 2.2
        map_y = sh / 2 + pany + gy * hh / ze - dy * dep * 2.2
        hero = cv2.remap(a["S"], map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        bz = 1.03 + 0.04 * q
        bw, bh = round(2304 / bz), round(1296 / bz)
        bgc = cv2.resize(a["bg"], (bw, bh), interpolation=cv2.INTER_LINEAR)
        bx = int((bw - W) / 2 - dx * 0.5)
        by = int((bh - H) / 2 - dy * 0.5)
        bx = max(0, min(bw - W, bx)); by = max(0, min(bh - H, by))
        canvas = bgc[by:by + H, bx:bx + W].astype(np.float32)
        canvas *= (1 - a["shadow"][:, :, None])
        canvas[a["hy"]:a["hy"] + hh, a["hx"]:a["hx"] + hw] = hero
        frame = canvas.astype(np.uint8)
        if year and 0.55 < t < 3.7:
            ain = out_ease((t - 0.65) / 0.5)
            aout = 1 - max(0.0, min(1.0, (t - 3.2) / 0.45))
            alpha = ain * aout
            if alpha > 0.01:
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                dr = ImageDraw.Draw(ov)
                tx = round(112 - 45 * (1 - ain))
                dr.text((tx + 2, 841), year, font=font, fill=(0, 0, 0, round(alpha * 150)), stroke_width=2)
                dr.text((tx, 838), year, font=font, fill=(255, 255, 255, round(alpha * 255)))
                rw = round(76 * out_ease((t - 0.8) / 0.45, 2))
                dr.rectangle((tx, 967, tx + rw, 972), fill=(206, 51, 64, round(alpha * 255)))
                ovn = np.asarray(ov)
                al = ovn[:, :, 3:4].astype(np.float32) / 255
                frame = (frame * (1 - al) + ovn[:, :, :3][:, :, ::-1] * al).astype(np.uint8)
        proc.stdin.write(frame[:, :, ::-1].tobytes())
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"encode failed {s['id']}")
    return str(out)

if __name__ == "__main__":
    import multiprocessing as mp
    only = sys.argv[1:] if len(sys.argv) > 1 else None
    jobs = [(i, s) for i, s in enumerate(SCENES)]
    if only:
        jobs = [(i, s) for i, s in jobs if s["id"] in only or str(i) in only]
    with mp.Pool(3) as pool:
        for r in pool.imap_unordered(render_scene, jobs):
            print("done", r, flush=True)
    print("ALL SCENES DONE", flush=True)