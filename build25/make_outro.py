#!/usr/bin/env python3
import json, pathlib, random, re, shutil
import numpy as np
from PIL import Image, ImageEnhance

BASE = pathlib.Path(__file__).parent
SRC = BASE.parent / "25_лет_вместе_только_исходники"
OLD = BASE.parent / "party25"
OUT = BASE / "outro"
(OUT / "assets" / "strips").mkdir(parents=True, exist_ok=True)
(OUT / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
(OUT / "lib").mkdir(parents=True, exist_ok=True)
gsap = OUT / "lib" / "gsap.min.js"
if not gsap.is_file():
    shutil.copy(OLD / "lib" / "gsap.min.js", gsap)
shutil.copy(SRC / "assets" / "fonts" / "Unbounded-SemiBold.ttf", OUT / "assets" / "fonts" / "Unbounded-SemiBold.ttf")

photos = json.loads((SRC / "photos.json").read_text())
ids = [p["id"] for p in photos]
rng = random.Random(7)

STRIP_W, STRIP_H, CELL_W, BLEND = 3200, 640, 460, 70
for digit in ("2", "5"):
    dst = OUT / "assets" / "strips" / f"d{digit}.jpg"
    pick = rng.sample(ids, 9)
    strip = np.zeros((STRIP_H, STRIP_W, 3), np.float32)
    weight = np.zeros((STRIP_H, STRIP_W, 1), np.float32)
    x = -BLEND
    for k, pid in enumerate(pick):
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

svg = (OLD / "compositions" / "logo-finale.html").read_text(encoding="utf-8")
svg = svg[svg.index("<svg"):svg.index("</svg>") + 6]
sym = svg[svg.index('<g id="brand-symbol">'):svg.index('<g id="brand-name">')]
sym = sym.replace('<g id="brand-symbol">', '').rstrip()
assert sym.endswith("</g>")
sym = sym[:-4]
sym = sym.replace('<path d="M64.6042', '<path fill-rule="evenodd" d="M64.6042')
name = svg[svg.index('<g id="brand-name">'):svg.index("</g></g>")]
name = name.replace('<g id="brand-name">', '').rstrip()
svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 170 175" fill="none">'
       f'<g transform="translate(30,0) scale(1.5)">{sym}</g>'
       f'<g transform="translate(-81.5,106)">{name}</g></svg>')
print("logo: stacked lockup per reference, bear torso cut out")

html = """<!doctype html><html lang="ru"><head><meta charset="utf-8"><script src="lib/gsap.min.js"></script>
<style>
@font-face{font-family:Unbounded;src:url('assets/fonts/Unbounded-SemiBold.ttf');font-weight:600}
*{box-sizing:border-box}html,body{margin:0;width:1920px;height:1080px;overflow:hidden;background:#07254a}
#root{position:relative;width:1920px;height:1080px;overflow:hidden;font-family:Unbounded;font-weight:600}
.field{position:absolute;inset:0;background:linear-gradient(180deg,#0a2c58 0%,#083b79 52%,#052449 100%)}
.glow{position:absolute;left:50%;top:46%;width:1500px;height:900px;transform:translate(-50%,-50%);background:radial-gradient(closest-side,rgba(120,170,255,.14),rgba(120,170,255,0))}
.vig{position:absolute;inset:0;background:radial-gradient(120% 90% at 50% 45%,rgba(0,0,0,0) 55%,rgba(2,10,26,.55) 100%)}
.dust{position:absolute;border-radius:50%;background:#cfe1ff;will-change:transform,opacity}
.lockup{position:absolute;inset:0;will-change:transform}
.brand{position:absolute;left:50%;top:58px;width:292px;height:300px;transform:translateX(-50%)}
.brand svg{width:100%;height:100%;display:block}
.digits{position:absolute;left:0;right:0;top:352px;display:flex;justify-content:center;gap:0;font-size:470px;line-height:0.92;letter-spacing:-30px}
.digit{display:block;background-size:auto 100%;background-repeat:no-repeat;-webkit-background-clip:text;background-clip:text;color:transparent;will-change:transform,filter,clip-path,background-position}
#d2{background-image:url('assets/strips/d2.jpg')}
#d5{background-image:url('assets/strips/d5.jpg')}
.line{position:absolute;left:0;right:0;top:760px;text-align:center;color:#fff;font-size:148px;line-height:1;letter-spacing:18px;white-space:nowrap}
.line span{display:inline-block;will-change:transform,filter,opacity}
.rule{position:absolute;left:50%;top:944px;width:240px;height:6px;margin-left:-120px;background:#e13c4d;transform-origin:center}
.over{position:absolute;left:0;right:0;top:980px;text-align:center;color:rgba(230,240,255,.82);font-size:27px;letter-spacing:10px}
.shine{position:absolute;left:-500px;top:300px;width:300px;height:560px;background:linear-gradient(90deg,rgba(255,255,255,0),rgba(255,255,255,.22),rgba(255,255,255,0));transform:rotate(-16deg);mix-blend-mode:screen}
.sweep{position:absolute;left:-600px;top:-400px;width:2500px;height:1900px;background:#d33442;transform-origin:50% 50%}
.white-sweep{position:absolute;left:-600px;top:-400px;width:2500px;height:1900px;background:#fff;transform-origin:50% 50%}
</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="11" data-width="1920" data-height="1080" data-fps="60">
<div class="field" id="f-field"><div class="glow"></div><div id="dust"></div>
<div class="lockup" id="f-lock">
<div class="brand" id="f-brand">__SVG__</div>
<div class="digits"><span class="digit" id="d2">2</span><span class="digit" id="d5">5</span></div>
<div class="line" id="f-line"><span id="w-let">лет</span>&nbsp;<span id="w-vm">вместе</span></div>
<div class="rule" id="f-rule"></div>
<div class="over" id="f-over">2001&nbsp;—&nbsp;2026&nbsp;&nbsp;·&nbsp;&nbsp;БОГОРОДСКИЙ&nbsp;ГОРОДСКОЙ&nbsp;ОКРУГ</div>
</div>
<div class="vig"></div>
<div class="shine" id="f-shine"></div>
</div>
<div class="white-sweep" id="f-ws"></div><div class="sweep" id="f-s"></div>
</div>
<script>
const tl=gsap.timeline({paused:true});
const dust=document.getElementById('dust');
const R=(s=>()=> (s=Math.imul(s^s>>>15,s|1),s^=s+Math.imul(s^s>>>7,s|61),((s^s>>>14)>>>0)/4294967296))(25);
for(let i=0;i<22;i++){const d=document.createElement('div');d.className='dust';const sz=2+R()*4;
d.style.width=d.style.height=sz+'px';d.style.left=(R()*1920)+'px';d.style.top=(R()*1080)+'px';d.style.opacity=0;
dust.appendChild(d);
tl.fromTo(d,{opacity:0,y:30},{opacity:0.05+R()*0.07,y:-50-R()*60,duration:9+R()*2,ease:'none'},0.4+R()*1.5);}
tl.fromTo('#f-field',{clipPath:'polygon(100% 0,100% 0,100% 100%,100% 100%)'},{clipPath:'polygon(0% 0,100% 0,100% 100%,-12% 100%)',duration:1.0,ease:'power3.inOut'},0);
tl.fromTo('#f-ws',{x:2900,rotationZ:-15},{x:-3100,rotationZ:-15,duration:1.05,ease:'power3.inOut'},0);
tl.fromTo('#f-s',{x:3100,rotationZ:-15},{x:-3300,rotationZ:-15,duration:1.1,ease:'power3.inOut'},.04);
tl.fromTo('#f-brand',{opacity:0,y:-26,scale:0.96},{opacity:1,y:0,scale:1,duration:0.9,ease:'power3.out'},0.55);
tl.fromTo('#d2',{clipPath:'inset(100% 0 0 0)',y:90,filter:'blur(16px)',opacity:0},{clipPath:'inset(0% 0 0 0)',y:0,filter:'blur(0px)',opacity:1,duration:1.15,ease:'power4.out'},0.85);
tl.fromTo('#d5',{clipPath:'inset(100% 0 0 0)',y:90,filter:'blur(16px)',opacity:0},{clipPath:'inset(0% 0 0 0)',y:0,filter:'blur(0px)',opacity:1,duration:1.15,ease:'power4.out'},1.0);
tl.fromTo('#d2',{backgroundPositionX:'0px'},{backgroundPositionX:'-1400px',duration:9.6,ease:'none'},1.2);
tl.fromTo('#d5',{backgroundPositionX:'-1400px'},{backgroundPositionX:'0px',duration:9.6,ease:'none'},1.2);
tl.fromTo('#w-let',{y:46,opacity:0,filter:'blur(10px)'},{y:0,opacity:1,filter:'blur(0px)',duration:0.8,ease:'power3.out'},2.25);
tl.fromTo('#w-vm',{y:46,opacity:0,filter:'blur(10px)'},{y:0,opacity:1,filter:'blur(0px)',duration:0.8,ease:'power3.out'},2.4);
tl.fromTo('#f-line',{letterSpacing:'18px'},{letterSpacing:'-5px',duration:1.5,ease:'power3.inOut'},2.25);
tl.fromTo('#f-rule',{scaleX:0},{scaleX:1,duration:0.6,ease:'power3.out'},3.35);
tl.fromTo('#f-over',{opacity:0,letterSpacing:'14px'},{opacity:1,letterSpacing:'4px',duration:0.9,ease:'power3.out'},3.55);
tl.fromTo('#f-shine',{x:-500,opacity:0},{x:2400,opacity:1,duration:0.9,ease:'power2.inOut'},4.35);
tl.to('#f-shine',{opacity:0,duration:0.25},5.1);
tl.to('#f-lock',{scale:1.035,duration:5.6,ease:'sine.inOut'},5.2);
tl.to({},{duration:11},0);
window.__timelines=window.__timelines||{};window.__timelines.main=tl;
</script></body></html>"""
html = html.replace("__SVG__", svg)
(OUT / "index.html").write_text(html, encoding="utf-8")
print("outro v2 written")