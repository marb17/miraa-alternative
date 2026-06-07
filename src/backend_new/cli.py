# STANDARD LIBRARIES
from pathlib import Path

# HELPER LIBRARY
from backend_new.core.processing import ALLOWED_MODEL_NAMES, AUDIO_MODEL_PRESETS

# CONSTANTS
from backend_new.utils.constants import TEMP_DIR, MODEL_INFO

# PYPI LIBRARIES
import click

@click.group
def main():
    """miraa-alternative CLI TOOL"""
    pass

@main.command()
@click.argument("url")
@click.option("--rename-id", is_flag=True, default=False, help="Rename the video file to the youtube ID")
def download_audio(url: str, rename_id: bool) -> None:
    """
    Downloads the audio from YouTube, always outputs .wav and outputs to .temp
    """
    from backend_new.extractors.downloader import Downloader

    with Downloader() as dl:
        file_path, file_data = dl.download_youtube_video(url)

    print(file_path)

    if not rename_id:
        file_path.rename(f"{TEMP_DIR / file_data["title"]}.wav")

@main.command()
@click.argument("file")
@click.option("--model",
              type=click.Choice([key for key in AUDIO_MODEL_PRESETS]),
              default="vocal_full",
              help=f"Model to use for separation\n\n{MODEL_INFO}")
def separate_audio(file: str, model: ALLOWED_MODEL_NAMES) -> None:
    """
    Separates the audio from the URL provided, if song not yet downloaded, it will download automatically
    """
    from backend_new.core.processing import VocalSeparation

    user_file_path = Path(file)
    if len(user_file_path.parts) == 1:
        file_path = TEMP_DIR / user_file_path
    elif user_file_path.is_absolute():
        file_path = user_file_path
    else:
        raise Exception(f"Please do not use relative file paths.")

    if file_path.exists():
        pass
    else:
        raise FileNotFoundError("File does not exist.")

    click.echo(f"Separating {file_path}")

    with VocalSeparation(model_name=model) as separation:
        separation.separate_audio(file_path)


if __name__ == "__main__":
    main()