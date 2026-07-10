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


class CKDEPSWindow(Adw.ApplicationWindow):
    """Main application window with page-based wizard navigation."""

    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("CKDEPS")
        self.set_default_size(900, 620)
        self.set_size_request(750, 500)
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
        title_widget = Adw.WindowTitle(
            title="CKDEPS",
            subtitle="CachyOS KDE Personal Stuff"
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
        quit_btn.connect("clicked", lambda _: self._on_finish())
        header.append(quit_btn)

        handle.set_child(header)
        main_box.append(handle)

        # ─── Main Content Stack ──────────────────────
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self._stack.set_transition_duration(400)
        self._stack.set_vexpand(True)

        # ─── Create Pages ─────────────────────────────
        self._splash_page = SplashPage()
        self._stack.add_named(self._splash_page, "splash")

        self._welcome_page = WelcomePage(on_begin=self._go_to_bootstrap)
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
        self._stack.set_visible_child_name("splash")
        self._splash_page.start_animation()
        
        # Transition to welcome after 2.5 seconds
        GLib.timeout_add(2500, self._show_welcome)

    def _show_welcome(self):
        """Transition from splash to welcome."""
        self._stack.set_visible_child_name("welcome")
        self._welcome_page.focus_entry()
        return False

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
        """Show the bootstrap page and start it."""
        self._terminal_log = "" # Reset log
        self._installer.sudo_password = password
        self._bootstrap_page.start_bootstrap()
        self._stack.set_visible_child_name("bootstrap")

    def _go_back_to_welcome(self):
        """Go back to welcome from packages/bootstrap."""
        self._stack.set_visible_child_name("welcome")

    def _go_back_to_packages(self):
        """Go back to packages selection from extras."""
        self._stack.set_visible_child_name("packages")

    def append_log(self, line):
        """Append a line to the global terminal log."""
        self._terminal_log += line + "\n"

    def _go_to_packages(self):
        """Navigate to package selection page."""
        self._stack.set_visible_child_name("packages")
        self._packages_page.load_status()

    def _go_to_extras(self, selected_packages):
        """Navigate to extras page."""
        self._selected_packages = selected_packages
        self._stack.set_visible_child_name("extras")

    def _go_to_progress(self, selected_extras):
        """Navigate to progress page and start installation."""
        self._start_time = time.time()
        self._selected_extras = selected_extras
        self._stack.set_visible_child_name("progress")

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
            on_extra_complete=self._on_extra_done,
            on_all_complete=self._on_all_extras_done,
        )

    def _on_install_complete(self, package_results):
        """Navigate to summary page after packages are done."""
        self._package_results = package_results

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

        if self._selected_extras:
            self._installer.run_extras(
                extras=self._selected_extras,
                installed_packages=installed_names,
                on_extra_complete=self._on_extra_done,
                on_all_complete=self._on_all_extras_done,
            )
        else:
            # No extras, just Brave fix runs automatically
            self._installer.run_extras(
                extras=[],
                installed_packages=installed_names,
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
        self._summary_page.populate(self._package_results, self._extras_results, duration, self._terminal_log)
        self._stack.set_visible_child_name("summary")

    def _on_finish(self):
        """Close the application."""
        self.get_application().quit()
