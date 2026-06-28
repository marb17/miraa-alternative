import json
import os
from pathlib import Path
from typing import Any

import questionary as q
from dotenv import set_key, load_dotenv

from backend_new.utils.constants import CONFIG_FILE, ENV_FILE, DEFAULT_ENV_VARS, TEMP_DIR
from backend_new.utils.logger import Logger
logger = Logger(__name__)



def read_json_file(file_path: Path, safe_fail: bool = False) -> dict:
    """
    Reads a JSON file in a directory
    :param file_path: File path to the JSON file
    :param safe_fail: If true, when file doesn't exist, doesn't raise an exception
    :return: A dict containing the JSON data
    """
    if not file_path.exists():
        logger.warning(f"File {file_path} does not exist")
        if safe_fail:
            return {}
        else:
            raise FileNotFoundError(f"File {file_path} does not exist")

    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"The provided JSON file is not a valid JSON file or is corrupted, please remove / repair this file. {file_path}", e.doc, e.pos)


def write_json_file(file_path: Path, payload: Any, keys: list[str] = None) -> None:
    """
    Writes data to a JSON file in a directory
    :param file_path: File path to the JSON file
    :param payload: Data to write
    :param keys: A list of keys to navigate the JSON file
    """
    data = read_json_file(file_path)

    current_level = data
    for key in keys[:-1]:
        if key not in current_level or not isinstance(current_level[key], dict):
            current_level[key] = {}
        current_level = current_level[key]

    if keys:
        current_level[keys[-1]] = payload

    file_path.write_text(json.dumps(data, indent=4))


def read_config() -> dict[str, Any]:
    """
    Reads the config file data
    :return: Config file data
    :rtype: dict[str, Any]
    """
    return read_json_file(CONFIG_FILE)


def write_config(payload: Any, keys: list[str] = None) -> None:
    """
    Writes to the config file
    :param payload: Data to write
    :param keys: A list of keys to navigate the JSON file
    """
    write_json_file(CONFIG_FILE, payload, keys)


def write_env_key(value: str, key: str) -> None:
    set_key(dotenv_path=ENV_FILE, key_to_set=key, value_to_set=value, quote_mode="never")


def load_env_file(safe_empty: bool = True) -> dict[Any, str | None]:
    """
    Loads the environment variables from the .env file.
    Creates a new .env file if it doesn't exist.
    DOES NOT check if the file is filled
    """
    if ENV_FILE.exists():
        load_dotenv(dotenv_path=ENV_FILE)
        logger.debug("Loaded .env file.")
    else:
        if safe_empty:
            pass
        else:
            logger.critical("No .env file found. Creating empty .env file. Do NOT reorder the variables")
            ENV_FILE.write_text("\n".join([f"{var}=" for var in DEFAULT_ENV_VARS]))
            raise FileNotFoundError(".env file not found, creating one. Please add your credentials to the .env file.")

    load_dotenv()
    return dict([(var, os.getenv(var)) for var in DEFAULT_ENV_VARS])


def clear_temp_dir() -> None:
    if q.confirm(f"Are you sure you want to clear the .temp directory?\n{TEMP_DIR}", auto_enter=False, default=False).ask():
        for item in TEMP_DIR.iterdir():
            if item.suffix == ".wav":
                item.unlink()
            elif item.suffix == ".json":
                item.unlink()
            else:
                logger.info(f"{item} is not a a .wav or .json file")
    else:
        logger.info("Cancelling operation")


def all_available_temp_json_files() -> list[dict[str, str | Path]]:
    all_json_files = [file for file in TEMP_DIR.iterdir() if file.suffix == ".json"]
    final_dict: list[dict[str, str | Path]] = []
    for file in all_json_files:
        final_dict.append({
            "name": file.stem,
            "path": file.absolute()
        })

    return final_dict