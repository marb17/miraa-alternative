# STANDARD LIBRARIES
from pathlib import Path

# HELPER LIBRARY
from backend_new.core.processing import ALLOWED_MODEL_NAMES

# CONSTANTS
from backend_new.utils.paths import TEMP_DIR
from backend_new.utils.default.default_var import MODEL_INFO, AUDIO_MODEL_PRESETS

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
    # TODO gotta redo this

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
    from backend_new.core.processing import VocalSeparation

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

    with VocalSeparation(model_name=model) as separation:
        list(separation.separate_audio(file_path))


if __name__ == "__main__":
    main()