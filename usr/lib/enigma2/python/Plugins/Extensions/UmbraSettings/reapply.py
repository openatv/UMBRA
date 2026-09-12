"""Rebuild generated skin files after an update without importing receiver UI modules."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from UmbraSettings.styles import prepare_saved_skin


if __name__ == "__main__":
    prepare_saved_skin(Path("/usr/share/enigma2/Umbra"), Path("/etc/enigma2/settings"), Path("/etc/enigma2/umbra/styles"))
