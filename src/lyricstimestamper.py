import faster_whisper
import torch
import hf_xet
import gc
import json

# global config
with open('globalconfig.json', 'r') as f:
    config = json.load(f)

whisper_model = str(config["whisper_model"])
whisper_quiet_mode = bool(config["whisper_quiet_mode"])

# use cuda if avaliable
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def transcribe(filepath: str) -> json:
    model = faster_whisper.WhisperModel(whisper_model, device="cuda", compute_type='float16')

    #! do NOT change temperature out of 0 or omit, will crash
    result, info = model.transcribe(filepath, language="ja", word_timestamps=True, log_progress=whisper_quiet_mode, beam_size=5, temperature=0, vad_filter=True)

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

    # clear vram and cache for other models
    del model
    torch.cuda.empty_cache()
    gc.collect()

    return json.dumps(words_result, ensure_ascii=False, indent=2)