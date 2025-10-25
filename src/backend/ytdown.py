import yt_dlp
import json
import os
from globalfuncs import str_to_base58
import globalfuncs


# global config
with open('../config/globalconfig.json', 'r') as f:
    config = json.load(f)

quiet_mode = bool(config['ytdown_quiet_mode'])

# main functions
def extract_video_title(url: str) -> json:
    """
    Extracts the video title using the URL
    :param url: URL of a YouTube video as a string
    :return: a string with the video title
    """
    ydl_opts = {"quiet": quiet_mode}

    # get info as json
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        # output the title only
        return info["title"]

def youtube_download_audio(url: str, output_dir='../../database/songs/') -> tuple:
    """
    Downloads the audio from a YouTube video
    :param url: URL of a YouTube video as a string
    :param output_dir: output directory to save audio file to encoded in base58
    :return: A tuple containing the title and title encoded in base58
    """
    title = extract_video_title(url)
    title_enc = str_to_base58(title)

    globalfuncs.logger.verbose(f"{title_enc} | {title}")

    song_dir = os.path.join(output_dir, title_enc)
    os.makedirs(song_dir, exist_ok=True)

    outtmpl = os.path.join(song_dir, "audio")

    # save as wav
    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "wav",
            "preferredquality": "192",
        }],
        "outtmpl": outtmpl,
        "quiet": quiet_mode,
    }

    # download
    if os.path.exists(f"{outtmpl}.wav"):
        globalfuncs.logger.verbose(f"Audio file already exists, skipping download")
    else:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    # return the title
    return title, title_enc