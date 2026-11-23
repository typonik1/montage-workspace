#!/usr/bin/env python3
import json, pathlib, sys
import numpy as np
import cv2
import onnxruntime as ort

BASE = pathlib.Path(__file__).parent
SRC = BASE.parent / "25_лет_вместе_только_исходники"
OUT = BASE / "work" / "depth"
OUT.mkdir(parents=True, exist_ok=True)

tl = json.loads((SRC / "timeline.json").read_text())
photos = json.loads((SRC / "photos.json").read_text())
rows = {p["id"]: p for p in photos}
need = sorted({s["photo"] for s in tl["scenes"] if "photo" in s})

sess = ort.InferenceSession(str(BASE / "models" / "depth_anything_v2_small.onnx"),
                            providers=["CPUExecutionProvider"])
inp = sess.get_inputs()[0]
print("model input:", inp.name, inp.shape, flush=True)

mean = np.array([0.485, 0.456, 0.406], np.float32)
std = np.array([0.229, 0.224, 0.225], np.float32)

for pid in need:
    dst = OUT / f"{pid:03d}.npy"
    if dst.exists():
        continue
    img = cv2.imread(str(SRC / rows[pid]["file"]), cv2.IMREAD_COLOR)
    h, w = img.shape[:2]
    scale = 518 / max(h, w)
    nh, nw = max(14, round(h * scale / 14) * 14), max(14, round(w * scale / 14) * 14)
    small = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    x = (small[:, :, ::-1].astype(np.float32) / 255 - mean) / std
    x = x.transpose(2, 0, 1)[None]
    d = sess.run(None, {inp.name: x})[0].squeeze()
    d = cv2.resize(d, (w, h), interpolation=cv2.INTER_CUBIC)
    lo, hi = np.percentile(d, 2), np.percentile(d, 98)
    d = np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1)
    np.save(dst, d.astype(np.float16))
    print(f"depth {pid:03d} {w}x{h}", flush=True)
print("depth pass complete", flush=True)