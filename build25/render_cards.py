#!/usr/bin/env python3
import json, math, pathlib, subprocess, sys, functools
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

BASE = pathlib.Path(__file__).parent
SRC = BASE.parent / "25_лет_вместе_только_исходники"
W, H = 1920, 1080
FPS = 60
PHOTO_W, PHOTO_H = 1560, 878
FR_SIDE, FR_TOP, FR_BOT = 16, 16, 52
SS = 1.5
FOCAL = 1500.0
FONT = str(BASE / "fonts" / "Unbounded-SemiBold.ttf")

tl = json.loads((SRC / "timeline.json").read_text())
SCENES = [s for s in tl["scenes"] if "photo" in s]
ROWS = {p["id"]: p for p in json.loads((SRC / "photos.json").read_text())}

def clamp01(x):
    return max(0.0, min(1.0, x))

def sine(x):
    return (1 - math.cos(math.pi * clamp01(x))) / 2

def out_ease(x, n=3):
    return 1 - (1 - clamp01(x)) ** (n + 1)

def rounded_alpha(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    return np.asarray(m, np.float32) / 255

@functools.lru_cache(maxsize=6)
def photo_assets(pid):
    img = cv2.imread(str(SRC / ROWS[pid]["file"]), cv2.IMREAD_COLOR)
    h, w = img.shape[:2]
    sc = min(PHOTO_W / w, PHOTO_H / h)
    pw, ph = round(w * sc), round(h * sc)
    photo = cv2.resize(img, (pw, ph), interpolation=cv2.INTER_AREA if sc < 1 else cv2.INTER_LANCZOS4)
    photo = photo.astype(np.float32)
    photo *= np.array([0.965, 1.0, 1.035], np.float32)
    rng = np.random.default_rng(pid)
    photo += rng.normal(0, 3.2, (ph, pw, 1)).astype(np.float32)
    photo = np.clip(photo, 0, 255)
    cw, ch = pw + FR_SIDE * 2, ph + FR_TOP + FR_BOT
    sw, sh = round(cw * SS), round(ch * SS)
    paper = np.empty((sh, sw, 3), np.float32)
    paper[:] = np.array([236, 243, 246], np.float32)
    paper += rng.normal(0, 1.6, (sh, sw, 1)).astype(np.float32)
    px, py = round(FR_SIDE * SS), round(FR_TOP * SS)
    pws, phs = round(pw * SS), round(ph * SS)
    photos = cv2.resize(photo.astype(np.uint8), (pws, phs), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
    paper[py:py + phs, px:px + pws] = photos
    inner = np.zeros((sh, sw), np.float32)
    cv2.rectangle(inner, (px, py), (px + pws, py + phs), 1.0, 2)
    inner = cv2.GaussianBlur(inner, (0, 0), 1.2) * 0.30
    paper *= (1 - inner[:, :, None])
    alpha = rounded_alpha(sw, sh, round(7 * SS))
    rgba = np.dstack([np.clip(paper, 0, 255), alpha * 255]).astype(np.float32)
    shadow_src = (alpha * 255).astype(np.uint8)
    cover = cv2.resize(img, (2304, 1296), interpolation=cv2.INTER_AREA)
    cover = cv2.GaussianBlur(cover, (0, 0), 42).astype(np.float32)
    cover = cover * 0.26 + np.array([26, 15, 7], np.float32) * 0.74
    bg = cover.astype(np.uint8)
    bokeh = np.zeros((1296, 2304, 4), np.float32)
    rb = np.random.default_rng(pid + 1000)
    for _ in range(14):
        cx, cy = int(rb.integers(0, 2304)), int(rb.integers(0, 1296))
        r = int(rb.integers(26, 95))
        a = float(rb.uniform(0.05, 0.13))
        col = np.array([210, 225, 255], np.float32) if rb.random() < 0.6 else np.array([180, 200, 235], np.float32)
        cv2.circle(bokeh, (cx, cy), r, (float(col[0]), float(col[1]), float(col[2]), a), -1, cv2.LINE_AA)
    bokeh = cv2.GaussianBlur(bokeh, (0, 0), 10)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vig = np.clip(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2, 0, 2)
    vig = (0.30 * np.clip(vig - 0.55, 0, 1))[:, :, None]
    src_corners = np.array([[0, 0], [sw, 0], [sw, sh], [0, sh]], np.float32)
    return dict(rgba=rgba, shadow_src=shadow_src, cw=cw, ch=ch, sw=sw, sh=sh,
                bg=bg, bokeh=bokeh, vig=vig, src_corners=src_corners)

def choreography(s, i, t, d):
    sid = s["id"]
    o = min(0.92, d * 0.35)
    q = sine(t / d)
    enter = 1 - out_ease(t / o, 3)
    exit_ = sine((t - (d - o)) / o)
    found = sid.startswith("founding")
    k = 0.35 if found else 1.0
    sg = 1 if i % 2 == 0 else -1
    pat = i % 6
    if sid == "founding-wide":
        bry, brx, bsc, btx, bty, brz = -2 + 4 * q, 1.5 - 2 * q, 0.97 + 0.05 * q, 0, 0, 0
    elif sid == "founding-close":
        bry, brx, bsc, btx, bty, brz = 3 - 5 * q, -1 + 2 * q, 1.30 + 0.10 * q, 0, -99, 0
    elif sid == "founding-return":
        bry, brx, bsc, btx, bty, brz = -3 + 5 * q, 1.5 - 2 * q, 1.12 - 0.07 * q, 0, -18, 0
    elif pat == 0:
        bry, brx, bsc, btx, bty, brz = -5 + 10 * q, 2 - 4 * q, 1.00 + 0.06 * q, -8 + 16 * q, 4 - 8 * q, -1.5 + 2 * q
    elif pat == 1:
        bry, brx, bsc, btx, bty, brz = 5 - 10 * q, -2 + 4 * q, 1.06 - 0.06 * q, 8 - 16 * q, -4 + 8 * q, 1.5 - 2 * q
    elif pat == 2:
        bry, brx, bsc, btx, bty, brz = -3 + 6 * q, -4 + 7 * q, 1.02 + 0.06 * q, 0, 8 - 16 * q, 0.8 * q
    elif pat == 3:
        bry, brx, bsc, btx, bty, brz = -7 + 12 * q, 1 - 2 * q, 1.03 + 0.04 * q, -10 + 18 * q, 0, -1 + 1.5 * q
    elif pat == 4:
        bry, brx, bsc, btx, bty, brz = 7 - 12 * q, -1 + 2 * q, 1.05 - 0.04 * q, 10 - 18 * q, 0, 1 - 1.5 * q
    else:
        bry, brx, bsc, btx, bty, brz = -2 + 4 * q, 4 - 7 * q, 1.01 + 0.07 * q, 0, -8 + 14 * q, -0.8 + 1.2 * q
    if found:
        ery, erx, esc, etx, ety, erz = 4 * sg, -3 * sg, -0.05, -60 * sg, 30, 1.5 * sg
        xry, xrx, xsc, xtx, xty, xrz = -3 * sg, 2 * sg, 0.03, 50 * sg, -20, -1 * sg
    elif pat == 0:
        ery, erx, esc, etx, ety, erz = 12, -7, -0.12, -170, 90, -5
        xry, xrx, xsc, xtx, xty, xrz = -8, 4, 0.06, 130, -60, 3
    elif pat == 1:
        ery, erx, esc, etx, ety, erz = -12, 7, -0.12, 170, -90, 5
        xry, xrx, xsc, xtx, xty, xrz = 8, -4, 0.06, -130, 60, -3
    elif pat == 2:
        ery, erx, esc, etx, ety, erz = 0, 10, -0.18, 0, 110, 2
        xry, xrx, xsc, xtx, xty, xrz = 0, -6, 0.08, 0, -80, -1.5
    elif pat == 3:
        ery, erx, esc, etx, ety, erz = 22, -3, -0.08, -220, 20, -3
        xry, xrx, xsc, xtx, xty, xrz = -14, 2, 0.05, 160, -30, 2
    elif pat == 4:
        ery, erx, esc, etx, ety, erz = -22, 3, -0.08, 220, -20, 3
        xry, xrx, xsc, xtx, xty, xrz = 14, -2, 0.05, -160, 30, -2
    else:
        ery, erx, esc, etx, ety, erz = 5, -12, -0.14, 40, 140, 4
        xry, xrx, xsc, xtx, xty, xrz = -4, 8, 0.07, -50, -100, -2.5
    ry = math.radians(bry + k * (enter * ery + exit_ * xry))
    rx = math.radians(brx + k * (enter * erx + exit_ * xrx))
    rz = math.radians(brz + k * (enter * erz + exit_ * xrz))
    sc = bsc * (1 + k * (enter * esc + exit_ * xsc))
    tx = btx + k * (enter * etx + exit_ * xtx)
    ty = bty + k * (enter * ety + exit_ * xty)
    return ry, rx, rz, sc, tx, ty

def project(cw, ch, rx, ry, rz, s, tx, ty, ox=0.0, oy=0.0, grow=1.0):
    cx, cy = math.cos(rx), math.sin(rx)
    bx, by = math.cos(ry), math.sin(ry)
    pts = []
    for X, Y in ((-cw / 2, -ch / 2), (cw / 2, -ch / 2), (cw / 2, ch / 2), (-cw / 2, ch / 2)):
        x1, y1, z1 = X, Y * cx, Y * cy
        x2, y2, z2 = x1 * bx + z1 * by, y1, -x1 * by + z1 * bx
        px = FOCAL * x2 / (FOCAL + z2)
        py = FOCAL * y2 / (FOCAL + z2)
        pts.append((s * grow * px, s * grow * py))
    cz, sz = math.cos(rz), math.sin(rz)
    out = []
    for px, py in pts:
        out.append((W / 2 + tx + ox + px * cz - py * sz, H / 2 + ty + oy + px * sz + py * cz))
    return np.array(out, np.float32)

def render_scene(args):
    i, s = args
    a = photo_assets(s["photo"])
    dur = s["duration"]
    n = round(dur * FPS)
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
    cw, ch = a["cw"], a["ch"]
    for f in range(n):
        t = f / FPS
        ry, rx, rz, sc, tx, ty = choreography(s, i, t, dur)
        dst = project(cw, ch, rx, ry, rz, sc, tx, ty)
        M = cv2.getPerspectiveTransform(a["src_corners"], dst)
        card = cv2.warpPerspective(a["rgba"], M, (W, H), flags=cv2.INTER_LINEAR,
                                   borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        dst_sh = project(cw, ch, rx, ry, rz, sc, tx, ty,
                         ox=12 - 20 * math.sin(ry), oy=30, grow=1.04)
        Ms = cv2.getPerspectiveTransform(a["src_corners"], dst_sh)
        shmask = cv2.warpPerspective(a["shadow_src"], Ms, (W, H), flags=cv2.INTER_LINEAR,
                                     borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        shmask = cv2.GaussianBlur(shmask, (0, 0), 18).astype(np.float32) / 255 * 0.6
        q = sine(t / dur)
        bz = 1.05 + 0.04 * q
        bw, bh = round(2304 / bz), round(1296 / bz)
        bgc = cv2.resize(a["bg"], (bw, bh), interpolation=cv2.INTER_LINEAR)
        bx = int((bw - W) / 2 - tx * 0.6 - 40 * math.sin(ry))
        by = int((bh - H) / 2 - ty * 0.02)
        bx = max(0, min(bw - W, bx)); by = max(0, min(bh - H, by))
        canvas = bgc[by:by + H, bx:bx + W].astype(np.float32)
        bok = cv2.resize(a["bokeh"], (bw, bh), interpolation=cv2.INTER_LINEAR)
        kx = int((bw - W) / 2 - tx * 1.4 - 60 * math.sin(ry) + t * 3)
        ky = int((bh - H) / 2 - ty * 0.05)
        kx = max(0, min(bw - W, kx)); ky = max(0, min(bh - H, ky))
        bok = bok[ky:ky + H, kx:kx + W]
        ba = bok[:, :, 3:4]
        canvas = canvas * (1 - ba) + bok[:, :, :3] * ba
        canvas *= (1 - shmask[:, :, None])
        al = card[:, :, 3:4] / 255
        canvas = canvas * (1 - al) + card[:, :, :3] * al
        canvas *= (1 - a["vig"])
        frame = canvas.astype(np.uint8)
        if year and 0.55 < t < 3.7:
            ain = out_ease((t - 0.65) / 0.5)
            aout = 1 - clamp01((t - 3.2) / 0.45)
            alpha = ain * aout
            if alpha > 0.01:
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                dr = ImageDraw.Draw(ov)
                txr = round(112 - 45 * (1 - ain))
                dr.text((txr + 2, 841), year, font=font, fill=(0, 0, 0, round(alpha * 150)), stroke_width=2)
                dr.text((txr, 838), year, font=font, fill=(255, 255, 255, round(alpha * 255)))
                rw = round(76 * out_ease((t - 0.8) / 0.45, 2))
                dr.rectangle((txr, 967, txr + rw, 972), fill=(206, 51, 64, round(alpha * 255)))
                ovn = np.asarray(ov)
                al2 = ovn[:, :, 3:4].astype(np.float32) / 255
                frame = (frame * (1 - al2) + ovn[:, :, :3][:, :, ::-1] * al2).astype(np.uint8)
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