import faster_whisper
import torch
import hf_xet

import json

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = faster_whisper.WhisperModel('large-v3', device="cuda", compute_type='float16')
# model = faster_whisper.WhisperModel('small', device="cuda", compute_type='float16')

def transcribe(filepath: str):
    # do not change temperature out of 0 or omit, will crash
    result, info = model.transcribe(filepath, language="ja", word_timestamps=True, log_progress=True, beam_size=5, temperature=0, vad_filter=True)

    segments = list(result)  # consume generator immediately

    # collect words
    words_result = []
    for segment in segments:
        for word in segment.words:
            words_result.append({
                "start": word.start,
                "end": word.end,
                "word": word.word
            })

    return json.dumps(words_result, ensure_ascii=False, indent=2)
