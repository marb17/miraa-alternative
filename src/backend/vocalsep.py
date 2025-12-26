import torch
import torchaudio
from demucs.pretrained import get_model
from demucs.apply import apply_model
import os
import gc
import json
import globalfuncs
from pedalboard import Pedalboard, Reverb, PeakFilter, NoiseGate, HighpassFilter, LowpassFilter
import soundfile
import numpy as np

# global config
with open('../config/globalconfig.json', 'r') as f:
    config = json.load(f)

demucs_shifts = int(config["demucs_shifts"])
demucs_worker_num = int(config["demucs_worker_num"])
demucs_quiet_mode = bool(config["demucs_quiet_mode"])
demucs_model = str(config["demucs_model"])
demucs_model_2 = str(config["demucs_model_2"])
demucs_post_processing = bool(config["demucs_post_processing"])
demucs_weight = float(config["demucs_weight"])
demucs_2_weight = float(config["demucs_2_weight"])
ensemble_gamma = float(config["ensemble_gamma"])
demucs_quiet_mode = not demucs_quiet_mode

def separate_audio(filepath: str, split=True, device="cuda" if torch.cuda.is_available() else "cpu", avg_method='weighted_median') -> None:
    window = torch.hann_window(4096, device=device)

    def stft(x):
        return torch.stft(
            x,
            n_fft=4096,
            hop_length=1024,
            window=window,
            center=True,
            return_complex=True
        )

    def istft(x, length):
        return torch.istft(
            x,
            n_fft=4096,
            hop_length=1024,
            window=window,
            center=True,
            length=length
        )

    globalfuncs.logger.verbose(f"Post Processing: {demucs_post_processing}, Ensemble: {demucs_ensemble}, Models: '{demucs_model}' and '{demucs_model_2}'")

    # demucs model
    model = get_model(demucs_model)
    model.to(device)

    # get abs path
    filepath = os.path.abspath(filepath)

    # load audio
    wav, sr = torchaudio.load(filepath)

    wav = wav.to(device)
    mix_spec = stft(wav[0])

    # make sure stereo
    if wav.shape[0] == 1:
        wav = wav.repeat(2, 1)

    wav = wav.unsqueeze(0).to(device)

    # split
    sources = apply_model(model, wav, split=split, device=device, shifts=demucs_shifts, progress=demucs_quiet_mode, num_workers=demucs_worker_num)

    # only get vocals
    vocals = sources[0, -1, :, :]
    voc_spec = stft(vocals)

    vocals = vocals.to(device)
    mix_spec = mix_spec.to(device)
    voc_spec = voc_spec.to(device)

    mask_1 = torch.abs(voc_spec) / (torch.abs(mix_spec) + 1e-8)
    mask_1 = torch.clamp(mask_1, 0.01, 1)

    del model
    torch.cuda.empty_cache()
    gc.collect()

    vocals_trans = vocals.cpu().numpy()

    board = Pedalboard([
        Reverb(
            room_size=0.4,
            damping=0.2,
            wet_level=0.05),
        PeakFilter(
            cutoff_frequency_hz=3500,
            gain_db=6,
            q=0.7),
        PeakFilter(
            cutoff_frequency_hz=7500,
            gain_db=-4,
            q=2.5),
        PeakFilter(
            cutoff_frequency_hz=750,
            gain_db=-3,
            q=2.0),
        NoiseGate(
            threshold_db=-52.5,
            ratio=5.0,
            attack_ms=2.5,
            release_ms=150),
        HighpassFilter(110),
        LowpassFilter(11000),
    ])

    vocals_np = vocals.cpu().numpy()

    # ensemble mode to mix two models into one
    model_2 = get_model(demucs_model_2)
    model_2.to(device)

    sources_2 = apply_model(model_2, wav, split=split, device=device, shifts=demucs_shifts, progress=demucs_quiet_mode,
                            num_workers=demucs_worker_num)

    vocals_2 = sources_2[0, -1, :, :]
    voc_spec_2 = stft(vocals_2)

    mask_2 = torch.abs(voc_spec_2) / (torch.abs(mix_spec) + 1e-8)
    mask_2 = torch.clamp(mask_2, 0, 1)
    vocals_2_np = vocals_2.cpu().numpy()

    stack = torch.stack([mask_1, mask_2], dim=0)
    weights = torch.tensor([demucs_weight, demucs_2_weight], device=stack.device)

    sorted_idx = torch.argsort(stack, dim=0)
    sorted_masks = torch.gather(stack, 0, sorted_idx)

    sorted_weights = weights[sorted_idx]
    cum_weights = torch.cumsum(sorted_weights, dim=0)

    cutoff = weights.sum() / 2
    median_idx = torch.argmax((cum_weights >= cutoff).int(), dim=0)

    ensemble_mask = torch.gather(
        sorted_masks,
        0,
        median_idx.unsqueeze(0)
    )[0]

    gamma = ensemble_gamma
    ensemble_mask = ensemble_mask ** gamma

    vocal_mask = ensemble_mask
    inst_mask = 1.0 - vocal_mask

    inst_mask = inst_mask ** gamma

    inst_mask = torch.clamp(inst_mask, 0, 1)

    ensemble_mask = torch.clamp(ensemble_mask, 0, 1)

    final_spec = mix_spec * ensemble_mask
    final_vocals = istft(final_spec, wav.shape[-1])
    final_vocals = final_vocals.cpu().numpy()

    inst_spec = mix_spec * inst_mask
    instrumental = istft(inst_spec, wav.shape[-1])
    instrumental = instrumental.cpu().numpy()

    del model_2
    torch.cuda.empty_cache()
    gc.collect()

    final_vocals = board(final_vocals, sr)

    # save path
    base = os.path.splitext(filepath)[0]
    out_path = f"{base}_vocals.wav"
    out_path_for_trans = f"{base}_vocals_trans.wav"
    out_path_for_inst = f"{base}_inst.wav"

    soundfile.write(out_path, final_vocals.T, sr)
    soundfile.write(out_path_for_trans, vocals_trans.T, sr)
    soundfile.write(out_path_for_inst, instrumental.T, sr)
    globalfuncs.logger.success(f"Saved vocals -> {out_path}")

    torch.cuda.empty_cache()
    gc.collect()