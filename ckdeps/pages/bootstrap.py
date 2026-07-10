"""Bootstrap page — system preparation with live progress."""

import shutil
import subprocess
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib


BOOTSTRAP_STEPS = [
    {
        "key": "system_update",
        "name": "System Update",
        "description": "Highly recommended before installing anything. "
                       "Ensures your system is up to date and avoids dependency conflicts.",
        "icon": "software-update-available-symbolic",
        "glow_icon": "✦",
        "default": True,
    },
    {
        "key": "base_deps",
        "name": "Base Dependencies",
        "description": "Required for CKDEPS to work. Installs build tools, git, "
                       "and the Flatpak runtime needed by this app.",
        "icon": "emblem-system-symbolic",
        "glow_icon": "⚙",
        "default": True,
    },
    {
        "key": "aur_helper",
        "name": "Yay AUR Helper",
        "description": "Needed to install packages from the AUR (Arch User Repository). "
                       "Without this, AUR packages will be unavailable on the next page.",
        "icon": "folder-download-symbolic",
        "glow_icon": "⬇",
        "default": True,
    },
    {
        "key": "flathub",
        "name": "Flathub Repository",
        "description": "Needed to install Flatpak apps. Without this, "
                       "Flatpak packages will be unavailable on the next page.",
        "icon": "application-x-flatpak-symbolic",
        "glow_icon": "◆",
        "default": True,
    },
]


def _detect_installed():
    """Detect what's already installed on the system."""
    result = {}

    # Check base deps: git, base-devel (makepkg), flatpak
    result["base_deps"] = (
        shutil.which("git") is not None
        and shutil.which("makepkg") is not None
        and shutil.which("flatpak") is not None
    )

    # Check yay
    result["aur_helper"] = shutil.which("yay") is not None

    # Check flathub remote
    try:
        out = subprocess.run(
            ["flatpak", "remotes"], capture_output=True, text=True, timeout=5
        )
        result["flathub"] = "flathub" in out.stdout.lower()
    except Exception:
        result["flathub"] = False

    # System update can't be detected
    result["system_update"] = False

    return result


class BootstrapPage(Gtk.Box):
    """System bootstrap page with optional steps and live tracking."""

    def __init__(self, installer, on_complete: callable):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("page-container")
        self.installer = installer
        self.on_complete = on_complete
        self._step_rows = []
        self._switches = {}
        self._step_keys = [s["key"] for s in BOOTSTRAP_STEPS]
        self._complete = False

        # ─── Header ──────────────────────────────────
        title = Gtk.Label(label="System Bootstrap")
        title.add_css_class("page-title")
        title.set_halign(Gtk.Align.START)
        self.append(title)

        subtitle = Gtk.Label(
            label="Choose which steps to run — detected items are pre-unchecked"
        )
        subtitle.add_css_class("page-subtitle")
        subtitle.set_halign(Gtk.Align.START)
        self.append(subtitle)

        # ─── Steps List ──────────────────────────────
        steps_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        steps_box.set_vexpand(True)

        for i, step in enumerate(BOOTSTRAP_STEPS):
            card = self._create_step_card(step, i)
            steps_box.append(card)

        self.append(steps_box)

        # ─── Spinner + Status ────────────────────────
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        status_box.set_halign(Gtk.Align.CENTER)
        status_box.set_margin_top(4)
        status_box.set_margin_bottom(8)

        self._spinner = Gtk.Spinner()
        self._spinner.add_css_class("spinner-large")
        self._spinner.set_spinning(False)
        self._spinner.set_visible(False)
        status_box.append(self._spinner)

        self._status_label = Gtk.Label(label="")
        self._status_label.add_css_class("progress-status")
        status_box.append(self._status_label)

        self.append(status_box)

        # ─── Navigation ──────────────────────────────
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        nav_box.set_halign(Gtk.Align.END)
        nav_box.set_margin_top(8)

        self._start_btn = Gtk.Button(label="Start Bootstrap  →")
        self._start_btn.add_css_class("nav-button-primary")
        self._start_btn.connect("clicked", lambda _: self.start_bootstrap())
        nav_box.append(self._start_btn)

        self._continue_btn = Gtk.Button(label="Continue  →")
        self._continue_btn.add_css_class("nav-button-primary")
        self._continue_btn.set_visible(False)
        self._continue_btn.connect("clicked", lambda _: self.on_complete())
        nav_box.append(self._continue_btn)

        self.append(nav_box)

        # ─── Auto-detect installed ───────────────────
        GLib.idle_add(self._auto_detect)

    def _create_step_card(self, step, index):
        """Create a single bootstrap step card with glow icon."""
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        card.add_css_class("extra-card")

        # Glow icon (emoji-based for theme matching)
        icon_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        icon_box.set_valign(Gtk.Align.CENTER)

        icon_label = Gtk.Label(label=step["glow_icon"])
        icon_label.add_css_class("bootstrap-glow-icon")
        icon_box.append(icon_label)

        card.append(icon_box)

        # Info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_hexpand(True)

        # Title row with optional detected badge
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title_row.set_halign(Gtk.Align.START)

        name_label = Gtk.Label(label=step["name"])
        name_label.add_css_class("extra-title")
        title_row.append(name_label)

        detected_label = Gtk.Label(label="detected ✓")
        detected_label.add_css_class("bootstrap-detected-badge")
        detected_label.set_visible(False)
        title_row.append(detected_label)

        info_box.append(title_row)

        desc_label = Gtk.Label(label=step["description"])
        desc_label.add_css_class("extra-desc")
        desc_label.set_halign(Gtk.Align.START)
        desc_label.set_wrap(True)
        info_box.append(desc_label)

        card.append(info_box)

        # Switch
        switch = Gtk.Switch()
        switch.set_active(step["default"])
        switch.set_valign(Gtk.Align.CENTER)
        switch.connect("state-set", self._on_switch_toggled, step, card)
        card.append(switch)
        self._switches[step["key"]] = switch

        self._step_rows.append({
            "card": card,
            "name": name_label,
            "icon": icon_label,
            "detected_badge": detected_label,
            "switch": switch,
            "key": step["key"],
        })

        return card

    def _auto_detect(self):
        """Check what's already installed and auto-uncheck."""
        detected = _detect_installed()

        for row_data in self._step_rows:
            key = row_data["key"]
            if detected.get(key, False):
                row_data["switch"].set_active(False)
                row_data["detected_badge"].set_visible(True)
                row_data["card"].set_opacity(0.6)

        return False

    def _on_switch_toggled(self, switch, state, step, card):
        """Handle step toggle."""
        if state:
            card.add_css_class("selected")
        else:
            card.remove_css_class("selected")

    def get_selected_steps(self):
        """Return list of selected step keys."""
        return [k for k, sw in self._switches.items() if sw.get_active()]

    def has_aur_helper(self):
        """Check if AUR helper step is selected."""
        return self._switches.get("aur_helper", Gtk.Switch()).get_active()

    def has_flathub(self):
        """Check if Flathub step is selected."""
        return self._switches.get("flathub", Gtk.Switch()).get_active()

    def start_bootstrap(self):
        """Begin the bootstrap process for selected steps."""
        selected = self.get_selected_steps()
        if not selected:
            self._status_label.set_text("No steps selected — skipping bootstrap")
            self._on_all_complete([])
            return

        # Disable switches and start button
        for sw in self._switches.values():
            sw.set_sensitive(False)
        self._start_btn.set_visible(False)
        self._spinner.set_spinning(True)
        self._spinner.set_visible(True)
        self._status_label.set_text("Starting bootstrap...")

        self.installer.bootstrap_system(
            selected_steps=selected,
            on_step=self._on_step,
            on_output=self._on_output,
            on_complete=self._on_all_complete,
        )

    def _on_step(self, message, step_key):
        """Called when a new bootstrap step begins."""
        self._status_label.set_text(message)

        # Find previous active step and mark done
        found_current = False
        for row_data in self._step_rows:
            if row_data["key"] == step_key:
                found_current = True
                # Mark current as active
                row_data["card"].remove_css_class("selected")
                row_data["card"].add_css_class("bootstrap-step-active")
                row_data["icon"].set_text("⟳")
                row_data["icon"].add_css_class("bootstrap-glow-icon-active")
                continue
            if not found_current and row_data["card"].has_css_class("bootstrap-step-active"):
                # Previous step done
                row_data["card"].remove_css_class("bootstrap-step-active")
                row_data["card"].add_css_class("bootstrap-step-done")
                row_data["icon"].set_text("✓")
                row_data["icon"].remove_css_class("bootstrap-glow-icon-active")
                row_data["icon"].add_css_class("bootstrap-glow-icon-done")

    def _on_output(self, line):
        """Send output to global log."""
        window = self.get_root()
        if hasattr(window, "append_log"):
            window.append_log(line)

    def _on_all_complete(self, results):
        """Called when all bootstrap steps are done."""
        self._spinner.set_spinning(False)
        self._spinner.set_visible(False)

        # Mark any active step as done
        for row_data in self._step_rows:
            if row_data["card"].has_css_class("bootstrap-step-active"):
                row_data["card"].remove_css_class("bootstrap-step-active")
                row_data["card"].add_css_class("bootstrap-step-done")
                row_data["icon"].set_text("✓")
                row_data["icon"].remove_css_class("bootstrap-glow-icon-active")
                row_data["icon"].add_css_class("bootstrap-glow-icon-done")

        # Dim unchecked steps
        for row_data in self._step_rows:
            if not row_data["switch"].get_active():
                row_data["card"].set_opacity(0.35)
                row_data["icon"].set_text("—")
                row_data["icon"].add_css_class("bootstrap-glow-icon-dim")

        if not results:
            self._status_label.set_text("Bootstrap skipped")
        else:
            all_ok = all(s for _, s in results)
            if all_ok:
                self._status_label.set_text("✨ System bootstrap complete!")
            else:
                failed = [n for n, s in results if not s]
                self._status_label.set_text(f"⚠ Some steps had issues: {', '.join(failed)}")

        self._continue_btn.set_visible(True)
        self._complete = True
