"""Splash screen — initial loading animation."""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

from ..backend.paths import app_icon_path
from ..backend.anim import stagger_fade_in


class SplashPage(Gtk.Box):
    """Initial splash screen with animation."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)
        self.add_css_class("splash-container")

        # ─── Logo / Icon ──────────────────────────────
        icon_path = app_icon_path()
        if icon_path:
            self._logo = Gtk.Image.new_from_file(str(icon_path))
            self._logo.set_pixel_size(96)
        else:
            self._logo = Gtk.Image.new_from_icon_name("application-x-executable-symbolic")
            self._logo.set_pixel_size(72)
        self._logo.add_css_class("splash-logo")
        self._logo.set_opacity(0)
        self.append(self._logo)

        # ─── Title ───────────────────────────────────
        self._title = Gtk.Label(label="CKDEPS")
        self._title.add_css_class("splash-title")
        self._title.set_opacity(0)
        self.append(self._title)

        # ─── Loading Bar ─────────────────────────────
        self._progress = Gtk.ProgressBar()
        self._progress.add_css_class("splash-progress")
        self._progress.set_margin_top(20)
        self._progress.set_opacity(0)
        self.append(self._progress)

        self._status = Gtk.Label(label="Initializing System...")
        self._status.add_css_class("splash-status")
        self._status.set_opacity(0)
        self.append(self._status)

    def start_animation(self):
        """Animate the splash elements in."""
        stagger_fade_in([self._logo, self._title, self._progress, self._status],
                         start_delay=100, step=180)

        # Start progress pulse
        GLib.timeout_add(100, self._pulse_progress)

    def _pulse_progress(self):
        self._progress.pulse()
        return True
