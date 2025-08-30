import torch
import torchaudio
from demucs.pretrained import get_model
from demucs.apply import apply_model
import os

from globalfuncs import base58_to_str, str_to_base58

def seperate_audio(filepath, split=True, device="cuda" if torch.cuda.is_available() else "cpu"):
    # demucs model
    model = get_model("mdx_extra_q")
    model.to(device)

    # get abs path
    filepath = os.path.abspath(filepath)

    # load audio
    wav, sr = torchaudio.load(filepath)

    # make sure strero
    if wav.shape[0] == 1:
        wav = wav.repeat(2, 1)

    wav = wav.unsqueeze(0).to(device)

    # split
    sources = apply_model(model, wav, split=split, device=device, shifts=3, progress=True)

    # only get vocals
    vocals = sources[0, -1, :, :]

    # save
    base = os.path.splitext(filepath)[0]
    out_path = f"{base}_vocals.wav"
    torchaudio.save(out_path, vocals.cpu(), sr)
    print(f"Saved vocals -> {out_path}")

    return vocals
