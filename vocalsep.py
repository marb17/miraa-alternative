import torch
import torchaudio
from demucs.pretrained import get_model
from demucs.apply import apply_model
import os
import gc
import json

# global config
with open('globalconfig.json', 'r') as f:
    config = json.load(f)

demucs_shifts = int(config["demucs_shifts"])
demucs_worker_num = int(config["demucs_worker_num"])
demucs_quiet_mode = bool(config["demucs_quiet_mode"])
demucs_model = str(["demucs_model"])

def separate_audio(filepath: str, split=True, device="cuda" if torch.cuda.is_available() else "cpu") -> None:
    # demucs model
    model = get_model("mdx_extra_q")
    model.to(device)

    # get abs path
    filepath = os.path.abspath(filepath)

    # load audio
    wav, sr = torchaudio.load(filepath)

    # make sure stereo
    if wav.shape[0] == 1:
        wav = wav.repeat(2, 1)

    wav = wav.unsqueeze(0).to(device)

    # split
    sources = apply_model(model, wav, split=split, device=device, shifts=demucs_shifts, progress=demucs_quiet_mode, num_workers=demucs_worker_num)

    # only get vocals
    vocals = sources[0, -1, :, :]

    # save
    base = os.path.splitext(filepath)[0]
    out_path = f"{base}_vocals.wav"
    torchaudio.save(out_path, vocals.cpu(), sr)
    print(f"Saved vocals -> {out_path}")

    # delete model
    del model
    torch.cuda.empty_cache()
    gc.collect()