from fractions import Fraction
import sys

import av
import numpy as np

main, ending, output = sys.argv[1:]
splice = 179.08


def nearby_frames(path, seconds):
    with av.open(path) as video:
        stream = video.streams.video[0]
        video.seek(int(Fraction(max(0, seconds - 1)) / stream.time_base), stream=stream)
        frames = []
        for frame in video.decode(stream):
            if frame.time < seconds - 0.065:
                continue
            if frame.time > seconds + 0.065:
                break
            gray = frame.reformat(width=256, height=144, format='gray').to_ndarray()
            frames.append((frame.time, gray.astype(np.float32)))
        return frames


def verify_picture(source, source_time, output_time):
    candidates = nearby_frames(source, source_time)
    appended = min(nearby_frames(output, output_time), key=lambda f: abs(f[0] - output_time))[1]
    error = min(float(np.abs(appended - image).mean()) for _, image in candidates)
    print(f'Video {output_time:.2f}s, mean luma error {error:.2f}/255')
    assert error < 6.0


def wave_samples(path):
    with av.open(path) as media:
        resampler = av.AudioResampler(format='fltp', layout='mono', rate=8000)
        result = [r.to_ndarray()[0] for frame in media.decode(audio=0) for r in resampler.resample(frame)]
        return np.concatenate(result).astype(np.float64)


def verify_sound(source, source_start, output_start, reference):
    rate = 8000
    radius = rate // 20
    source_audio = wave_samples(source)
    clip_length = 2 * rate
    offset = output_start - source_start
    starts = range(rate, len(source_audio) - clip_length - rate, 2 * rate)
    strongest = max(starts, key=lambda i: float(np.linalg.norm(source_audio[i:i + clip_length])))
    target = source_audio[strongest:strongest + clip_length]
    start = strongest + round(offset * rate)
    output_start = start / rate
    if np.linalg.norm(target) == 0:
        assert np.max(np.abs(reference[start:start + clip_length])) < 1e-4
        print(f'Audio {output_start:.2f}s, preserved digital silence')
        return
    sample = reference[start - radius:start + len(target) + radius]
    numerators = np.correlate(sample, target, mode='valid')
    cumulative = np.concatenate(([0], np.cumsum(sample * sample)))
    denominator = np.linalg.norm(target) * np.sqrt(cumulative[len(target):] - cumulative[:-len(target)])
    matches = np.divide(numerators, denominator, out=np.zeros_like(numerators), where=denominator > 1e-9)
    best = int(np.argmax(matches))
    print(f'Audio {output_start:.2f}s, correlation {matches[best]:.3f}, alignment error {(best-radius)/rate*1000:.1f} ms')
    assert matches[best] > 0.90


for source, local, global_time in [(main, 4.0, 4.0), (main, 178.6, 178.6),
                                   (ending, 0.9, splice + 0.9), (ending, 38.4, splice + 38.4)]:
    verify_picture(source, local, global_time)
reference = wave_samples(output)
verify_sound(main, 9.0, 9.0, reference)
verify_sound(ending, 25.4, splice + 25.4, reference)
