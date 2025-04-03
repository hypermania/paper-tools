from pathlib import Path
import os
import appdirs

# from dotenv import load_dotenv
# load_dotenv()  # Load .env file if present

def get_data_dir() -> Path:
    """Return OS-appropriate data directory"""
    custom_path = os.getenv("PAPER_TOOLS_DATA_PATH")
    if custom_path:
        dir_path = Path(custom_path)
    else:
        dir_path = Path(appdirs.user_data_dir("paper_tools"))
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path
