#!/usr/bin/env python3
"""Outro: photo-wall finale. Builds assets, then writes an 11 s HyperFrames composition."""
import json, pathlib, random, shutil
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

BASE = pathlib.Path(__file__).parent
SRC = BASE.parent / "25_лет_вместе_только_исходники"
OUT = BASE / "outro"
(OUT / "assets").mkdir(parents=True, exist_ok=True)
(OUT / "assets" / "strips").mkdir(parents=True, exist_ok=True)
(OUT / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
(OUT / "lib").mkdir(parents=True, exist_ok=True)
gsap = OUT / "lib" / "gsap.min.js"
if not gsap.is_file() or gsap.stat().st_size < 10_000:
    import urllib.request
    urllib.request.urlretrieve("https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js", gsap)
shutil.copy(SRC / "assets" / "fonts" / "Unbounded-SemiBold.ttf", OUT / "assets" / "fonts" / "Unbounded-SemiBold.ttf")

photos = json.loads((SRC / "photos.json").read_text())
ids = [p["id"] for p in photos]
rng = random.Random(7)

W, H = 1920, 1080
COLS, ROWS = 6, 4

def cover(im, cw, ch):
    w, h = im.size
    sc = max(cw / w, ch / h)
    im = im.resize((round(w * sc), round(h * sc)), Image.Resampling.LANCZOS)
    x = (im.size[0] - cw) // 2
    y = (im.size[1] - ch) // 2
    return im.crop((x, y, x + cw, y + ch))

# ---- background photo wall: chronological mosaic, graded and dimmed
wall_ids = [ids[i] for i in np.linspace(0, len(ids) - 1, COLS * ROWS).round().astype(int)]
cw, ch = W // COLS, H // ROWS
wall = Image.new("RGB", (W, H))
for k, pid in enumerate(wall_ids):
    im = Image.open(SRC / f"assets/photos/{pid:03d}.jpg").convert("RGB")
    wall.paste(cover(im, cw, ch), ((k % COLS) * cw, (k // COLS) * ch))
wall = ImageEnhance.Color(wall).enhance(0.72)
wall = ImageEnhance.Brightness(wall).enhance(0.46)
wall = wall.filter(ImageFilter.GaussianBlur(5))
blue = Image.new("RGB", (W, H), (7, 32, 68))
wall = Image.blend(wall, blue, 0.28)
wall = ImageEnhance.Contrast(wall).enhance(1.08)
wall.save(OUT / "assets" / "wall.jpg", quality=88)
print("wall ok")

# ---- digit strips: drifting film of photos inside the "2" and "5"
STRIP_W, STRIP_H, CELL_W, BLEND = 3200, 640, 460, 70
for digit in ("2", "5"):
    dst = OUT / "assets" / "strips" / f"d{digit}.jpg"
    pick = rng.sample(ids, 9)
    strip = np.zeros((STRIP_H, STRIP_W, 3), np.float32)
    weight = np.zeros((STRIP_H, STRIP_W, 1), np.float32)
    x = -BLEND
    for pid in pick:
        im = Image.open(SRC / f"assets/photos/{pid:03d}.jpg").convert("RGB")
        im = ImageEnhance.Color(im).enhance(0.88)
        a = np.asarray(im, np.float32)
        h, w = a.shape[:2]
        sc = STRIP_H / h
        nw = int(w * sc)
        a = np.asarray(Image.fromarray(a.astype(np.uint8)).resize((nw, STRIP_H), Image.Resampling.LANCZOS), np.float32)
        a = a[:, :, ::-1] * np.array([0.97, 1.0, 1.035], np.float32)
        g = np.random.default_rng(pid).normal(0, 2.0, a.shape).astype(np.float32)
        a = np.clip(a + g, 0, 255)
        tile = a[:, :CELL_W + BLEND] if a.shape[1] >= CELL_W + BLEND else np.pad(a, ((0, 0), (0, CELL_W + BLEND - a.shape[1]), (0, 0)), mode="edge")
        wgt = np.ones((STRIP_H, tile.shape[1], 1), np.float32)
        r = np.linspace(0, 1, BLEND, dtype=np.float32)[None, :, None]
        wgt[:, :BLEND] *= r
        wgt[:, -BLEND:] *= 1 - r
        x0 = max(0, x)
        x1 = min(STRIP_W, x + tile.shape[1])
        if x1 > x0:
            sx0, sx1 = x0 - x, x1 - x
            strip[:, x0:x1] += tile[:, sx0:sx1] * wgt[:, sx0:sx1]
            weight[:, x0:x1] += wgt[:, sx0:sx1]
        x += CELL_W
    strip /= np.maximum(weight, 1e-4)
    Image.fromarray(strip.astype(np.uint8)[:, :, ::-1]).save(dst, quality=88)
    print("strip", digit, "ok")

# ---- party emblem, stacked lockup (white-on-transparent PNG)
import base64
logo_b64 = base64.b64encode((BASE / "work" / "logo_new.png").read_bytes()).decode()
print("logo ok")

html = """<!doctype html><html lang="ru"><head><meta charset="utf-8"><script src="lib/gsap.min.js"></script>
<style>
@font-face{font-family:Unbounded;src:url('assets/fonts/Unbounded-SemiBold.ttf');font-weight:600}
*{box-sizing:border-box}html,body{margin:0;width:1920px;height:1080px;overflow:hidden;background:#04162e}
#root{position:relative;width:1920px;height:1080px;overflow:hidden;font-family:Unbounded;font-weight:600}
.wall{position:absolute;left:-60px;top:-60px;width:2040px;height:1200px;background:url('assets/wall.jpg') center/cover;will-change:transform}
.tint{position:absolute;inset:0;background:linear-gradient(180deg,rgba(4,18,40,.25) 0%,rgba(5,26,58,.55) 55%,rgba(3,14,32,.85) 100%)}
.halo{position:absolute;left:50%;top:44%;width:1700px;height:1000px;transform:translate(-50%,-50%);background:radial-gradient(closest-side,rgba(130,180,255,.16),rgba(130,180,255,0));will-change:opacity}
.vig{position:absolute;inset:0;background:radial-gradient(125% 95% at 50% 44%,rgba(0,0,0,0) 52%,rgba(1,8,20,.62) 100%)}
.dust{position:absolute;border-radius:50%;background:#cfe1ff;will-change:transform,opacity}
.lockup{position:absolute;inset:0;will-change:transform}
.brand{position:absolute;left:50%;top:64px;width:288px;height:296px;transform:translateX(-50%);filter:drop-shadow(0 18px 44px rgba(0,0,0,.55))}
.brand img{width:100%;height:100%;object-fit:contain;display:block}
.digits{position:absolute;left:0;right:0;top:352px;display:flex;justify-content:center;font-size:470px;line-height:0.92;letter-spacing:-30px}
.digit{display:block;background-size:auto 100%;background-repeat:repeat-x;-webkit-background-clip:text;background-clip:text;color:transparent;will-change:transform,filter,clip-path,background-position}
#d2{background-image:url('assets/strips/d2.jpg')}
#d5{background-image:url('assets/strips/d5.jpg')}
.line{position:absolute;left:0;right:0;top:762px;text-align:center;color:#fff;font-size:146px;line-height:1;white-space:nowrap}
.line span{display:inline-block;will-change:transform,filter,opacity}
.rule{position:absolute;left:50%;top:946px;width:260px;height:6px;margin-left:-130px;background:linear-gradient(90deg,transparent,#e13c4d 18%,#e13c4d 82%,transparent);transform-origin:center}
.over{position:absolute;left:0;right:0;top:982px;text-align:center;color:rgba(230,240,255,.85);font-size:27px;letter-spacing:10px}
.shine{position:absolute;left:-500px;top:280px;width:320px;height:600px;background:linear-gradient(90deg,rgba(255,255,255,0),rgba(255,255,255,.20),rgba(255,255,255,0));transform:rotate(-16deg);mix-blend-mode:screen}
.sweep{position:absolute;left:-600px;top:-400px;width:2500px;height:1900px;background:#d33442;transform-origin:50% 50%}
.white-sweep{position:absolute;left:-600px;top:-400px;width:2500px;height:1900px;background:#fff;transform-origin:50% 50%}
.fade{position:absolute;inset:0;background:#000;opacity:0;pointer-events:none}
</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="11" data-width="1920" data-height="1080" data-fps="60">
<div class="wall" id="f-wall"></div><div class="tint"></div><div class="halo" id="f-halo"></div><div id="dust"></div>
<div class="lockup" id="f-lock">
<div class="brand" id="f-brand">__LOGO__</div>
<div class="digits"><span class="digit" id="d2">2</span><span class="digit" id="d5">5</span></div>
<div class="line" id="f-line">__LETTERS__</div>
<div class="rule" id="f-rule"></div>
<div class="over" id="f-over">2001&nbsp;—&nbsp;2026&nbsp;&nbsp;·&nbsp;&nbsp;БОГОРОДСКИЙ&nbsp;ГОРОДСКОЙ&nbsp;ОКРУГ</div>
</div>
<div class="vig"></div>
<div class="shine" id="f-shine"></div>
<div class="white-sweep" id="f-ws"></div><div class="sweep" id="f-s"></div>
<div class="fade" id="f-fade"></div>
</div>
<script>
const tl=gsap.timeline({paused:true});
const dust=document.getElementById('dust');
const R=(s=>()=> (s=Math.imul(s^s>>>15,s|1),s^=s+Math.imul(s^s>>>7,s|61),((s^s>>>14)>>>0)/4294967296))(25);
for(let i=0;i<26;i++){const d=document.createElement('div');d.className='dust';const sz=2+R()*4;
d.style.width=d.style.height=sz+'px';d.style.left=(R()*1920)+'px';d.style.top=(R()*1080)+'px';d.style.opacity=0;
dust.appendChild(d);
tl.fromTo(d,{opacity:0,y:30},{opacity:0.06+R()*0.08,y:-60-R()*70,duration:8.5+R()*2,ease:'none'},0.4+R()*1.5);}

/* entry: wall settles, white+red wipes clear the frame */
tl.fromTo('#f-wall',{scale:1.16,x:26,y:-18},{scale:1.03,x:0,y:0,duration:10.4,ease:'sine.out'},0);
tl.fromTo('#f-halo',{opacity:0},{opacity:1,duration:2.2,ease:'sine.inOut'},0.4);
tl.fromTo('#f-ws',{x:2900,rotationZ:-15},{x:-3100,rotationZ:-15,duration:1.0,ease:'power3.inOut'},0);
tl.fromTo('#f-s',{x:3100,rotationZ:-15},{x:-3300,rotationZ:-15,duration:1.06,ease:'power3.inOut'},0.05);

/* emblem: soft landing */
tl.fromTo('#f-brand',{opacity:0,y:-30,scale:0.94},{opacity:1,y:0,scale:1,duration:1.0,ease:'back.out(1.4)'},0.5);

/* digits rise out of a masked field, strips drift against each other */
tl.fromTo('#d2',{clipPath:'inset(100% 0 0 0)',y:96,filter:'blur(18px)',opacity:0},{clipPath:'inset(0% 0 0 0)',y:0,filter:'blur(0px)',opacity:1,duration:1.2,ease:'power4.out'},0.8);
tl.fromTo('#d5',{clipPath:'inset(100% 0 0 0)',y:96,filter:'blur(18px)',opacity:0},{clipPath:'inset(0% 0 0 0)',y:0,filter:'blur(0px)',opacity:1,duration:1.2,ease:'power4.out'},0.95);
tl.fromTo('#d2',{backgroundPositionX:'0px'},{backgroundPositionX:'-1500px',duration:9.3,ease:'none'},1.1);
tl.fromTo('#d5',{backgroundPositionX:'-1500px'},{backgroundPositionX:'0px',duration:9.3,ease:'none'},1.1);

/* letters: per-letter rise, tracking settles via scale (transform, pixel-safe) */
const letters=document.querySelectorAll('#f-line span');
letters.forEach((el,i)=>{tl.fromTo(el,{y:54,opacity:0,filter:'blur(12px)',rotateX:38},{y:0,opacity:1,filter:'blur(0px)',rotateX:0,duration:0.75,ease:'power3.out'},2.15+i*0.055);});
tl.fromTo('#f-line',{scaleX:1.06},{scaleX:1.0,duration:1.6,ease:'power3.inOut',transformOrigin:'50% 50%'},2.15);

/* rule + credits */
tl.fromTo('#f-rule',{scaleX:0,opacity:0},{scaleX:1,opacity:1,duration:0.7,ease:'power3.out'},3.25);
tl.fromTo('#f-over',{opacity:0,scale:1.12},{opacity:1,scale:1.0,duration:1.0,ease:'power3.out'},3.5);

/* light pass over the lockup, then a long quiet breath */
tl.fromTo('#f-shine',{x:-500,opacity:0},{x:2450,opacity:1,duration:1.0,ease:'power2.inOut'},4.3);
tl.to('#f-shine',{opacity:0,duration:0.3},5.15);
tl.to('#f-lock',{scale:1.04,duration:5.3,ease:'sine.inOut'},5.2);

/* exit: fade to black so the video ends on a clean note */
tl.to('#f-fade',{opacity:1,duration:0.75,ease:'power2.in'},10.25);
tl.to({},{duration:11},0);
window.__timelines=window.__timelines||{};window.__timelines.main=tl;
</script></body></html>"""

letters = "".join(f"<span>{'&nbsp;' if ch == ' ' else ch}</span>" for ch in "лет вместе")
html = html.replace("__LOGO__", f'<img src="data:image/png;base64,{logo_b64}" alt="">').replace("__LETTERS__", letters)
(OUT / "index.html").write_text(html, encoding="utf-8")
print("outro v3 written")
