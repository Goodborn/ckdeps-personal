"""Resource path resolution — locates bundled assets in dev or installed layouts."""

from pathlib import Path
from typing import Optional

_APP_ICON_CANDIDATES = [
    # Development path (running from a source checkout)
    Path(__file__).resolve().parent.parent.parent / "data" / "com.goodborn.ckdeps.svg",
    # Installed path (hicolor icon theme)
    Path("/usr/share/icons/hicolor/scalable/apps/com.goodborn.ckdeps.svg"),
]


def app_icon_path() -> Optional[Path]:
    """Return the path to the CKDEPS app icon SVG, or None if not found."""
    for path in _APP_ICON_CANDIDATES:
        if path.is_file():
            return path
    return None
