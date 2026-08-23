"""Allow running as `python -m ckdeps`."""

import shutil
import subprocess
import sys

GUI_DEPS = ["python-gobject", "gtk4", "libadwaita"]


def _gui_runtime_available() -> bool:
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        return True
    except (ImportError, ValueError):
        return False


def _ensure_gui_deps() -> None:
    """Preflight: auto-install missing GTK4/libadwaita runtime (Arch/CachyOS)."""
    if _gui_runtime_available():
        return

    if not shutil.which("pacman"):
        print("❌ Missing GTK4/libadwaita runtime.\n"
              "   Install manually, e.g. on Debian/Ubuntu:\n"
              "     sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1\n"
              "   or Fedora:\n"
              "     sudo dnf install python3-gobject gtk4 libadwaita")
        sys.exit(1)

    print(f"📦 Installing missing system dependencies: {' '.join(GUI_DEPS)}")
    rc = subprocess.call(["sudo", "pacman", "-S", "--needed", "--noconfirm", *GUI_DEPS])
    if rc != 0 or not _gui_runtime_available():
        print(f"❌ Failed to set up GUI runtime. Install manually: sudo pacman -S {' '.join(GUI_DEPS)}")
        sys.exit(1)


_ensure_gui_deps()

from .main import main  # noqa: E402

sys.exit(main())
