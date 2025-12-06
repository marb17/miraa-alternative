import globalfuncs
import json

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

def transcribe_force_align(audio_path, lyrics_text, use_lyric=True):
    device = "cuda" if torch.cuda.is_available() else "cpu"

    model_dir = "../../model/whisperx"
    model = whisperx.load_model(
        "large-v3",
        device,
        compute_type='float16',
        download_root=model_dir
    )

    audio = whisperx.load_audio(audio_path)
    result = model.transcribe(audio, batch_size=whisperx_batch_size)
    globalfuncs.logger.verbose(str(result["segments"]))

    if use_lyric:
        result["text"] = lyrics_text

    model_a, metadata = whisperx.load_align_model(language_code=result['language'], device=device)
    result = whisperx.align(result['segments'], model_a, metadata, audio, device, return_char_alignments=False)

    return result["segments"]