# STANDARD LIBRARIES
import json
from pathlib import Path
from typing import Literal

# HELPER LIBRARY
from engine.core.processing import ALLOWED_MODEL_NAMES
from engine.extractors import downloader
from engine.utils.functions.filesystem import read_json_file

# CONSTANTS
from engine.utils.paths import TEMP_DIR
from engine.utils.default.default_var import MODEL_INFO, AUDIO_MODEL_PRESETS

# PYPI LIBRARIES
import click
from click_shell import shell

# @click.group
@shell(
    prompt="miraa > ",
    intro="Welcome to the miraa-alternative interactive shell! Type 'help' for available commands or 'exit' to quit."
)
def main():
    """miraa-alternative CLI TOOL"""
    pass

@main.command()
@click.argument("url")
@click.option("--output_type",
              type=click.Choice(["audio", "video"]),
              default="audio",
              help=f"Whether to download audio or video",)
def download_audio(url: str, output_type: Literal["audio", "video"]) -> None:
    """
    Downloads the audio from YouTube, always outputs .wav and outputs to .temp
    """
    with downloader.Downloader() as dl:
        result = list(dl.download_song(url, download_type=output_type))

@main.command()
@click.argument("file",
                type=click.Path(exists=True,
                                file_okay=True,
                                dir_okay=False,
                                readable=True,
                                path_type=Path))
@click.option("--model",
              type=click.Choice([key for key in AUDIO_MODEL_PRESETS]),
              default="vocal_full",
              help=f"Model to use for separation\n\n{MODEL_INFO}")
def separate_audio(file: str, model: ALLOWED_MODEL_NAMES) -> None:
    """
    Separates the audio from the file provided
    """
    from engine.core.processing import AudioSeparation

    user_file_path = Path(file)
    if len(user_file_path.parts) == 1:
        file_path = TEMP_DIR / user_file_path
    elif user_file_path.is_absolute():
        file_path = user_file_path
    else:
        raise Exception(f"Please do not use relative file paths.")

    if not file_path.exists():
        raise FileNotFoundError("File does not exist.")

    click.echo(f"Separating {file_path}")

    with AudioSeparation(model_name=model) as separation:
        list(separation.separate_audio(file_path))


# miraa-alternative stuff
@main.command()
def temp_view_files() -> None:
    for idx, file in enumerate([file for file in TEMP_DIR.iterdir() if file.suffix == ".json"]):
        click.echo(f"{idx} | {file.name}")

@main.command()
@click.argument("index", type=int)
@click.option("--data",
              type=click.Choice(["all", "lyrics", "translated_lyrics", "metadata"]),
              default="all",
              help="Which part of the data to display")
def temp_view_data(index: int, data: str) -> None:
    files = [file for file in TEMP_DIR.iterdir() if file.suffix == ".json"]
    try:
        selected_file = files[index]
        file_data = read_json_file(selected_file)
    except IndexError:
        click.echo("File does not exist, please check files by using 'temp-view-files'")
        return

    if data == "all":
        click.echo(json.dumps(file_data, indent=4))
    elif data == "lyrics":
        click.echo(file_data.get("lyrics_main", "No lyrics have been pulled"))
    elif data == "translated_lyrics":
        click.echo("\n".join(file_data.get("translated_lyrics", "Lyrics have not been translated")))
    elif data == "metadata":
        click.echo(f"Song: {file_data["pre_processing"]["view_name"]}")
        click.echo(f"Youtube ID: {file_data["pre_processing"]["youtube_id"]}")

if __name__ == "__main__":
    main()