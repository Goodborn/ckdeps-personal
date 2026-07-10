"""Extras page — system configuration extras selection."""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from ckdeps.backend.package_data import EXTRAS, ExtraConfig

FISH_CONFIG_PREVIEW = """# Starship prompt
starship init fish | source

# The Fuck (fk command)
thefuck --alias fk | source

# Atuin shell history
atuin init fish | source

# Zoxide smart cd
zoxide init fish | source

# Custom aliases (weather, ls, update, remove)
source ~/CustomScripts/aliases.fish

# Command duration in right prompt (shows >500ms commands)
"""


class ExtrasPage(Gtk.Box):
    """Configuration extras selection page."""

    def __init__(self, on_continue: callable, on_back: callable):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("page-container")
        self.on_continue = on_continue
        self.on_back = on_back
        self._extras = [ExtraConfig(
            key=e.key, title=e.title, description=e.description,
            icon_name=e.icon_name
        ) for e in EXTRAS]
        self._switches = {}
        self._preview_revealers = {}

        # ─── Header ──────────────────────────────────
        title = Gtk.Label(label="System Configuration")
        title.add_css_class("page-title")
        title.set_halign(Gtk.Align.START)
        self.append(title)

        subtitle = Gtk.Label(
            label="Optional system tweaks and configuration extras"
        )
        subtitle.add_css_class("page-subtitle")
        subtitle.set_halign(Gtk.Align.START)
        self.append(subtitle)

        # ─── Extras List ─────────────────────────────
        extras_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        extras_box.set_vexpand(True)

        for extra in self._extras:
            wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            card = self._create_extra_card(extra)
            wrapper.append(card)

            # Add preview revealer for fish_config
            if extra.key == "fish_config":
                revealer = self._create_preview_revealer(FISH_CONFIG_PREVIEW)
                self._preview_revealers[extra.key] = revealer
                wrapper.append(revealer)

            extras_box.append(wrapper)

        self.append(extras_box)

        # ─── Navigation ──────────────────────────────
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        nav_box.set_halign(Gtk.Align.END)
        nav_box.set_margin_top(12)

        back_btn = Gtk.Button(label="  ←  Back  ")
        back_btn.add_css_class("nav-button")
        back_btn.connect("clicked", lambda _: self.on_back())
        nav_box.append(back_btn)

        skip_btn = Gtk.Button(label="Skip Extras")
        skip_btn.add_css_class("nav-button")
        skip_btn.connect("clicked", lambda _: self.on_continue([]))
        nav_box.append(skip_btn)

        apply_btn = Gtk.Button(label="Apply Selected  →")
        apply_btn.add_css_class("nav-button-primary")
        apply_btn.connect("clicked", self._on_apply_clicked)
        nav_box.append(apply_btn)

        self.append(nav_box)

    def _create_extra_card(self, extra: ExtraConfig):
        """Create a single extra configuration card."""
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        card.add_css_class("extra-card")

        # Icon
        icon = Gtk.Image.new_from_icon_name(extra.icon_name)
        icon.set_pixel_size(32)
        icon.set_opacity(0.7)
        card.append(icon)

        # Info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_hexpand(True)

        title = Gtk.Label(label=extra.title)
        title.add_css_class("extra-title")
        title.set_halign(Gtk.Align.START)
        info_box.append(title)

        desc = Gtk.Label(label=extra.description)
        desc.add_css_class("extra-desc")
        desc.set_halign(Gtk.Align.START)
        desc.set_wrap(True)
        info_box.append(desc)

        card.append(info_box)

        # Switch
        switch = Gtk.Switch()
        switch.set_valign(Gtk.Align.CENTER)
        switch.connect("state-set", self._on_switch_toggled, extra, card)
        card.append(switch)

        self._switches[extra.key] = switch
        return card

    def _create_preview_revealer(self, preview_text):
        """Create a collapsible preview of config content."""
        revealer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        revealer_box.set_margin_start(48)
        revealer_box.set_margin_end(16)

        revealer = Gtk.Revealer()
        revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        revealer.set_transition_duration(300)
        revealer.set_reveal_child(False)

        preview_label = Gtk.Label(label="Preview — will be added to config.fish:")
        preview_label.add_css_class("package-desc")
        preview_label.set_halign(Gtk.Align.START)
        preview_label.set_margin_bottom(4)
        revealer.append(preview_label)

        # Code block
        code_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        code_box.add_css_class("log-scroll")

        code_label = Gtk.Label(label=preview_text.strip())
        code_label.add_css_class("log-text")
        code_label.set_halign(Gtk.Align.START)
        code_label.set_selectable(True)
        code_box.append(code_label)

        revealer.append(code_box)
        revealer_box.append(revealer)

        # Store revealer reference on the box for toggling
        revealer_box._revealer = revealer
        return revealer_box

    def _on_switch_toggled(self, switch, state, extra, card):
        """Handle extra toggle."""
        extra.selected = state
        if state:
            card.add_css_class("selected")
        else:
            card.remove_css_class("selected")

        # Toggle preview revealer if it exists
        if extra.key in self._preview_revealers:
            revealer_box = self._preview_revealers[extra.key]
            revealer_box._revealer.set_reveal_child(state)

    def _on_apply_clicked(self, _btn):
        """Continue with selected extras."""
        selected = [e for e in self._extras if e.selected]
        self.on_continue(selected)
