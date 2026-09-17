"""Main application window — manages page navigation with Adw.Carousel."""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, GLib
import time

import os
from pathlib import Path

from .backend.installer import Installer
from .pages.splash import SplashPage
from .pages.welcome import WelcomePage
from .pages.bootstrap import BootstrapPage
from .pages.packages import PackagesPage
from .pages.extras import ExtrasPage
from .pages.progress import ProgressPage
from .pages.summary import SummaryPage
from .widgets import StepIndicator


class CKDEPSWindow(Adw.ApplicationWindow):
    """Main application window with page-based wizard navigation."""

    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("CKDEPS")
        self.set_default_size(1040, 720)
        self.set_size_request(820, 560)
        self.set_decorated(False)
        self.add_css_class("ckdeps-window")

        self._installer = Installer()
        self._selected_packages = []
        self._selected_extras = []
        self._package_results = []
        self._extras_results = []
        self._terminal_log = ""
        self._start_time = 0

        # ─── Load Custom CSS ─────────────────────────
        self._load_css()

        # ─── Main Layout ─────────────────────────────
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Title widget
        from .backend.distro import friendly_name
        title_widget = Adw.WindowTitle(
            title="CKDEPS",
            subtitle=f"{friendly_name()} KDE Personal Stuff"
        )
        # ─── Custom Header (Undecorated Window) ───────
        handle = Gtk.WindowHandle()
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header.add_css_class("custom-header")
        
        # Title/Logo in header
        header.append(title_widget)
        
        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header.append(spacer)

        # Quit Button
        quit_btn = Gtk.Button()
        quit_btn.set_icon_name("window-close-symbolic")
        quit_btn.add_css_class("header-quit-button")
        quit_btn.set_tooltip_text("Quit Application")
        quit_btn.connect("clicked", lambda _: self._request_close())
        header.append(quit_btn)

        # Guard every close path (this button, Ctrl+Q, the WM) so an
        # installation in progress can't be silently interrupted.
        self.connect("close-request", self._on_close_request)

        handle.set_child(header)
        main_box.append(handle)

        # ─── Step Indicator ───────────────────────────
        self._step_indicator = StepIndicator()
        self._step_indicator.set_margin_bottom(4)
        main_box.append(self._step_indicator)

        # ─── Main Content Stack ──────────────────────
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self._stack.set_transition_duration(400)
        self._stack.set_vexpand(True)

        # ─── Create Pages ─────────────────────────────
        self._splash_page = SplashPage()
        self._stack.add_named(self._splash_page, "splash")

        self._welcome_page = WelcomePage(installer=self._installer, on_begin=self._go_to_bootstrap)
        self._stack.add_named(self._welcome_page, "welcome")

        self._bootstrap_page = BootstrapPage(
            installer=self._installer,
            on_complete=self._go_to_packages,
        )
        self._stack.add_named(self._bootstrap_page, "bootstrap")

        self._packages_page = PackagesPage(
            installer=self._installer,
            on_continue=self._go_to_extras,
            on_back=self._go_back_to_welcome,
        )
        self._stack.add_named(self._packages_page, "packages")

        self._extras_page = ExtrasPage(
            installer=self._installer,
            on_continue=self._go_to_progress,
            on_back=self._go_back_to_packages,
        )
        self._stack.add_named(self._extras_page, "extras")

        self._progress_page = ProgressPage(
            installer=self._installer,
            on_complete=self._on_install_complete,
        )
        self._stack.add_named(self._progress_page, "progress")

        self._summary_page = SummaryPage(
            on_close=self._on_finish,
        )
        self._stack.add_named(self._summary_page, "summary")

        main_box.append(self._stack)
        self.set_content(main_box)

        # Start on splash
        self._step_indicator.set_visible(False)
        self._stack.set_visible_child_name("splash")
        self._splash_page.start_animation()

        # Transition to welcome after 2.5 seconds
        GLib.timeout_add(2500, self._show_welcome)

    def _show_welcome(self):
        """Transition from splash to welcome."""
        self._step_indicator.set_visible(True)
        self._navigate_to("welcome")
        self._welcome_page.focus_entry()
        return False

    def _navigate_to(self, page_name: str):
        """Switch the stack page and keep the step indicator in sync."""
        self._stack.set_visible_child_name(page_name)
        self._step_indicator.set_active(page_name)

    def _load_css(self):
        """Load custom CSS from resources."""
        css_provider = Gtk.CssProvider()

        # Try multiple paths for CSS
        css_paths = [
            # Development path
            Path(__file__).parent / "resources" / "style.css",
            # Installed path
            Path("/usr/share/ckdeps/style.css"),
        ]

        for css_path in css_paths:
            if css_path.exists():
                css_provider.load_from_path(str(css_path))
                Gtk.StyleContext.add_provider_for_display(
                    Gdk.Display.get_default(),
                    css_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
                )
                break

    # ─── Page Navigation ──────────────────────────────

    def _go_to_bootstrap(self, password):
        """Show the bootstrap page."""
        self._terminal_log = ""
        self._installer.sudo_password = password
        self._navigate_to("bootstrap")

    def _go_back_to_welcome(self):
        """Go back to welcome from packages/bootstrap."""
        self._navigate_to("welcome")

    def _go_back_to_packages(self):
        """Go back to packages selection from extras."""
        self._navigate_to("packages")

    def append_log(self, line):
        """Append a line to the global terminal log."""
        self._terminal_log += line + "\n"

    def _go_to_packages(self):
        """Navigate to package selection page with bootstrap state."""
        # Check if tools are available — either bootstrap was selected OR already installed
        has_aur = (
            self._bootstrap_page.has_aur_helper()
            or self._installer.has_yay()
        )
        has_flatpak = (
            self._bootstrap_page.has_flathub()
            or self._installer.has_flatpak()
        )
        self._navigate_to("packages")
        self._packages_page.load_status(has_aur=has_aur, has_flatpak=has_flatpak)

    def _go_to_extras(self, selected_packages):
        """Navigate to extras page."""
        self._selected_packages = selected_packages
        self._navigate_to("extras")
        self._extras_page.load_status()

    def _go_to_progress(self, selected_extras):
        """Navigate to progress page and start installation."""
        self._start_time = time.time()
        self._selected_extras = selected_extras
        self._navigate_to("progress")

        if self._selected_packages:
            self._progress_page.start_installation(self._selected_packages)
        else:
            # Skip straight to extras processing
            self._run_extras_only()

    def _run_extras_only(self):
        """Run only extras (no packages selected)."""
        installed_names = [
            p.name for p in self._packages_page.get_all_packages()
            if p.installed
        ]
        self._installer.run_extras(
            extras=self._selected_extras,
            installed_packages=installed_names,
            newly_installed=[],
            on_extra_complete=self._on_extra_done,
            on_all_complete=self._on_all_extras_done,
        )

    def _on_install_complete(self, package_results):
        """Navigate to summary page after packages are done."""
        self._package_results = package_results

        if self._installer.was_cancelled:
            # Don't chain into extras — the user asked us to stop.
            self._installer.reset_cancel()
            self._on_all_extras_done([])
            return

        # Now run extras
        installed_names = [
            p.name for p, s in package_results if s in ("installed", "skipped")
        ]
        # Also include already-installed packages
        installed_names += [
            p.name for p in self._packages_page.get_all_packages()
            if p.installed
        ]
        installed_names = list(set(installed_names))

        # Only newly installed this session (not already installed before)
        newly_installed = [
            p.name for p, s in package_results if s == "installed"
        ]

        if self._selected_extras:
            self._installer.run_extras(
                extras=self._selected_extras,
                installed_packages=installed_names,
                newly_installed=newly_installed,
                on_extra_complete=self._on_extra_done,
                on_all_complete=self._on_all_extras_done,
            )
        else:
            self._installer.run_extras(
                extras=[],
                installed_packages=installed_names,
                newly_installed=newly_installed,
                on_extra_complete=self._on_extra_done,
                on_all_complete=self._on_all_extras_done,
            )

    def _on_extra_done(self, name, result):
        """Called when an extra finishes."""
        self._extras_results.append((name, result))

    def _on_all_extras_done(self, results):
        """Called when all extras are done, show summary."""
        duration = time.time() - self._start_time
        self._extras_results = results
        final_log_path = self._installer.finalize_log()
        self._summary_page.populate(
            self._package_results, self._extras_results, duration,
            self._terminal_log, final_log_path,
        )
        self._navigate_to("summary")

    def _request_close(self):
        """Ask the window to close through the normal close-request path,
        so the quit button and Ctrl+Q share the same in-progress guard as
        the window manager's own close signal."""
        self.close()

    def _on_close_request(self, *_args) -> bool:
        """Intercept every close path. If nothing is running, quit normally;
        otherwise warn before allowing pacman/yay to be interrupted."""
        if self._installer.busy:
            self._confirm_quit_during_install()
            return True  # stop the default handler; we decide when to close

        self._on_finish()
        return True

    def _confirm_quit_during_install(self):
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Installation in progress",
            body=(
                "CKDEPS is still installing packages or applying changes. "
                "Quitting now can leave pacman locked or your system "
                "half-configured.\n\n"
                "You can stop the current operation safely and keep the "
                "app open, or force quit anyway."
            ),
        )
        dialog.add_response("stay", "Keep Installing")
        dialog.add_response("stop", "Stop, Stay Open")
        dialog.add_response("force-quit", "Force Quit")
        dialog.set_response_appearance("stop", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_response_appearance("force-quit", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("stay")
        dialog.set_close_response("stay")
        dialog.connect("response", self._on_quit_confirm_response)
        dialog.present()

    def _on_quit_confirm_response(self, _dialog, response):
        if response == "stop":
            self._installer.cancel()
        elif response == "force-quit":
            self._installer.cancel()
            self._on_finish()

    def _on_finish(self):
        """Close the application."""
        self.get_application().quit()
