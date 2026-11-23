from pathlib import Path
import sys
import wave
import json

from faster_whisper import BatchedInferencePipeline, WhisperModel
import numpy as np

source = Path(sys.argv[1])
result = Path(sys.argv[2])
with wave.open(str(source), 'rb') as audio:
    assert audio.getframerate() == 16000 and audio.getsampwidth() == 2
    pcm = np.frombuffer(audio.readframes(audio.getnframes()), dtype='<i2')
    samples = pcm.reshape(-1, audio.getnchannels()).astype(np.float32).mean(axis=1) / 32768

model = WhisperModel('small', device='cpu', compute_type='int8', cpu_threads=4, local_files_only=True)
segments, _ = BatchedInferencePipeline(model).transcribe(samples, language='ru', batch_size=4, beam_size=3, word_timestamps=True)
with result.open('w', encoding='utf-8') as out:
    for segment in segments:
        line = {'start': segment.start, 'end': segment.end, 'text': segment.text,
                'words': [{'start': word.start, 'end': word.end, 'word': word.word} for word in segment.words]}
        out.write(json.dumps(line, ensure_ascii=False) + '\n')
        print(f'{segment.start:.2f}–{segment.end:.2f} {segment.text}', flush=True)
