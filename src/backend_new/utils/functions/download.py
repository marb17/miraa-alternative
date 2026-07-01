import re
from pathlib import Path
from typing import Generator

import gdown

from backend_new.utils.paths import DICTS_DIR
from backend_new.utils.default.default_var import DEFAULT_DICTS, DEFAULT_DICTS_FOLDER_LINK


def download_google_drive(link: str, output_path: Path) -> None:
    gdown.download(link, str(output_path), quiet=False)


def download_all_dicts() -> Generator[str, None, None]:
    try:
        files = gdown.download_folder(DEFAULT_DICTS_FOLDER_LINK, skip_download=True)
        re_dicts_search = [re.compile(f".*{item}.*") for item in DEFAULT_DICTS]

        for file_info in files:
            if any([complied.match(file_info.path) for complied in re_dicts_search]):
                yield f"Downloading: {file_info.path}"
                gdown.download(id=file_info.id, output=DICTS_DIR, use_cookies=False)
                yield f"Finished Downloading: {file_info.path}"
    except Exception as e:
        raise e
