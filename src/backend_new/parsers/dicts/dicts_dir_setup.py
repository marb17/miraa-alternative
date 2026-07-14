from backend_new.utils.constants import DICTS_DIR
import shutil

from backend_new.utils.logger import Logger
logger = Logger(__name__)

def extract_zip_files():
    all_zip_files = [file for file in DICTS_DIR.iterdir() if file.suffix == ".zip"]
    all_zip_files_stem = [file.stem for file in all_zip_files]

    if all_zip_files:
        logger.debug("New .zip files detected, extracting now")
        for file_path, stem_name in zip(all_zip_files, all_zip_files_stem):
            dir_path = DICTS_DIR / f"{stem_name}"
            dir_path.mkdir(parents=True, exist_ok=True)

            logger.debug(f"Extracting: {file_path}")
            try:
                shutil.unpack_archive(file_path, dir_path)
                logger.debug(f"Completed extracting: {file_path}, deleting old .zip files")
                file_path.unlink()
            except:
                raise Exception(
                    "File unsuccessfully extracted, please re-run and check for any unintended changes in 'dict' directory")
        logger.debug("All .zip files extracted successfully")
    else:
        logger.debug("No new .zip files detected, skipping")