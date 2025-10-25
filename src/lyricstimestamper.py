import faster_whisper
import torch
import hf_xet
import gc
import json

# global config
with open('../config/globalconfig.json', 'r') as f:
    config = json.load(f)

whisper_model = str(config["whisper_model"])
whisper_quiet_mode = bool(config["whisper_quiet_mode"])

whisper_quiet_mode = not whisper_quiet_mode

# use cuda if avaliable
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# main functions
def transcribe(filepath: str) -> json:
    model = faster_whisper.WhisperModel(whisper_model, device="cuda", compute_type='float16')

    result, info = model.transcribe(filepath, language="ja", word_timestamps=True, log_progress=whisper_quiet_mode, beam_size=10, temperature=0, vad_filter=True, best_of=4)

    segments = list(result)  # consume generator immediately

    # collect words
    words_result = []
    lyrics_result = []
    for segment in segments:
        lyrics_result.append(
            [
                segment.start,
                segment.end,
                segment.text,
            ]
        )
        for word in segment.words:
            words_result.append(
                [
                    word.start,
                    word.end,
                    word.word
                ]
            )

    # clear vram and cache for other models
    del model
    torch.cuda.empty_cache()
    gc.collect()

    return words_result, lyrics_result