import torch
import torchaudio
from demucs.pretrained import get_model
from demucs.apply import apply_model
import os
import gc
import json
import globalfuncs
from pedalboard import Pedalboard, Reverb
import soundfile

# global config
with open('../config/globalconfig.json', 'r') as f:
    config = json.load(f)

demucs_shifts = int(config["demucs_shifts"])
demucs_worker_num = int(config["demucs_worker_num"])
demucs_quiet_mode = bool(config["demucs_quiet_mode"])
demucs_model = str(config["demucs_model"])
demucs_model_2 = str(config["demucs_model_2"])
demucs_post_processing = bool(config["demucs_post_processing"])
demucs_ensemble = bool(config["demucs_ensemble"])
demucs_weight = float(config["demucs_weight"])
demucs_2_weight = float(config["demucs_2_weight"])
demucs_quiet_mode = not demucs_quiet_mode

def separate_audio(filepath: str, split=True, device="cuda" if torch.cuda.is_available() else "cpu") -> None:
    globalfuncs.logger.verbose(f"Post Processing: {demucs_post_processing}, Ensemble: {demucs_ensemble}, Models: '{demucs_model}' and '{demucs_model_2}'")

    # demucs model
    model = get_model(demucs_model)
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

    del model
    torch.cuda.empty_cache()
    gc.collect()

    vocals_trans = vocals.cpu().numpy()

    # post processing
    if demucs_post_processing:
        vocals_np = vocals.cpu().numpy()
        board = Pedalboard([Reverb(room_size=0.4, damping=0.2, wet_level=0.05)])
        vocals_np = board(vocals_np, sr)
    else:
        vocals_np = vocals.cpu().numpy()

    # ensemble mode to mix two models into one
    if demucs_ensemble:
        model_2 = get_model(demucs_model_2)
        model_2.to(device)

        sources_2 = apply_model(model_2, wav, split=split, device=device, shifts=demucs_shifts, progress=demucs_quiet_mode,
                              num_workers=demucs_worker_num)

        vocals_2 = sources_2[0, -1, :, :]
        vocals_2_np = vocals_2.cpu().numpy()

        if demucs_post_processing:
            vocals_2 = board(vocals_2_np, sr)

        final_vocals = demucs_weight * vocals_np + demucs_2_weight * vocals_2_np
        final_vocals = board(final_vocals, sr)

        del model_2
        torch.cuda.empty_cache()
        gc.collect()
    else:
        final_vocals = vocals_np

    # save path
    base = os.path.splitext(filepath)[0]
    out_path = f"{base}_vocals.wav"
    out_path_for_trans = f"{base}_vocals_trans.wav"

    soundfile.write(out_path, final_vocals.T, sr)
    soundfile.write(out_path_for_trans, vocals_trans.T, sr)
    globalfuncs.logger.success(f"Saved vocals -> {out_path}")

    torch.cuda.empty_cache()
    gc.collect()