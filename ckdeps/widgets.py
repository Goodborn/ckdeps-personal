"""Small reusable chrome widgets shared by the main window."""

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

# (stack page name, short label) — splash is intentionally excluded, it's
# a loading screen rather than a wizard step.
STEPS = [
    ("welcome", "Welcome"),
    ("bootstrap", "Prepare"),
    ("packages", "Packages"),
    ("extras", "Extras"),
    ("progress", "Install"),
    ("summary", "Done"),
]


class StepIndicator(Gtk.Box):
    """Horizontal breadcrumb showing where the user is in the wizard."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.add_css_class("step-indicator")
        self.set_halign(Gtk.Align.CENTER)

        self._items = {}
        for i, (key, label) in enumerate(STEPS):
            if i > 0:
                connector = Gtk.Box()
                connector.add_css_class("step-connector")
                connector.set_valign(Gtk.Align.CENTER)
                self.append(connector)

            item = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            item.add_css_class("step-item")

            dot = Gtk.Box()
            dot.add_css_class("step-dot")
            item.append(dot)

            lbl = Gtk.Label(label=label)
            lbl.add_css_class("step-label")
            item.append(lbl)

            self.append(item)
            self._items[key] = item

    def set_active(self, active_key: str):
        """Mark `active_key` current; everything before it done, after it upcoming."""
        found_active = active_key in self._items
        passed = False
        for key, _label in STEPS:
            item = self._items[key]
            item.remove_css_class("step-active")
            item.remove_css_class("step-done")
            item.remove_css_class("step-upcoming")
            if key == active_key:
                item.add_css_class("step-active")
                passed = True
            elif not passed:
                item.add_css_class("step-done")
            else:
                item.add_css_class("step-upcoming")
        if not found_active:
            # e.g. splash — no step is current yet.
            for item in self._items.values():
                item.add_css_class("step-upcoming")


def build_ambient_background(overlay: Gtk.Overlay):
    """Attach slow-drifting, softly glowing color blobs behind the main
    content for an ambient, alive backdrop instead of a flat gradient."""
    orb1 = Gtk.Box()
    orb1.add_css_class("ambient-orb")
    orb1.add_css_class("ambient-orb-1")
    orb1.set_halign(Gtk.Align.START)
    orb1.set_valign(Gtk.Align.START)
    orb1.set_can_target(False)
    overlay.add_overlay(orb1)
    overlay.set_measure_overlay(orb1, False)

    orb2 = Gtk.Box()
    orb2.add_css_class("ambient-orb")
    orb2.add_css_class("ambient-orb-2")
    orb2.set_halign(Gtk.Align.END)
    orb2.set_valign(Gtk.Align.END)
    orb2.set_can_target(False)
    overlay.add_overlay(orb2)
    overlay.set_measure_overlay(orb2, False)

    orb3 = Gtk.Box()
    orb3.add_css_class("ambient-orb")
    orb3.add_css_class("ambient-orb-3")
    orb3.set_halign(Gtk.Align.END)
    orb3.set_valign(Gtk.Align.START)
    orb3.set_can_target(False)
    overlay.add_overlay(orb3)
    overlay.set_measure_overlay(orb3, False)
