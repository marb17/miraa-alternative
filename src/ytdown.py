import yt_dlp
import json
import os
import re

from globalfuncs import base58_to_str, str_to_base58

with open('globalconfig.json', 'r') as f:
    config = json.load(f)

quiet_mode = bool(config['ytdown_quiet_mode'])

def extract_video_title(url: str) -> json:
    ydl_opts = {"quiet": quiet_mode}

    # get info as json
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        # output the title only
        return info["title"]

def get_audio(url: str, output_dir='../database/songs/'):
    # create new dir for specific song
    title = extract_video_title(url)
    # use base58 cuz no special characters
    title_enc = str_to_base58(title)

    print(title_enc, " | ", title)

    os.makedirs(output_dir, exist_ok=True)

    # save as wav
    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "wav",
            "preferredquality": "192",
        }],
        "outtmpl": f"{output_dir}/{title_enc}/{title_enc}",
        "quiet": quiet_mode,
    }

    # download
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # return the title
    return title, title_enc