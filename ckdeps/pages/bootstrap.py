"""Bootstrap page — system preparation with live progress."""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib


BOOTSTRAP_STEPS = [
    {
        "key": "system_update",
        "name": "System Update",
        "short": "Run pacman -Syu to update all packages",
        "description": "Highly recommended before installing anything. "
                       "Ensures your system is up to date and avoids dependency conflicts.",
        "default": True,
    },
    {
        "key": "base_deps",
        "name": "Base Dependencies",
        "short": "Install git, base-devel, and flatpak",
        "description": "Required for CKDEPS to work. Installs build tools, git, "
                       "and the Flatpak runtime needed by this app.",
        "default": True,
    },
    {
        "key": "aur_helper",
        "name": "Yay AUR Helper",
        "short": "Install yay to access AUR packages",
        "description": "Needed to install packages from the AUR (Arch User Repository). "
                       "Without this, AUR packages will be unavailable on the next page.",
        "default": True,
    },
    {
        "key": "flathub",
        "name": "Flathub Repository",
        "short": "Add the Flathub remote for Flatpak",
        "description": "Needed to install Flatpak apps. Without this, "
                       "Flatpak packages will be unavailable on the next page.",
        "default": True,
    },
]


class BootstrapPage(Gtk.Box):
    """System bootstrap page with optional steps and live tracking."""

    def __init__(self, installer, on_complete: callable):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("page-container")
        self.installer = installer
        self.on_complete = on_complete
        self._step_rows = []
        self._checkboxes = {}
        self._step_keys = [s["key"] for s in BOOTSTRAP_STEPS]
        self._complete = False

        # ─── Header ──────────────────────────────────
        title = Gtk.Label(label="System Bootstrap")
        title.add_css_class("page-title")
        title.set_halign(Gtk.Align.START)
        self.append(title)

        subtitle = Gtk.Label(
            label="Choose which steps to run — uncheck anything you've already done"
        )
        subtitle.add_css_class("page-subtitle")
        subtitle.set_halign(Gtk.Align.START)
        self.append(subtitle)

        # ─── Steps List ──────────────────────────────
        steps_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        steps_box.set_margin_bottom(8)

        for i, step in enumerate(BOOTSTRAP_STEPS):
            row = self._create_step_row(step, i)
            steps_box.append(row)

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

        # ─── Start / Continue Buttons ────────────────
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.END)

        self._start_btn = Gtk.Button(label="Start Bootstrap →")
        self._start_btn.add_css_class("nav-button-primary")
        self._start_btn.connect("clicked", lambda _: self.start_bootstrap())
        btn_box.append(self._start_btn)

        self._continue_btn = Gtk.Button(label="Continue →")
        self._continue_btn.add_css_class("nav-button-primary")
        self._continue_btn.set_visible(False)
        self._continue_btn.connect("clicked", lambda _: self.on_complete())
        btn_box.append(self._continue_btn)

        self.append(btn_box)

    def _create_step_row(self, step, index):
        """Create a bootstrap step row with checkbox."""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.add_css_class("bootstrap-step")
        row.add_css_class("bootstrap-step-pending")

        # Checkbox
        check = Gtk.CheckButton()
        check.set_active(step["default"])
        check.set_valign(Gtk.Align.CENTER)
        row.append(check)
        self._checkboxes[step["key"]] = check

        # Step number
        num = Gtk.Label(label=f"{index + 1}")
        num.set_size_request(24, 24)
        num.add_css_class("step-status")
        row.append(num)

        # Info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        info_box.set_hexpand(True)

        name_label = Gtk.Label(label=step["name"])
        name_label.add_css_class("step-title")
        name_label.add_css_class("step-title-pending")
        name_label.set_halign(Gtk.Align.START)
        info_box.append(name_label)

        short_label = Gtk.Label(label=step["short"])
        short_label.add_css_class("feature-desc")
        short_label.set_halign(Gtk.Align.START)
        info_box.append(short_label)

        desc_label = Gtk.Label(label=step["description"])
        desc_label.add_css_class("package-desc")
        desc_label.set_halign(Gtk.Align.START)
        desc_label.set_wrap(True)
        info_box.append(desc_label)

        row.append(info_box)

        # Status indicator
        status = Gtk.Label(label="⏳")
        status.add_css_class("step-status")
        row.append(status)

        self._step_rows.append({
            "row": row,
            "title": name_label,
            "status": status,
            "num": num,
            "check": check,
            "key": step["key"],
        })

        return row

    def get_selected_steps(self):
        """Return list of selected step keys."""
        return [k for k, cb in self._checkboxes.items() if cb.get_active()]

    def has_aur_helper(self):
        """Check if AUR helper step is selected."""
        return self._checkboxes.get("aur_helper", Gtk.CheckButton()).get_active()

    def has_flathub(self):
        """Check if Flathub step is selected."""
        return self._checkboxes.get("flathub", Gtk.CheckButton()).get_active()

    def start_bootstrap(self):
        """Begin the bootstrap process for selected steps."""
        selected = self.get_selected_steps()
        if not selected:
            self._status_label.set_text("No steps selected — skipping bootstrap")
            self._on_all_complete([])
            return

        # Disable checkboxes and start button
        for cb in self._checkboxes.values():
            cb.set_sensitive(False)
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

        # Find row index by key
        idx = self._step_keys.index(step_key) if step_key in self._step_keys else -1

        # Update previous step as done
        for row_data in self._step_rows:
            if row_data["key"] == step_key:
                break
            if row_data["row"].has_css_class("bootstrap-step-active"):
                row_data["row"].remove_css_class("bootstrap-step-active")
                row_data["row"].add_css_class("bootstrap-step-done")
                row_data["title"].remove_css_class("step-title-active")
                row_data["title"].add_css_class("step-title-done")
                row_data["status"].set_text("✓")

        # Mark current step as active
        if 0 <= idx < len(self._step_rows):
            current = self._step_rows[idx]
            current["row"].remove_css_class("bootstrap-step-pending")
            current["row"].add_css_class("bootstrap-step-active")
            current["title"].remove_css_class("step-title-pending")
            current["title"].add_css_class("step-title-active")
            current["status"].set_text("⚙️")

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
            if row_data["row"].has_css_class("bootstrap-step-active"):
                row_data["row"].remove_css_class("bootstrap-step-active")
                row_data["row"].add_css_class("bootstrap-step-done")
                row_data["title"].remove_css_class("step-title-active")
                row_data["title"].add_css_class("step-title-done")
                row_data["status"].set_text("✓")

        # Skip unchecked steps visually
        for row_data in self._step_rows:
            if not row_data["check"].get_active():
                row_data["status"].set_text("—")
                row_data["title"].set_opacity(0.4)

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
