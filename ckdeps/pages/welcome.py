"""Welcome page — animated branding and system information."""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Pango
import platform
import os

from ..backend.paths import app_icon_path


class WelcomePage(Gtk.Box):
    """First page of the wizard with animated branding."""

    def __init__(self, installer, on_begin: callable):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._installer = installer
        self._on_begin = on_begin
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)
        self.add_css_class("welcome-container")

        # ─── Logo ─────────────────────────────────────
        icon_path = app_icon_path()
        if icon_path:
            logo = Gtk.Image.new_from_file(str(icon_path))
            logo.set_pixel_size(72)
        else:
            logo = Gtk.Image.new_from_icon_name("application-x-executable-symbolic")
            logo.set_pixel_size(56)
        logo.add_css_class("welcome-logo")
        logo.set_opacity(0)
        self.append(logo)

        # ─── Title ────────────────────────────────────
        title = Gtk.Label(label="CKDEPS")
        title.add_css_class("welcome-title")
        title.set_opacity(0)
        self.append(title)

        from ..backend.distro import friendly_name
        subtitle = Gtk.Label(label=f"{friendly_name()} KDE Personal Stuff")
        subtitle.add_css_class("welcome-subtitle")
        subtitle.set_opacity(0)
        self.append(subtitle)

        # ─── Description ─────────────────────────────
        desc = Gtk.Label(
            label="A personal initial (fresh install) app to my liking\n"
                  f"to get {friendly_name()} KDE ready for my personal use."
        )
        desc.add_css_class("welcome-description")
        desc.set_wrap(True)
        desc.set_max_width_chars(60)
        desc.set_justify(Gtk.Justification.CENTER)
        desc.set_opacity(0)
        self.append(desc)

        # ─── Personal Signature ──────────────────────
        signature = Gtk.Label(label="Handcrafted by Goodborn")
        signature.add_css_class("personal-signature")
        signature.set_opacity(0)
        self.append(signature)

        # ─── Feature Cards ───────────────────────────
        features_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        features_box.set_halign(Gtk.Align.CENTER)
        features_box.add_css_class("welcome-features")
        features_box.set_opacity(0)

        features = [
            ("package-x-generic-symbolic", "My Packages", "AUR + Flatpak picks"),
            ("system-run-symbolic", "Personal Prep", "Custom bootstrap script"),
            ("preferences-desktop-appearance-symbolic", "Handpicked Extras", "Opinionated system tweaks"),
            ("emblem-synchronizing-symbolic", "Live Progress", "Real-time deployment tracking"),
        ]

        for icon_name, ftitle, fdesc in features:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            card.add_css_class("feature-card")
            card.set_size_request(150, -1)

            icon_label = Gtk.Image.new_from_icon_name(icon_name)
            icon_label.set_pixel_size(22)
            icon_label.add_css_class("feature-icon")
            card.append(icon_label)

            title_label = Gtk.Label(label=ftitle)
            title_label.add_css_class("feature-title")
            card.append(title_label)

            desc_label = Gtk.Label(label=fdesc)
            desc_label.add_css_class("feature-desc")
            card.append(desc_label)

            features_box.append(card)

        self.append(features_box)

        # ─── System Info ─────────────────────────────
        sysinfo = Gtk.Label()
        sysinfo.add_css_class("welcome-description")
        sysinfo.set_markup(
            f'<span size="small" alpha="40%">'
            f'{platform.node()} • {platform.machine()} • '
            f'Python {platform.python_version()}'
            f'</span>'
        )
        sysinfo.set_opacity(0)
        self.append(sysinfo)

        # ─── Password Entry ──────────────────────────
        pass_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        pass_box.add_css_class("welcome-password-box")
        pass_box.set_halign(Gtk.Align.CENTER)
        pass_box.set_margin_top(12)
        pass_box.set_margin_bottom(24)
        pass_box.set_opacity(0)
        
        pass_label = Gtk.Label(label="Root Password (Required for Installation)")
        pass_label.add_css_class("welcome-description")
        pass_box.append(pass_label)
        
        self.pass_entry = Gtk.PasswordEntry()
        self.pass_entry.set_show_peek_icon(True)
        self.pass_entry.set_size_request(300, -1)
        self.pass_entry.connect("activate", lambda _: self._on_begin_clicked())
        pass_box.append(self.pass_entry)

        self._pass_error = Gtk.Label(label="")
        self._pass_error.add_css_class("welcome-password-error")
        self._pass_error.set_halign(Gtk.Align.CENTER)
        self._pass_error.set_visible(False)
        pass_box.append(self._pass_error)

        self.append(pass_box)

        # ─── Begin Button ────────────────────────────
        begin_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        begin_box.set_halign(Gtk.Align.CENTER)
        begin_box.set_opacity(0)
        self._begin_box = begin_box

        self._begin_spinner = Gtk.Spinner()
        self._begin_spinner.set_visible(False)
        begin_box.append(self._begin_spinner)

        self.begin_btn = Gtk.Button(label="Begin Setup  →")
        self.begin_btn.add_css_class("begin-button")
        self.begin_btn.connect("clicked", lambda _: self._on_begin_clicked())
        begin_box.append(self.begin_btn)

        self.append(begin_box)

        # ─── Stagger fade-in animation ───────────────
        widgets = [logo, title, subtitle, desc, features_box, sysinfo, pass_box, begin_box]
        for i, w in enumerate(widgets):
            GLib.timeout_add(200 + i * 120, self._fade_in, w)

    @staticmethod
    def _fade_in(widget):
        """Animate widget fade-in via opacity."""
        widget.set_opacity(1)
        return False  # Don't repeat

    def focus_entry(self):
        """Set keyboard focus to the password entry."""
        self.pass_entry.grab_focus()

    def _on_begin_clicked(self):
        password = self.pass_entry.get_text()
        if not password:
            self.pass_entry.add_css_class("error")
            self._show_error("Enter your password to continue.")
            return

        self._set_busy(True, "Verifying password...")
        self._installer.verify_sudo_password(password, self._on_password_verified)

    def _on_password_verified(self, ok: bool):
        password = self.pass_entry.get_text()
        if not ok:
            self._set_busy(False)
            self.pass_entry.add_css_class("error")
            self._show_error("Incorrect password. Please try again.")
            self.pass_entry.grab_focus()
            return

        self.pass_entry.remove_css_class("error")
        self._hide_error()
        self._set_busy(True, "Checking system...")
        self._installer.check_environment(
            lambda issues: self._on_environment_checked(issues, password)
        )

    def _on_environment_checked(self, issues, password):
        self._set_busy(False)

        if not issues:
            self._on_begin(password)
            return

        self._show_preflight_dialog(issues, password)

    def _show_preflight_dialog(self, issues, password):
        """Warn about anything the environment check found before letting
        pacman/yay loose on the system. Errors (e.g. not Arch-based) get a
        strong warning but the user can still override on their own system."""
        has_error = any(level == "error" for level, _ in issues)
        lines = "\n\n".join(f"• {msg}" for _level, msg in issues)

        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Before we continue" if not has_error else "This may not be safe",
            body=lines,
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("continue", "Continue Anyway")
        dialog.set_response_appearance(
            "continue",
            Adw.ResponseAppearance.DESTRUCTIVE if has_error else Adw.ResponseAppearance.SUGGESTED,
        )
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", lambda d, r: self._on_preflight_response(r, password))
        dialog.present()

    def _on_preflight_response(self, response, password):
        if response == "continue":
            self._on_begin(password)

    def _set_busy(self, busy: bool, status: str = ""):
        self.begin_btn.set_sensitive(not busy)
        self.pass_entry.set_sensitive(not busy)
        self._begin_spinner.set_visible(busy)
        if busy:
            self._begin_spinner.start()
        else:
            self._begin_spinner.stop()
        if status:
            self._show_error(status, is_error=False)
        elif not busy:
            self._hide_error()

    def _show_error(self, text: str, is_error: bool = True):
        self._pass_error.set_text(text)
        self._pass_error.set_visible(True)
        if is_error:
            self._pass_error.add_css_class("is-error")
        else:
            self._pass_error.remove_css_class("is-error")

    def _hide_error(self):
        self._pass_error.set_visible(False)
