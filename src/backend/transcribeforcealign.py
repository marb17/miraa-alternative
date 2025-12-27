import globalfuncs
import json
import librosa
import numpy as np

import torch

torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True

from omegaconf.listconfig import ListConfig
from omegaconf.base import ContainerMetadata, Metadata
from omegaconf.nodes import AnyNode
from typing import Any
from collections import defaultdict
from pyannote.audio.core.model import Introspection
from pyannote.audio.core.task import Specifications, Problem, Resolution

# Fix for pyannote VAD loading
torch.serialization.add_safe_globals([ListConfig,ContainerMetadata,Any,list,defaultdict,dict,int,AnyNode,Metadata,torch.torch_version.TorchVersion,Introspection,Specifications,Problem,Resolution])

import whisperx

with open('../config/globalconfig.json', 'r') as f:
    config = json.load(f)

whisperx_batch_size = int(config['whisperx_batch_size'])

def transcribe_force_align(audio_path, lyrics_text, use_lyric=True, bad_result_threshold=0.4):
    y, sr = librosa.load(audio_path, sr=None)
    duration = librosa.get_duration(y=y, sr=sr)

    device = "cuda" if torch.cuda.is_available() else "cpu"

    model_dir = "../../model/whisperx"
    model = whisperx.load_model(
        "large-v2",
        device,
        compute_type='float16',
        download_root=model_dir
    )

    audio = whisperx.load_audio(audio_path)
    result = model.transcribe(audio, batch_size=whisperx_batch_size)
    globalfuncs.logger.verbose(str(result["segments"]))

    if use_lyric:
        for lyric, counter in zip(lyrics_text, range(len(lyrics_text))):
            lyrics_text[counter] = lyric + ' '

        str_lyrics = ''.join(lyrics_text)


        result['segments'] = [{
            "text": str_lyrics,
            "start": result['segments'][0]['start'],
            "end": duration,
        }]

    model_a, metadata = whisperx.load_align_model(language_code=result['language'], device=device)
    result = whisperx.align(result['segments'], model_a, metadata, audio, device, return_char_alignments=False)

    print(result['segments'])

    while True:
        last_result = result["segments"]
        new_segments = []

        for segment in last_result:
            is_valid = True

            for word in segment["words"]:
                if word["score"] < bad_result_threshold:
                    is_valid = False
                    break

            if is_valid:
                seg_start = segment['words'][0]['start']
                seg_end = segment['words'][-1]['end']
                seg_text = "".join(word["word"] for word in segment["words"])
                seg_words = segment['words']

                new_segments.append({
                    "start": seg_start,
                    "end": seg_end,
                    "text": seg_text,
                    "words": seg_words
                })
            else:
                def split_list_by_score_invalid(input_list):
                    for index, item in enumerate(input_list):
                        if item["score"] < bad_result_threshold:
                            return input_list[:index], input_list[index:]
                valid_part, invalid_part = split_list_by_score_invalid(segment['words'])

                # valid part
                seg_start = valid_part[0]['start']
                seg_end = valid_part[-1]['end']
                seg_text = "".join(word["word"] for word in valid_part)
                seg_words = valid_part

                new_segments.append({
                    "start": seg_start,
                    "end": seg_end,
                    "text": seg_text,
                    "words": seg_words
                })

                seg_start = seg_end
                seg_end = duration
                seg_text = "".join(word["word"] for word in invalid_part)
                seg_words = invalid_part

                new_segments.append({
                    "start": seg_start,
                    "end": seg_end,
                    "text": seg_text,
                    "words": seg_words
                })

        result = whisperx.align(new_segments, model_a, metadata, audio, device, return_char_alignments=False)

        everything_valid = True
        for segment in result["segments"]:
            for word in segment["words"]:
                if word["score"] < bad_result_threshold:
                    everything_valid = False
                    break

        if everything_valid:
            return result['segments']
        else:
            print(result['segments'])

if __name__ == '__main__':
    print(transcribe_force_align("../../database/songs/RzMh/audio_vocals_trans.wav", [
                "Taking off, taking off",
                "姿形の見えない魔物",
                "どこへでも連れて行くよ",
                "街を見下ろして",
                "Well, you are my star",
                "",
                "耳を塞いでも聞こえるの",
                "衝動の弾ける音が",
                "Uh, just a moment, du-ru-du, du-ru-du, du-ru-du",
                "I am just waiting for my, du-ru-du, du-ru-du, du-ru-du",
                "一瞬の静寂の匂い",
                "あなたを思い出す",
                "別れ際のあなたを思う",
                "金曜の午後の空想さ",
                "Give me a second, du-ru-du, du-ru-du, du-ru-du",
                "恋する白昼夢, du-ru-du, du-ru-du",
                "今は何をしているの？",
                "あなたが居ればどこでも行けてしまう",
                "",
                "急いで！",
                "Taking off, taking off",
                "姿形の見えない魔物",
                "耳を塞いでも聞こえる衝動の音",
                "You're just moving on, moving on",
                "今はどこか遠くへ逃げよう",
                "どこへでも連れて行くよ",
                "街を見下ろして",
                "You are my jet star",
                "",
                "一人きりの部屋で騒ぐ",
                "ひとりでに燃える鼓動さ",
                "Nobody like you, du-ru-du, du-ru-du, du-ru-du",
                "恋するダンスフロア, du-ru-du, du-ru-du, du-ru-du",
                "小さすぎる部屋",
                "ああ、私の知らないそんな顔しないで",
                "",
                "Loving you, loving you",
                "嘘も誠も要らない、up to you",
                "一人の部屋、続く夏の匂い",
                "I'm just moving on, moving on",
                "あなたに出会うまでは私",
                "ねえ、どんな顔をして生きてきたんだっけ？",
                "All I need is you",
                "",
                "Ladies and gentlemen",
                "For your comfort, we will be dimming the main cabin lights",
                "If you wish to continue reading, you will find your reading light",
                "In the panel above you, thank you",
                "",
                "Taking off, taking off",
                "姿形の見えない魔物",
                "耳を塞いでも聞こえる衝動の音",
                "You're just moving on, moving on",
                "口は災いのもとならば",
                "何も言わなくていいよ",
                "どこに行こう？",
                "Taking off, taking off",
                "今は明日まで待てない Taking a trip",
                "この夏が終わる前に",
                "私たちきっと会いましょう",
                "",
                "Ah-ah",
                "Du-ru-du, du-ru-du, du-ru-du",
                "Nobody like you, ooh-ooh, ooh-ooh",
                "Moving on, moving on",
                "Nobody like you are my star"
            ], use_lyric=True))