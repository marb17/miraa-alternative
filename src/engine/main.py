import os
import sys
import subprocess
import platform
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = SRC_DIR.parent

if platform.system() == "Windows":
    venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
elif platform.system() == "Darwin":
    venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
else:
    venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"

python_to_use = str(venv_python) if venv_python.exists() else sys.executable

if Path(sys.executable).resolve() != Path(python_to_use).resolve():
    print(f"Switching to virtual environment python: {python_to_use}")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR)
    os.execve(python_to_use, [python_to_use, __file__] + sys.argv[1:], env)

sys.path.insert(0, str(SRC_DIR))
from engine.utils.logger import Logger

logger = Logger(__name__)


def main() -> None:
    env = os.environ.copy()

    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = f"{SRC_DIR}{os.pathsep}{env['PYTHONPATH']}"
    else:
        env["PYTHONPATH"] = str(SRC_DIR)

    cmd = [python_to_use, "-m", "engine.tui.app"]
    print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, env=env)
        sys.exit(result.returncode)
    except Exception as e:
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    main()