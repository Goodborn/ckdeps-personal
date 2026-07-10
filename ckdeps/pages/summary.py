"""Summary page — color-coded deployment report."""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib


class SummaryPage(Gtk.Box):
    """Final summary page with deployment report."""

    def __init__(self, on_close: callable):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("summary-container")
        self.on_close = on_close
        self._layout_mode = "compact"  # Default to compact
        self._package_results = []
        self._extras_results = []
        self._duration = 0
        self._log = ""

        # ─── Hero Section ────────────────────────────
        hero_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        hero_box.set_margin_bottom(12)
        hero_box.set_halign(Gtk.Align.CENTER)
        self.append(hero_box)

        check_icon = Gtk.Label(label="✨")
        check_icon.add_css_class("welcome-logo")
        check_icon.set_opacity(0)
        hero_box.append(check_icon)

        header = Gtk.Label(label="Deployment Successful")
        header.add_css_class("summary-header")
        header.set_opacity(0)
        hero_box.append(header)

        self._subheader = Gtk.Label(label="Your system is ready for action")
        self._subheader.add_css_class("summary-subheader")
        self._subheader.set_opacity(0)
        hero_box.append(self._subheader)

        # ─── Stats Grid ──────────────────────────────
        self._stats_grid = Gtk.Grid()
        self._stats_grid.set_column_spacing(8)
        self._stats_grid.set_row_spacing(8)
        self._stats_grid.set_halign(Gtk.Align.CENTER)
        self._stats_grid.set_margin_bottom(12)
        self._stats_grid.set_opacity(0)
        self.append(self._stats_grid)

        # ─── Results Section Title ───────────────────
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        
        self._results_title = Gtk.Label(label="DEPLOYMENT REPORT")
        self._results_title.add_css_class("summary-section-title")
        self._results_title.set_halign(Gtk.Align.START)
        self._results_title.set_hexpand(True)
        self._results_title.set_opacity(0)
        title_row.append(self._results_title)

        # Layout Toggle
        self._layout_btn = Gtk.Button()
        self._layout_btn.set_icon_name("view-list-symbolic")
        self._layout_btn.add_css_class("nav-button")
        self._layout_btn.set_opacity(0)
        self._layout_btn.set_tooltip_text("Toggle Detailed/Compact View")
        self._layout_btn.connect("clicked", self._on_toggle_layout)
        title_row.append(self._layout_btn)
        
        self.append(title_row)

        # ─── Scrollable Results ──────────────────────
        self._scroll = Gtk.ScrolledWindow()
        self._scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._scroll.set_vexpand(True)
        self._scroll.set_opacity(0)

        self._results_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._results_box.set_margin_bottom(12)
        self._scroll.set_child(self._results_box)
        self.append(self._scroll)

        # ─── Footer Section ──────────────────────────
        footer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        footer_box.set_margin_top(12)
        self.append(footer_box)

        # Close Button
        self._close_btn = Gtk.Button(label="Finish Deployment  ✦")
        self._close_btn.add_css_class("finish-button")
        self._close_btn.set_halign(Gtk.Align.CENTER)
        self._close_btn.set_opacity(0)
        self._close_btn.connect("clicked", lambda _: self.on_close())
        footer_box.append(self._close_btn)

        # Personal Signature
        signature = Gtk.Label(label="Handcrafted by Goodborn")
        signature.add_css_class("personal-signature")
        signature.set_opacity(0)
        footer_box.append(signature)

        # Store widgets for animation
        self._anim_widgets = [
            check_icon, header, self._subheader, self._stats_grid,
            self._results_title, self._scroll, self._close_btn, signature
        ]

    def populate(self, package_results, extras_results, duration=0, log=""):
        """Fill in the summary data and animate."""
        self._package_results = package_results
        self._extras_results = extras_results
        self._duration = duration
        self._log = log
        self._build_report()

    def _build_report(self):
        """Build the report based on current layout mode."""
        package_results = self._package_results
        extras_results = self._extras_results
        duration = self._duration
        # Clear existing
        child = self._stats_grid.get_first_child()
        while child:
            self._stats_grid.remove(child)
            child = self._stats_grid.get_first_child()

        child = self._results_box.get_first_child()
        while child:
            self._results_box.remove(child)
            child = self._results_box.get_first_child()

        if self._layout_mode == "compact":
            self._results_box.add_css_class("summary-grid-compact")
        else:
            self._results_box.remove_css_class("summary-grid-compact")

        # Count stats
        installed = sum(1 for _, s in package_results if s == "installed")
        skipped = sum(1 for _, s in package_results if s == "skipped")
        failed = sum(1 for _, s in package_results if s == "failed")
        extras_ok = sum(1 for _, (s, _) in extras_results if s in ("success", "exists"))

        # Format duration
        mins = int(duration // 60)
        secs = int(duration % 60)
        time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

        self._subheader.set_text(
            f"Successfully processed {len(package_results)} packages and {len(extras_results)} configurations in {time_str}"
        )

        # ─── Stats Cards ─────────────────────────────
        stats = [
            (str(installed), "Installed", "stat-number-installed", "📦"),
            (str(skipped), "Already Present", "stat-number-skipped", "✓"),
            (str(failed), "Failed", "stat-number-failed", "✗"),
            (time_str, "Total Time", "stat-number-extras", "⏱️"),
        ]

        for i, (num, label, css, icon) in enumerate(stats):
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            card.add_css_class("stat-card")
            card.set_hexpand(True)

            top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            
            icon_label = Gtk.Label(label=icon)
            icon_label.set_margin_end(8)
            top_row.append(icon_label)

            num_label = Gtk.Label(label=num)
            num_label.add_css_class("stat-number")
            num_label.add_css_class(css)
            top_row.append(num_label)
            card.append(top_row)

            text_label = Gtk.Label(label=label)
            text_label.add_css_class("stat-label")
            text_label.set_halign(Gtk.Align.START)
            card.append(text_label)

            self._stats_grid.attach(card, i % 2, i // 2, 1, 1)

        # ─── Grouped Results ─────────────────────────
        # Package Sources
        sources = {
            "aur": ("AUR / PACMAN PACKAGES", "summary-section-aur"),
            "flatpak": ("FLATPAK PACKAGES", "summary-section-flatpak")
        }

        for source_id, (title, css) in sources.items():
            results = [(p, s) for p, s in package_results if p.source == source_id]
            if results:
                section_title = Gtk.Label(label=title)
                section_title.add_css_class("summary-section-title")
                section_title.add_css_class(css)
                section_title.set_halign(Gtk.Align.START)
                section_title.set_margin_top(6)
                self._results_box.append(section_title)

                if self._layout_mode == "compact":
                    flow = Gtk.FlowBox()
                    flow.set_valign(Gtk.Align.START)
                    flow.set_max_children_per_line(20) # High limit for responsiveness
                    flow.set_min_children_per_line(1)
                    flow.set_selection_mode(Gtk.SelectionMode.NONE)
                    flow.set_column_spacing(8)
                    flow.set_row_spacing(8)
                    for pkg, status in results:
                        flow.append(self._create_result_token(pkg, status))
                    self._results_box.append(flow)
                else:
                    for pkg, status in results:
                        row = self._create_result_card(pkg, status)
                        self._results_box.append(row)

        # Extras
        if extras_results:
            section_title = Gtk.Label(label="CONFIGURATION EXTRAS")
            section_title.add_css_class("summary-section-title")
            section_title.add_css_class("summary-section-extras")
            section_title.set_halign(Gtk.Align.START)
            section_title.set_margin_top(12)
            self._results_box.append(section_title)

            for name, (status, msg) in extras_results:
                row = self._create_extra_result_row(name, status, msg)
                self._results_box.append(row)

        # ─── Terminal Log (Expander) ─────────────────
        if self._log:
            title_label = Gtk.Label(label="TECHNICAL INSTALLATION LOG")
            title_label.add_css_class("summary-section-title")
            title_label.set_halign(Gtk.Align.START)
            
            log_expander = Gtk.Expander()
            log_expander.set_label_widget(title_label)
            log_expander.set_margin_top(8)
            
            log_scroll = Gtk.ScrolledWindow()
            log_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            log_scroll.set_min_content_height(150)
            log_scroll.add_css_class("log-scroll")

            buffer = Gtk.TextBuffer()
            buffer.set_text(self._log)
            
            view = Gtk.TextView(buffer=buffer)
            view.set_editable(False)
            view.set_cursor_visible(False)
            view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
            view.add_css_class("log-text")
            log_scroll.set_child(view)
            
            log_expander.set_child(log_scroll)
            self._results_box.append(log_expander)

        # ─── Animate In ──────────────────────────────
        for i, w in enumerate(self._anim_widgets):
            GLib.timeout_add(150 + i * 100, self._fade_in, w)
        GLib.timeout_add(150 + len(self._anim_widgets) * 100, self._fade_in, self._layout_btn)

    def _on_toggle_layout(self, _btn):
        """Switch between detailed and compact view."""
        self._layout_mode = "detailed" if self._layout_mode == "compact" else "compact"
        self._layout_btn.set_icon_name("view-grid-symbolic" if self._layout_mode == "detailed" else "view-list-symbolic")
        self._build_report()

    def _create_result_token(self, pkg, status):
        """Create a very compact token for a package."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.add_css_class("summary-token")
        
        icon_map = {
            "installed": ("✓", "status-installed"),
            "skipped": ("↷", "status-skipped"),
            "failed": ("✗", "status-failed"),
        }
        icon_text, css_class = icon_map.get(status, ("?", "status-skipped"))
        
        icon = Gtk.Label(label=icon_text)
        icon.add_css_class(css_class)
        box.append(icon)

        # Package icon
        pkg_icon = Gtk.Image()
        pkg_icon.set_pixel_size(16)
        pkg_icon.set_valign(Gtk.Align.CENTER)
        
        if pkg.domain:
            from ckdeps.backend.icon_loader import icon_loader
            def on_icon_loaded(pixbuf):
                if pixbuf:
                    pkg_icon.set_from_pixbuf(pixbuf)
                else:
                    pkg_icon.set_from_icon_name(pkg.icon_name or "package-x-generic")
            icon_loader.load_icon_async(f"https://icon.horse/icon/{pkg.domain}", pkg.icon_name, 16, on_icon_loaded)
        else:
            pkg_icon.set_from_icon_name(pkg.icon_name or "package-x-generic")
            
        box.append(pkg_icon)
        
        name = Gtk.Label(label=pkg.display_name)
        name.add_css_class("summary-pkg-name-compact")
        box.append(name)
        
        return box

    def _create_result_card(self, pkg, status):
        """Create a detailed result card for a package."""
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        card.add_css_class("summary-item-card")

        # Status icon
        icon_map = {
            "installed": ("✓", "status-installed"),
            "skipped": ("↷", "status-skipped"),
            "failed": ("✗", "status-failed"),
        }
        icon_text, css_class = icon_map.get(status, ("?", "status-skipped"))

        icon = Gtk.Label(label=icon_text)
        icon.add_css_class(css_class)
        icon.add_css_class("summary-status-icon")
        icon.set_valign(Gtk.Align.CENTER)
        card.append(icon)

        # Info
        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info.set_hexpand(True)
        info.set_valign(Gtk.Align.CENTER)

        # Name + Icon Row
        name_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        name = Gtk.Label(label=pkg.display_name)
        name.add_css_class("summary-pkg-name")
        name.set_halign(Gtk.Align.START)
        name_row.append(name)

        # Package icon
        pkg_icon = Gtk.Image()
        pkg_icon.set_pixel_size(24)
        pkg_icon.set_valign(Gtk.Align.CENTER)
        
        if pkg.domain:
            from ckdeps.backend.icon_loader import icon_loader
            def on_icon_loaded(pixbuf):
                if pixbuf:
                    pkg_icon.set_from_pixbuf(pixbuf)
                else:
                    pkg_icon.set_from_icon_name(pkg.icon_name or "package-x-generic")
            icon_loader.load_icon_async(f"https://icon.horse/icon/{pkg.domain}", pkg.icon_name, 24, on_icon_loaded)
        else:
            pkg_icon.set_from_icon_name(pkg.icon_name or "package-x-generic")
            
        name_row.append(pkg_icon)
        
        info.append(name_row)

        desc = Gtk.Label(label=pkg.description)
        desc.add_css_class("package-desc")
        desc.set_halign(Gtk.Align.START)
        desc.set_ellipsize(3)
        info.append(desc)
        card.append(info)

        # Status Label
        status_label = Gtk.Label(label=status.upper())
        status_label.add_css_class(css_class)
        status_label.set_valign(Gtk.Align.CENTER)
        card.append(status_label)

        return card

    def _create_extra_result_row(self, name, status, msg):
        """Create a result row for an extra config."""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.add_css_class("summary-item")

        icon_map = {
            "success": ("✓", "status-success"),
            "exists": ("ℹ", "status-exists"),
            "skipped": ("↷", "status-skipped"),
            "failed": ("✗", "status-failed"),
        }
        icon_text, css_class = icon_map.get(status, ("?", "status-skipped"))

        icon = Gtk.Label(label=icon_text)
        icon.add_css_class(css_class)
        icon.set_valign(Gtk.Align.CENTER)
        row.append(icon)

        name_label = Gtk.Label(label=f"{name}: {msg}")
        name_label.add_css_class("summary-pkg-name")
        name_label.set_hexpand(True)
        name_label.set_halign(Gtk.Align.START)
        row.append(name_label)

        status_label = Gtk.Label(label=status.upper())
        status_label.add_css_class(css_class)
        row.append(status_label)

        return row

    @staticmethod
    def _fade_in(widget):
        """Animate widget fade-in."""
        widget.set_opacity(1)
        return False
