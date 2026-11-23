import sys
import zipfile
import subprocess
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context

stage = Path(__file__).resolve().parent
base = stage.parents[1]
sys.path.insert(0, str(base))
import render_cards as cards
cards.BASE = stage
cards.SRC = stage
(stage / "scenes").mkdir(exist_ok=True)
cards.cv2.setNumThreads(1)
names = ['дайверы.JPG', 'DSC_0031.JPG', 'DSC_0184.JPG', 'DSC_0068.JPG']
with zipfile.ZipFile(base.parent / 'фотки 2010-2016.zip') as archive:
    for i, name in enumerate(names):
        photo = stage / name
        photo.write_bytes(archive.read(name))
        cards.ROWS[100+i] = {'file':name}

jobs = [(100+i, {'id':f'archive-{i+1}', 'photo':100+i, 'duration':3.8}) for i in range(4)]
with ProcessPoolExecutor(max_workers=2, mp_context=get_context('fork')) as pool:
    paths = list(pool.map(cards.render_scene,jobs))
source = base.parent / '25_лет_вместе_2026_v2.mp4'
output = base.parent / '25_лет_вместе_2026_v3.mp4'
starts = [98.15,109.55,133.55,157.55]
inputs = ['-threads','2','-i',str(source)]
filters=[]
prev='[0:v]'
for i,(clip,start) in enumerate(zip(paths,starts),1):
    inputs += ['-threads','1','-i',clip]
    filters.append(f'[{i}:v]format=yuva420p,fade=t=in:d=0.5:alpha=1,fade=t=out:st=3.3:d=0.5:alpha=1,setpts=PTS+{start}/TB[p{i}]')
    filters.append(f'{prev}[p{i}]overlay=eof_action=pass:repeatlast=0:enable=between(t\\,{start}\\,{start+3.8})[o{i}]')
    prev=f'[o{i}]'
tmp=stage/'render.mp4'
subprocess.run(['ffmpeg','-v','error','-xerror','-y','-filter_complex_threads','2',*inputs,'-filter_complex',';'.join(filters),'-map',prev,'-map','0:a:0','-map_metadata','0','-c:v','libx264','-preset','veryfast','-threads','4','-b:v','2620k','-maxrate','4500k','-bufsize','9000k','-pix_fmt','yuv420p','-colorspace','bt709','-color_trc','bt709','-color_primaries','bt709','-c:a','copy','-movflags','+faststart','-progress',str(stage/'progress'),str(tmp)],check=True)
assert 130_000_000 <= tmp.stat().st_size <= 150_000_000,tmp.stat().st_size
tmp.replace(output)
print(output,output.stat().st_size)
