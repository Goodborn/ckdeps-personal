"""Package selection page — beautiful card grid with checkboxes."""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Pango

from ..backend.package_data import ALL_PACKAGES, AUR_PACKAGES, PACMAN_PACKAGES, FLATPAK_PACKAGES, CATEGORY_COLORS
from ..backend.icon_loader import icon_loader


class PackagesPage(Gtk.Box):
    """Package selection page with categorized card grid."""

    def __init__(self, installer, on_continue: callable, on_back: callable):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("page-container")
        self.installer = installer
        self.on_continue = on_continue
        self.on_back = on_back
        self._cards = {}  # pkg.name -> (card_widget, check_button)
        self._all_packages = list(ALL_PACKAGES)  # Make copies
        self._layout_mode = "compact"  # Default to compact
        self._has_aur = True
        self._has_flatpak = True
        for pkg in self._all_packages:
            pkg.selected = False

        # ─── Header Row ──────────────────────────────
        header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header_row.set_margin_bottom(8)

        header_left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header_left.set_hexpand(True)

        title = Gtk.Label(label="Select Packages")
        title.add_css_class("page-title")
        title.set_halign(Gtk.Align.START)
        header_left.append(title)

        subtitle = Gtk.Label(label="Choose which packages to install • Green border = already installed")
        subtitle.add_css_class("page-subtitle")
        subtitle.set_halign(Gtk.Align.START)
        header_left.append(subtitle)

        header_row.append(header_left)

        # Action buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_valign(Gtk.Align.CENTER)

        select_all_btn = Gtk.Button(label="Select All")
        select_all_btn.add_css_class("select-all-btn")
        select_all_btn.connect("clicked", self._on_select_all)
        btn_box.append(select_all_btn)

        deselect_btn = Gtk.Button(label="Deselect All")
        deselect_btn.add_css_class("nav-button")
        deselect_btn.connect("clicked", self._on_deselect_all)
        btn_box.append(deselect_btn)

        # Layout Toggle
        self._layout_btn = Gtk.Button()
        self._layout_btn.set_icon_name("view-list-symbolic")
        self._layout_btn.add_css_class("nav-button")
        self._layout_btn.set_tooltip_text("Toggle Compact/Detailed Layout")
        self._layout_btn.connect("clicked", self._on_toggle_layout)
        btn_box.append(self._layout_btn)

        header_row.append(btn_box)
        self.append(header_row)

        # ─── Loading Spinner ─────────────────────────
        self._loading_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._loading_box.set_valign(Gtk.Align.CENTER)
        self._loading_box.set_vexpand(True)

        spinner = Gtk.Spinner()
        spinner.add_css_class("spinner-large")
        spinner.set_spinning(True)
        self._loading_box.append(spinner)

        loading_label = Gtk.Label(label="Checking installed packages...")
        loading_label.add_css_class("progress-status")
        self._loading_box.append(loading_label)

        self.append(self._loading_box)

        # ─── Scrollable Package Grid ─────────────────
        self._scroll = Gtk.ScrolledWindow()
        self._scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._scroll.set_vexpand(True)
        self._scroll.set_visible(False)

        self._grid_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._scroll.set_child(self._grid_box)
        self.append(self._scroll)

        # ─── Navigation ──────────────────────────────
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        nav_box.set_halign(Gtk.Align.END)
        nav_box.set_margin_top(10)

        self._selected_label = Gtk.Label(label="0 selected")
        self._selected_label.add_css_class("page-subtitle")
        self._selected_label.set_hexpand(True)
        self._selected_label.set_halign(Gtk.Align.START)
        nav_box.append(self._selected_label)

        back_btn = Gtk.Button(label="← Back")
        back_btn.add_css_class("nav-button")
        back_btn.connect("clicked", lambda _: self.on_back())
        nav_box.append(back_btn)

        self._skip_btn = Gtk.Button(label="Skip Installation")
        self._skip_btn.add_css_class("nav-button-skip")
        self._skip_btn.connect("clicked", lambda _: self.on_continue([]))
        self._skip_btn.set_visible(True)
        nav_box.append(self._skip_btn)

        self._continue_btn = Gtk.Button(label="Install Selected →")
        self._continue_btn.add_css_class("nav-button-primary")
        self._continue_btn.connect("clicked", self._on_continue_clicked)
        self._continue_btn.set_sensitive(False)
        nav_box.append(self._continue_btn)

        self.append(nav_box)

    def load_status(self, has_aur=True, has_flatpak=True):
        """Check installation status of all packages."""
        self._has_aur = has_aur
        self._has_flatpak = has_flatpak
        self.installer.check_all_status(self._all_packages, self._on_status_loaded)

    def _on_status_loaded(self, packages):
        """Build the package grid after status check."""
        self._all_packages = packages
        self._loading_box.set_visible(False)
        self._scroll.set_visible(True)
        self._build_grid()

    def _build_grid(self):
        """Build the package card grid grouping by source type."""
        aur_pkgs = [p for p in self._all_packages if p.source == "aur"]
        pacman_pkgs = [p for p in self._all_packages if p.source == "pacman"]
        flatpak_pkgs = [p for p in self._all_packages if p.source == "flatpak"]

        groups = [
            ("AUR Packages", aur_pkgs, self._has_aur),
            ("Pacman (Official) Packages", pacman_pkgs, True),
            ("Flatpak Packages", flatpak_pkgs, self._has_flatpak),
        ]

        for title, pkgs, available in groups:
            if not pkgs:
                continue

            # Section Header
            header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            header_box.set_halign(Gtk.Align.START)

            header = Gtk.Label(label=title.upper())
            header.add_css_class("category-header")
            header.set_halign(Gtk.Align.START)
            header_box.append(header)

            if not available:
                notice = Gtk.Label(label="(unavailable — complete bootstrap step first)")
                notice.add_css_class("package-desc")
                notice.set_halign(Gtk.Align.START)
                header_box.append(notice)

            self._grid_box.append(header_box)

            # Flow box for cards
            flow = Gtk.FlowBox()
            flow.set_valign(Gtk.Align.START)
            flow.set_max_children_per_line(5)
            flow.set_min_children_per_line(2)
            flow.set_selection_mode(Gtk.SelectionMode.NONE)
            flow.set_homogeneous(True)
            flow.set_column_spacing(6)
            flow.set_row_spacing(6)
            flow.add_css_class("package-grid")
            if self._layout_mode == "compact":
                flow.set_max_children_per_line(30)
                flow.set_homogeneous(True)
                flow.add_css_class("layout-compact")
            else:
                flow.set_max_children_per_line(1)
                flow.set_homogeneous(False)
                flow.add_css_class("layout-detailed")

            for i, pkg in enumerate(pkgs):
                try:
                    card = self._create_package_card(pkg, available=available)
                    card.set_visible(True)
                    flow.append(card)
                except Exception as e:
                    print(f"Error creating card for {pkg.name}: {e}")

            flow.set_visible(True)
            self._grid_box.append(flow)

    def _create_package_card(self, pkg, available=True):
        """Create a single compact package card widget with animated description revealer."""

        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        card.add_css_class("package-card")
        if pkg.installed:
            card.add_css_class("installed")
        if not available:
            card.set_opacity(0.35)
            card.set_sensitive(False)
        elif pkg.installed:
            card.set_opacity(0.5)
            card.set_sensitive(False)

        # Checkbox
        check = Gtk.CheckButton()
        check.set_active(pkg.selected if (available and not pkg.installed) else False)
        check.set_valign(Gtk.Align.START)
        check.set_margin_top(4)
        check.set_sensitive(available and not pkg.installed)
        check.connect("toggled", self._on_package_toggled, pkg, card)
        card.append(check)

        # Icon (Always visible)
        icon_image = Gtk.Image()
        icon_image.set_pixel_size(24)
        icon_image.set_valign(Gtk.Align.CENTER)
        card.append(icon_image)

        if pkg.domain:
            url = f"https://icon.horse/icon/{pkg.domain}"
            def on_icon_loaded(pixbuf):
                if pixbuf:
                    icon_image.set_from_pixbuf(pixbuf)
                else:
                    icon_image.set_from_icon_name(pkg.icon_name or "package-x-generic")
            icon_loader.load_icon_async(url, pkg.icon_name, 24, on_icon_loaded)
        else:
            icon_image.set_from_icon_name(pkg.icon_name or "package-x-generic")

        # Content container
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        content_box.set_hexpand(True)
        content_box.set_valign(Gtk.Align.CENTER)

        # Info Box (Icon + Name + Badges)
        info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        info_box.set_hexpand(True)
        info_box.set_valign(Gtk.Align.CENTER)
        

        # Name and Badges on the same line for compactness
        name_badge_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        name_badge_box.set_hexpand(True)
        name_badge_box.set_valign(Gtk.Align.CENTER)

        name_label = Gtk.Label(label=pkg.display_name)
        name_label.add_css_class("package-name")
        name_label.set_halign(Gtk.Align.START)
        name_label.set_valign(Gtk.Align.CENTER)
        name_label.set_margin_top(2)
        name_label.set_ellipsize(Pango.EllipsizeMode.END)
        name_badge_box.append(name_label)

        # Badges aligned to the right
        badge_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        badge_row.set_halign(Gtk.Align.END)
        badge_row.set_hexpand(True)
        badge_row.set_valign(Gtk.Align.CENTER)
        
        source_label = {"aur": "AUR", "pacman": "PACMAN", "flatpak": "FLATPAK"}.get(pkg.source, pkg.source.upper())
        source_badge = Gtk.Label(label=source_label)
        source_badge.add_css_class("package-source-badge")
        source_badge.add_css_class(f"badge-{pkg.source}")
        source_badge.set_valign(Gtk.Align.CENTER)
        badge_row.append(source_badge)

        if pkg.installed:
            installed_badge = Gtk.Label(label="✓")
            installed_badge.add_css_class("package-source-badge")
            installed_badge.add_css_class("installed-badge")
            installed_badge.set_valign(Gtk.Align.CENTER)
            badge_row.append(installed_badge)

        name_badge_box.append(badge_row)
        info_box.append(name_badge_box)
        content_box.append(info_box)

        # Animated Revealer for Description
        revealer = Gtk.Revealer()
        revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        revealer.set_transition_duration(300)
        
        desc_label = Gtk.Label(label=pkg.description)
        desc_label.add_css_class("package-desc")
        desc_label.set_wrap(True)
        desc_label.set_halign(Gtk.Align.START)
        desc_label.set_margin_top(4)
        revealer.set_child(desc_label)
        
        content_box.append(revealer)
        card.append(content_box)

        # Info Button (Separate from selection)
        info_btn = Gtk.Button()
        info_btn.set_icon_name("info-symbolic")
        info_btn.add_css_class("card-info-button")
        info_btn.set_valign(Gtk.Align.CENTER)
        info_btn.set_halign(Gtk.Align.END)
        info_btn.connect("clicked", lambda _: revealer.set_reveal_child(not revealer.get_reveal_child()))
        card.append(info_btn)

        if self._layout_mode == "compact":
            card.add_css_class("compact")
            info_btn.add_css_class("compact")
            icon_image.set_pixel_size(16)
            
        # Click gesture to toggle the CHECKBOX (reverted)
        gesture = Gtk.GestureClick()
        def on_card_click(gesture, n_press, x, y):
            check.set_active(not check.get_active())
        gesture.connect("pressed", on_card_click)
        content_box.add_controller(gesture)

        self._cards[pkg.name] = (card, check)
        return card
        
    @staticmethod
    def _fade_in(widget):
        """Animate card entrance."""
        widget.set_opacity(1)
        widget.add_css_class("animated-enter")
        return False

    def _on_package_toggled(self, check_button, pkg, card):
        """Handle package checkbox toggle."""
        pkg.selected = check_button.get_active()
        if pkg.selected:
            card.add_css_class("selected")
        else:
            card.remove_css_class("selected")
        self._update_selected_count()

    def _update_selected_count(self):
        """Update the selected count label and button states."""
        count = sum(1 for p in self._all_packages if p.selected)
        self._selected_label.set_text(f"{count} package{'s' if count != 1 else ''} selected")
        self._continue_btn.set_sensitive(count > 0)
        self._skip_btn.set_visible(count == 0)

    def _on_select_all(self, _btn):
        """Select all packages."""
        for pkg in self._all_packages:
            pkg.selected = True
            if pkg.name in self._cards:
                card, check = self._cards[pkg.name]
                check.set_active(True)
                card.add_css_class("selected")
        self._update_selected_count()

    def _on_deselect_all(self, _btn):
        """Deselect all packages."""
        for pkg in self._all_packages:
            pkg.selected = False
            if pkg.name in self._cards:
                card, check = self._cards[pkg.name]
                check.set_active(False)
                card.remove_css_class("selected")
        self._update_selected_count()

    def _on_toggle_layout(self, _btn):
        """Switch between compact and detailed view."""
        if self._layout_mode == "detailed":
            self._layout_mode = "compact"
            self._layout_btn.set_icon_name("view-grid-symbolic")
        else:
            self._layout_mode = "detailed"
            self._layout_btn.set_icon_name("view-list-symbolic")
        
        # Clear and rebuild the grid
        child = self._grid_box.get_first_child()
        while child:
            self._grid_box.remove(child)
            child = self._grid_box.get_first_child()
            
        self._cards.clear()
        self._build_grid()

    def _on_continue_clicked(self, _btn):
        """Continue with selected packages."""
        selected = [p for p in self._all_packages if p.selected]
        self.on_continue(selected)

    def get_all_packages(self):
        """Return the full package list with current status."""
        return self._all_packages
