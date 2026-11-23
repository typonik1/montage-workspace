#!/usr/bin/env python3
import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

BASE = Path(__file__).resolve().parent
SRC = BASE.parent / "25_лет_вместе_только_исходники"
WORK = BASE / "work"
SEGMENTS = WORK / "delivery_segments"
FINAL = BASE.parent / "25_лет_вместе_2026_v2.mp4"
FPS = 60


@dataclass(frozen=True)
class Clip:
    path: Path
    start: int
    frames: int

    @property
    def end(self):
        return self.start + self.frames


def video_frames(path):
    if not path.is_file():
        return None
    info = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=nb_frames", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    count = info.stdout.strip()
    return int(count) if info.returncode == 0 and count.isdigit() else None


def seconds(frames):
    return f"{frames / FPS:.6f}"


def dissolve(clips, start):
    inputs = []
    graph = []
    previous = "[0:v]"
    previous_end = clips[0].end
    for i, clip in enumerate(clips):
        seek_frames = max(0, start - clip.start)
        if seek_frames:
            # Round down so a frame at this position survives input seeking.
            seek = (seek_frames * 1_000_000 // FPS) / 1_000_000
            inputs += ["-ss", f"{seek:.6f}"]
        inputs += ["-threads", "1", "-i", str(clip.path)]
        if i:
            overlap = previous_end - clip.start
            if overlap <= 0:
                raise ValueError(f"No overlap before {clip.path.name}: {overlap} frames")
            output = f"[fade{i}]"
            graph.append(
                f"{previous}[{i}:v]xfade=transition=fade:"
                f"duration={seconds(overlap)}:offset={seconds(clip.start - start)}{output}"
            )
            previous = output
        previous_end = clip.end
    filters = ["-filter_complex", ";".join(graph), "-map", previous] if graph else ["-map", "0:v:0"]
    return inputs, filters


def run_ffmpeg(options, label):
    print(label, flush=True)
    subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-y", "-filter_complex_threads", "2",
         "-stats_period", "5", "-progress", str(WORK / "assemble.progress")] + options,
        check=True,
    )


def require_frames(path, expected):
    actual = video_frames(path)
    if actual != expected:
        raise ValueError(f"{path.name}: expected {expected} video frames, found {actual}")


def reusable(path, frames, sources):
    if video_frames(path) != frames:
        return False
    stamp = path.stat().st_mtime_ns
    return all(not source.exists() or source.stat().st_mtime_ns <= stamp for source in sources)


def render_segment(clips, start, frames, path):
    inputs, filters = dissolve(clips, start)
    video = filters + [
        "-an", "-frames:v", str(frames), "-c:v", "libx264",
        "-preset", "veryfast", "-threads", "4", "-profile:v", "high", "-level:v", "4.2",
        "-b:v", "3400k", "-maxrate", "5200k", "-bufsize", "10400k",
        "-pix_fmt", "yuv420p", "-r", str(FPS), "-video_track_timescale", "15360",
        "-colorspace", "bt709", "-color_trc", "bt709", "-color_primaries", "bt709",
        "-color_range", "tv",
    ]
    with TemporaryDirectory(prefix="segment-", dir=WORK) as stage:
        passlog = ["-passlogfile", str(Path(stage) / "x264")]
        output = Path(stage) / path.name
        run_ffmpeg(inputs + video + passlog + ["-pass", "1", "-f", "null", "-"],
                   f"{path.name}, pass 1/2")
        run_ffmpeg(inputs + video + passlog + ["-pass", "2", str(output)],
                   f"{path.name}, pass 2/2")
        require_frames(output, frames)
        output.replace(path)


def main():
    parser = argparse.ArgumentParser(description="Assemble the build25 video from available renders.")
    parser.add_argument("--audio", type=Path, default=BASE / "mix.m4a")
    args = parser.parse_args()
    SEGMENTS.mkdir(parents=True, exist_ok=True)
    timeline_path = SRC / "timeline.json"
    timeline = json.loads(timeline_path.read_text())
    photos = [s for s in timeline["scenes"] if "photo" in s]
    scenes = [
        Clip(BASE / "scenes" / f"{i:03d}_{s['id']}.mp4",
             round(s["start"] * FPS), round(s["duration"] * FPS))
        for i, s in enumerate(photos)
    ]

    intro_path, outro_path = BASE / "intro.mp4", BASE / "outro.mp4"
    intro_frames, outro_frames = video_frames(intro_path), video_frames(outro_path)
    if not intro_frames or not outro_frames:
        raise SystemExit("Missing or incomplete intro/outro")
    intro = Clip(intro_path, 0, intro_frames)
    finale = next(s for s in timeline["scenes"] if s.get("kind") == "logo-outro")
    outro = Clip(outro_path, round(finale["start"] * FPS), outro_frames)

    groups = []
    for i in range(0, len(scenes), 10):
        group = scenes[i:i + 10]
        start = group[0].start
        chunk_path = BASE / "chunks" / f"chunk_{i:03d}.mp4"
        chunk_frames = group[-1].end - start
        if reusable(chunk_path, chunk_frames, [timeline_path, *(clip.path for clip in group)]):
            group = [Clip(chunk_path, start, chunk_frames)]
        groups.append(group)
    groups[0].insert(0, intro)
    groups[-1].append(outro)

    outputs = []
    pending = []
    for i, group in enumerate(groups):
        start = group[0].start
        end = groups[i + 1][0].start if i + 1 < len(groups) else outro.end
        frames = end - start
        path = SEGMENTS / f"segment_{i:02d}.mp4"
        clips = [groups[i - 1][-1], *group] if i else group
        if reusable(path, frames, [timeline_path, *(clip.path for clip in clips)]):
            print(f"Reuse {path.name}", flush=True)
        else:
            missing = [clip.path.name for clip in clips if video_frames(clip.path) != clip.frames]
            if missing:
                pending.extend(missing)
                continue
            render_segment(clips, start, frames, path)
        outputs.append((path, frames))

    if pending:
        print("Waiting for scenes: " + ", ".join(pending), flush=True)
        return 2
    if not args.audio.is_file():
        raise SystemExit(f"Missing audio mix: {args.audio}")

    credit = (SRC / "MUSIC_CREDIT.txt").read_text().strip().replace("\n", " ")
    with TemporaryDirectory(prefix="assemble-", dir=WORK) as stage:
        manifest = Path(stage) / "segments.ffconcat"
        lines = ["ffconcat version 1.0"]
        for path, frames in outputs:
            lines += [f"file '../delivery_segments/{path.name}'", f"duration {seconds(frames)}"]
        manifest.write_text("\n".join(lines) + "\n")
        output = Path(stage) / FINAL.name
        run_ffmpeg(
            ["-f", "concat", "-safe", "0", "-i", str(manifest), "-i", str(args.audio),
             "-map", "0:v:0", "-map", "1:a:0", "-c", "copy", "-movflags", "+faststart",
             "-metadata", "title=25 лет вместе — Единая Россия, Ногинское отделение",
             "-metadata", f"comment={credit}", str(output)],
            "Mux final MP4",
        )
        require_frames(output, outro.end)
        output.replace(FINAL)
    print(f"FINAL {FINAL} {FINAL.stat().st_size}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
