#===================================================
#      DIRECTORIES
#===================================================

# BASE DIR
from pathlib import Path

#! Adjust based on exact depth
BASE_DIR = Path(__file__).resolve().parent.parent.parent

#! CHANGE WHEN CHANGING BACKEND FOLDER NAME
BACKEND_DIR = BASE_DIR / "engine"

# DIRECTORIES
TEMP_DIR = BASE_DIR / ".temp"
CACHE_DIR = BASE_DIR / ".cache"
DICTS_DIR = BASE_DIR / "dicts"
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"

DATABASE_DIR = BACKEND_DIR / "database"

# FILES
ENV_FILE = CONFIG_DIR / ".env"
CONFIG_FILE = CONFIG_DIR / "config.json"
