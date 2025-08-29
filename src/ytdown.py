import yt_dlp
import io
import requests

def download_youtube_video(url):
    yt_download_options = {"format": "bestaudio/best", "quiet": True}
    with yt_dlp.YoutubeDL(yt_download_options) as ydl:
        info = ydl.extract_info(url, download=False)
        video_info = info.get('title', None)
        stream = info["url"]

    response = requests.get(stream, stream=True)

    file_like = io.BytesIO(response.content)
    file_like.seek(0)

    return video_info, file_like

if __name__ == "__main__":
    pass