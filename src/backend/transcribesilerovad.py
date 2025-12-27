import globalfuncs

import torch
import torchaudio
from silero_vad import get_speech_timestamps

model, utils = torch.hub.load(
    repo_or_dir='snakers4/silero-vad',
    model='silero_vad'
)


(get_speech_timestamps, _, _, _, _) = utils

wav, sr = torchaudio.load("../../database/songs/RzMh/audio_vocals.wav")
timestamps = get_speech_timestamps(
    wav[0],
    model,
    sampling_rate=sr,
    min_speech_duration_ms=400,
    min_silence_duration_ms=350,
    speech_pad_ms=120
)

def merge_segments(segs, max_gap=0.25):
    merged = [segs[0]]
    for seg in segs[1:]:
        gap = (seg['start'] - merged[-1]['end']) / sr
        if gap < max_gap:
            merged[-1]['end'] = seg['end']
        else:
            merged.append(seg)
    return merged

print(merge_segments(timestamps))
print(timestamps)

sec_timestamps = []
for item in timestamps:
    sec_timestamps.append({"start":item['start'] / sr, "end":item['end'] / sr})

print(sec_timestamps)