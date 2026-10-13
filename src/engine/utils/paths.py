#===================================================
#      DIRECTORIES
#===================================================

# BASE DIR
from pathlib import Path

#! Adjust based on exact depth
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
SRC_DIR = Path(BASE_DIR / "src")

#! CHANGE WHEN CHANGING BACKEND FOLDER NAME
BACKEND_DIR = SRC_DIR / "engine"

# DIRECTORIES
TEMP_DIR = SRC_DIR / ".temp"
CACHE_DIR = SRC_DIR / ".cache"
DICTS_DIR = SRC_DIR / "dicts"
CONFIG_DIR = SRC_DIR / "config"
DATA_DIR = SRC_DIR / "data"
MODEL_DIR = SRC_DIR / "models"

DATABASE_DIR = DATA_DIR / "database"

# FILES
ENV_FILE = CONFIG_DIR / ".env"
CONFIG_FILE = CONFIG_DIR / "config.json"
