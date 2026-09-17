"""Small animation helpers shared across pages, so entrance choreography
(fade + slide-up, staggered) is consistent instead of every page rolling
its own GLib.timeout_add loop."""

import gi
gi.require_version("GLib", "2.0")
from gi.repository import GLib


def stagger_fade_in(widgets, start_delay=80, step=70, slide=True):
    """Fade (and optionally slide-up) a sequence of widgets in, staggered.

    Widgets must start at opacity 0 (set by the caller before layout)."""
    for i, widget in enumerate(widgets):
        GLib.timeout_add(start_delay + i * step, _reveal, widget, slide)


def _reveal(widget, slide):
    widget.set_opacity(1)
    if slide:
        widget.add_css_class("animate-slide-up")
    return False
