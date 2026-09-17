"""Progress page — animated installation progress with live output."""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

from ..backend.paths import app_icon_path
from ..backend.anim import stagger_fade_in

INSTALL_TIPS = [
    "Packages already on your system are detected automatically and skipped.",
    "Cancel any time — CKDEPS stops cleanly after the current package finishes.",
    "AUR packages are built and installed through yay, the AUR helper.",
    "A full log of this run is saved to ~/ckdeps-logs/ once it's done.",
    "Closing the window mid-install prompts a safe stop instead of a hard quit.",
    "vm-curator-bin also pulls in qemu-full and sdl2 automatically.",
    "Bolt Launcher needs a JVM — jre-openjdk is installed for it automatically.",
    "Flatpak apps install from Flathub, sandboxed from the rest of your system.",
]


class ProgressPage(Gtk.Box):
    """Live installation progress page with per-package tracking."""

    def __init__(self, installer, on_complete: callable):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("progress-container")
        self.installer = installer
        self.on_complete = on_complete
        self._results = []
        self._tip_index = 0
        self._tip_timer_id = None

        # ─── Header ──────────────────────────────────
        title = Gtk.Label(label="Installing Packages")
        title.add_css_class("page-title")
        title.set_halign(Gtk.Align.START)
        self.append(title)

        subtitle = Gtk.Label(label="Sit back while your system is being configured")
        subtitle.add_css_class("page-subtitle")
        subtitle.set_halign(Gtk.Align.START)
        self.append(subtitle)

        # ─── Immersive Mode Toggle ─────────────────────
        toggle_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        toggle_row.add_css_class("immersive-toggle-row")
        toggle_row.set_halign(Gtk.Align.END)

        toggle_label = Gtk.Label(label="Immersive install screen")
        toggle_label.add_css_class("immersive-toggle-label")
        toggle_row.append(toggle_label)

        self._immersive_switch = Gtk.Switch()
        self._immersive_switch.set_active(True)
        self._immersive_switch.set_valign(Gtk.Align.CENTER)
        self._immersive_switch.connect("state-set", self._on_immersive_toggled)
        toggle_row.append(self._immersive_switch)

        self.append(toggle_row)

        # ─── Counter + Current Package ────────────────
        center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        center_box.set_halign(Gtk.Align.CENTER)
        center_box.set_margin_top(16)
        center_box.set_margin_bottom(12)

        self._counter_label = Gtk.Label(label="0 / 0")
        self._counter_label.add_css_class("progress-counter")
        center_box.append(self._counter_label)

        progress_label = Gtk.Label(label="PACKAGES")
        progress_label.add_css_class("progress-label")
        center_box.append(progress_label)

        self.append(center_box)

        # ─── Current Package Name ─────────────────────
        self._current_pkg_label = Gtk.Label(label="Preparing...")
        self._current_pkg_label.add_css_class("progress-current-pkg")
        self._current_pkg_label.set_halign(Gtk.Align.CENTER)
        self.append(self._current_pkg_label)

        # ─── Overall Progress Bar ─────────────────────
        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.set_margin_top(12)
        self._progress_bar.set_margin_bottom(8)
        self._progress_bar.add_css_class("progress-overall-bar")
        self._progress_bar.set_show_text(False)
        self.append(self._progress_bar)

        # ─── Status Text ─────────────────────────────
        self._status_label = Gtk.Label(label="Initializing...")
        self._status_label.add_css_class("progress-status")
        self._status_label.set_halign(Gtk.Align.CENTER)
        self.append(self._status_label)

        # ─── Cancel Button ────────────────────────────
        self._cancel_btn = Gtk.Button(label="Cancel Installation")
        self._cancel_btn.add_css_class("nav-button-skip")
        self._cancel_btn.set_halign(Gtk.Align.CENTER)
        self._cancel_btn.set_margin_top(8)
        self._cancel_btn.connect("clicked", self._on_cancel_clicked)
        self._cancel_btn.set_visible(False)
        self.append(self._cancel_btn)

        # ─── Immersive "Loading Screen" Panel ──────────
        # A toggleable game-style loading screen: big art + rotating tips,
        # instead of the raw log — shown by default, switch to compare.
        immersive_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        immersive_panel.add_css_class("immersive-panel")
        immersive_panel.set_valign(Gtk.Align.CENTER)
        immersive_panel.set_vexpand(True)
        immersive_panel.set_margin_top(20)

        icon_path = app_icon_path()
        if icon_path:
            immersive_icon = Gtk.Image.new_from_file(str(icon_path))
            immersive_icon.set_pixel_size(64)
        else:
            immersive_icon = Gtk.Image.new_from_icon_name("system-run-symbolic")
            immersive_icon.set_pixel_size(56)
        immersive_icon.add_css_class("immersive-icon")
        immersive_icon.set_halign(Gtk.Align.CENTER)
        immersive_panel.append(immersive_icon)

        now_label = Gtk.Label(label="NOW INSTALLING")
        now_label.add_css_class("immersive-now-installing")
        now_label.set_halign(Gtk.Align.CENTER)
        immersive_panel.append(now_label)

        self._immersive_pkg_label = Gtk.Label(label="Preparing...")
        self._immersive_pkg_label.add_css_class("immersive-pkg-name")
        self._immersive_pkg_label.set_halign(Gtk.Align.CENTER)
        self._immersive_pkg_label.set_wrap(True)
        self._immersive_pkg_label.set_justify(Gtk.Justification.CENTER)
        immersive_panel.append(self._immersive_pkg_label)

        self._immersive_tip_label = Gtk.Label(label=INSTALL_TIPS[0])
        self._immersive_tip_label.add_css_class("immersive-tip")
        self._immersive_tip_label.set_halign(Gtk.Align.CENTER)
        self._immersive_tip_label.set_wrap(True)
        self._immersive_tip_label.set_justify(Gtk.Justification.CENTER)
        self._immersive_tip_label.set_max_width_chars(50)
        immersive_panel.append(self._immersive_tip_label)

        self._immersive_panel = immersive_panel
        self.append(immersive_panel)

        # ─── Detail View: Log + Per-Package Result Cards ──
        detail_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self._log_scroll = Gtk.ScrolledWindow()
        self._log_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._log_scroll.set_min_content_height(120)
        self._log_scroll.set_max_content_height(160)
        self._log_scroll.add_css_class("log-scroll")
        self._log_scroll.set_margin_top(20)

        self._log_label = Gtk.Label(label="Initializing logs...")
        self._log_label.add_css_class("log-text")
        self._log_label.set_halign(Gtk.Align.START)
        self._log_label.set_valign(Gtk.Align.START)
        self._log_label.set_wrap(True)
        self._log_scroll.set_child(self._log_label)
        detail_box.append(self._log_scroll)

        # Per-package result cards
        self._result_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._result_box.set_margin_top(16)
        self._result_box.set_margin_bottom(8)
        self._result_box.set_hexpand(True)
        detail_box.append(self._result_box)

        # The window has a fixed size — a long result list must scroll
        # rather than overflow past the visible page.
        self._detail_scroll = Gtk.ScrolledWindow()
        self._detail_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._detail_scroll.set_vexpand(True)
        self._detail_scroll.set_child(detail_box)
        self._detail_scroll.set_visible(False)
        self.append(self._detail_scroll)

        # ─── Entrance animation ────────────────────────
        for w in (title, subtitle, toggle_row, center_box, self._current_pkg_label,
                  self._progress_bar, self._status_label):
            w.set_opacity(0)
        stagger_fade_in(
            [title, subtitle, toggle_row, center_box, self._current_pkg_label,
             self._progress_bar, self._status_label],
            start_delay=80, step=70,
        )

        if self._immersive_switch.get_active():
            self._start_tip_rotation()

    # ─── Immersive Loading Screen ──────────────────────

    def _on_immersive_toggled(self, _switch, state):
        self._immersive_panel.set_visible(state)
        self._detail_scroll.set_visible(not state)
        if state:
            self._start_tip_rotation()
        else:
            self._stop_tip_rotation()
        return False

    def _start_tip_rotation(self):
        if self._tip_timer_id is not None:
            return
        self._tip_timer_id = GLib.timeout_add_seconds(4, self._cycle_tip)

    def _stop_tip_rotation(self):
        if self._tip_timer_id is not None:
            GLib.source_remove(self._tip_timer_id)
            self._tip_timer_id = None

    def _cycle_tip(self):
        self._tip_index = (self._tip_index + 1) % len(INSTALL_TIPS)
        self._swap_text(self._immersive_tip_label, INSTALL_TIPS[self._tip_index])
        return True

    @staticmethod
    def _swap_text(label, text):
        """Set new text with a quick crossfade via a replayable CSS keyframe."""
        label.set_text(text)
        label.remove_css_class("text-swap-fade")
        GLib.idle_add(label.add_css_class, "text-swap-fade")

    def start_installation(self, packages):
        """Begin installing the selected packages."""
        if not packages:
            self._status_label.set_text("No packages to install")
            self._stop_tip_rotation()
            GLib.timeout_add(800, lambda: self.on_complete([]))
            return

        self._total = len(packages)
        self._counter_label.set_text(f"0 / {self._total}")
        self._cancel_btn.set_visible(True)
        self._cancel_btn.set_sensitive(True)

        self.installer.install_packages_sequential(
            packages=packages,
            on_package_start=self._on_package_start,
            on_output=self._on_output,
            on_package_complete=self._on_package_complete,
            on_all_complete=self._on_all_complete,
        )

    def _on_package_start(self, pkg, index, total):
        """Called when a package installation begins."""
        display = pkg.display_name
        if pkg.source == "flatpak":
            display += " (Flatpak)"
        elif pkg.source == "pacman":
            display += " (Pacman)"

        self._current_pkg_label.set_text(display)
        self._status_label.set_text(f"Installing {display}...")
        self._counter_label.set_text(f"{index + 1} / {total}")
        self._swap_text(self._immersive_pkg_label, display)

        # Pulse progress
        fraction = index / total
        self._progress_bar.set_fraction(fraction)

    def _on_output(self, line):
        """Show output in the local log area and global log."""
        current_text = self._log_label.get_text()
        # Keep only last 20 lines for performance
        lines = (current_text + "\n" + line).split("\n")[-20:]
        self._log_label.set_text("\n".join(lines))
        
        window = self.get_root()
        if hasattr(window, "append_log"):
            window.append_log(line)

    def _on_package_complete(self, pkg, status, index, total):
        """Called when a package finishes installing."""
        self._results.append((pkg, status))

        # Create detailed result card
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        row.add_css_class("package-card")
        row.set_margin_start(4)
        row.set_margin_end(4)

        # Status icon
        if status == "installed":
            icon_text = "✓"
            css_class = "status-installed"
        elif status == "skipped":
            icon_text = "↷"
            css_class = "status-skipped"
        else:
            icon_text = "✗"
            css_class = "status-failed"

        icon = Gtk.Label(label=icon_text)
        icon.add_css_class(css_class)
        icon.set_valign(Gtk.Align.CENTER)
        row.append(icon)

        # Package icon
        pkg_icon = Gtk.Image()
        pkg_icon.set_pixel_size(32)
        pkg_icon.set_valign(Gtk.Align.CENTER)
        
        if pkg.domain:
            from ckdeps.backend.icon_loader import icon_loader
            def on_icon_loaded(pixbuf):
                if pixbuf:
                    pkg_icon.set_from_pixbuf(pixbuf)
                else:
                    pkg_icon.set_from_icon_name(pkg.icon_name or "package-x-generic")
            icon_loader.load_icon_async(f"https://icon.horse/icon/{pkg.domain}", pkg.icon_name, 32, on_icon_loaded)
        else:
            pkg_icon.set_from_icon_name(pkg.icon_name or "package-x-generic")
        
        row.append(pkg_icon)

        # Info Box (Name + Description)
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info_box.set_valign(Gtk.Align.CENTER)
        info_box.set_hexpand(True)

        name = Gtk.Label(label=pkg.display_name)
        name.add_css_class("summary-pkg-name")
        name.set_halign(Gtk.Align.START)
        info_box.append(name)

        desc = Gtk.Label(label=pkg.description)
        desc.add_css_class("package-desc")
        desc.set_halign(Gtk.Align.START)
        info_box.append(desc)
        row.append(info_box)

        # Right side box (Source + Status)
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        right_box.set_valign(Gtk.Align.CENTER)

        status_label = Gtk.Label(label=status.upper())
        status_label.add_css_class(css_class)
        status_label.set_halign(Gtk.Align.END)
        right_box.append(status_label)

        source_label = {"aur": "AUR", "pacman": "PACMAN", "flatpak": "FLATPAK"}.get(pkg.source, pkg.source.upper())
        source_badge = Gtk.Label(label=source_label)
        source_badge.add_css_class("package-source-badge")
        source_badge.add_css_class(f"badge-{pkg.source}")
        source_badge.set_halign(Gtk.Align.END)
        right_box.append(source_badge)

        row.append(right_box)

        self._result_box.append(row)

        # Update progress
        fraction = (index + 1) / total
        self._progress_bar.set_fraction(fraction)

    def _on_cancel_clicked(self, _btn):
        """Stop installation after the current package finishes."""
        self._cancel_btn.set_sensitive(False)
        self._cancel_btn.set_label("Cancelling...")
        self._status_label.set_text("Stopping after the current package...")
        self.installer.cancel()

    def _on_all_complete(self, results):
        """Called when all packages are done."""
        self._results = results
        self._stop_tip_rotation()
        self._cancel_btn.set_visible(False)
        self._progress_bar.set_fraction(1.0)
        self._current_pkg_label.set_text("Complete!")
        self._status_label.set_text("Transitioning to Summary...")

        # Immediate transition to Summary
        GLib.timeout_add(800, lambda: self.on_complete(self._results))
