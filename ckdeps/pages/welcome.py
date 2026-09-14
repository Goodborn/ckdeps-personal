"""Welcome page — animated branding and system information."""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Pango
import platform
import os


class WelcomePage(Gtk.Box):
    """First page of the wizard with animated branding."""

    def __init__(self, on_begin: callable):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._on_begin = on_begin
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)
        self.add_css_class("welcome-container")

        # ─── Logo / Rocket ────────────────────────────
        logo = Gtk.Label(label="🚀")
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
            ("📦", "My Packages", "AUR + Flatpak picks"),
            ("⚡", "Personal Prep", "Custom bootstrap script"),
            ("🎨", "Handpicked Extras", "Opinionated system tweaks"),
            ("📊", "Live Progress", "Real-time deployment tracking"),
        ]

        for icon, ftitle, fdesc in features:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            card.add_css_class("feature-card")
            card.set_size_request(150, -1)

            icon_label = Gtk.Label(label=icon)
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
        
        self.append(pass_box)

        # ─── Begin Button ────────────────────────────
        self.begin_btn = Gtk.Button(label="Begin Setup  →")
        self.begin_btn.add_css_class("begin-button")
        self.begin_btn.set_halign(Gtk.Align.CENTER)
        self.begin_btn.set_opacity(0)
        self.begin_btn.connect("clicked", lambda _: self._on_begin_clicked())
        self.append(self.begin_btn)

        # ─── Stagger fade-in animation ───────────────
        widgets = [logo, title, subtitle, desc, features_box, sysinfo, pass_box, self.begin_btn]
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
            return
        self._on_begin(password)
