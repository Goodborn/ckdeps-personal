PREFIX ?= /usr
DESTDIR ?=
LIBDIR = $(PREFIX)/lib/ckdeps
BINDIR = $(PREFIX)/bin
DATADIR = $(PREFIX)/share
ICONDIR = $(DATADIR)/icons/hicolor/scalable/apps
APPDIR = $(DATADIR)/applications
METADIR = $(DATADIR)/metainfo
CSSDIR = $(DATADIR)/ckdeps

.PHONY: install uninstall deps

deps:
	# Install system dependencies if pacman is available (Arch/CachyOS)
	@if command -v pacman > /dev/null; then \
		echo "📦 Installing system dependencies..."; \
		sudo pacman -S --needed --noconfirm python-gobject gtk4 libadwaita flatpak librsvg; \
	fi

install: deps
	# Install Python package
	install -dm755 "$(DESTDIR)$(LIBDIR)/ckdeps"
	install -dm755 "$(DESTDIR)$(LIBDIR)/ckdeps/backend"
	install -dm755 "$(DESTDIR)$(LIBDIR)/ckdeps/pages"
	install -dm755 "$(DESTDIR)$(LIBDIR)/ckdeps/resources"
	install -Dm644 ckdeps/__init__.py "$(DESTDIR)$(LIBDIR)/ckdeps/__init__.py"
	install -Dm644 ckdeps/main.py "$(DESTDIR)$(LIBDIR)/ckdeps/main.py"
	install -Dm644 ckdeps/window.py "$(DESTDIR)$(LIBDIR)/ckdeps/window.py"
	install -Dm644 ckdeps/backend/__init__.py "$(DESTDIR)$(LIBDIR)/ckdeps/backend/__init__.py"
	install -Dm644 ckdeps/backend/installer.py "$(DESTDIR)$(LIBDIR)/ckdeps/backend/installer.py"
	install -Dm644 ckdeps/backend/package_data.py "$(DESTDIR)$(LIBDIR)/ckdeps/backend/package_data.py"
	install -Dm644 ckdeps/backend/icon_loader.py "$(DESTDIR)$(LIBDIR)/ckdeps/backend/icon_loader.py"
	install -Dm644 ckdeps/pages/__init__.py "$(DESTDIR)$(LIBDIR)/ckdeps/pages/__init__.py"
	install -Dm644 ckdeps/pages/splash.py "$(DESTDIR)$(LIBDIR)/ckdeps/pages/splash.py"
	install -Dm644 ckdeps/pages/welcome.py "$(DESTDIR)$(LIBDIR)/ckdeps/pages/welcome.py"
	install -Dm644 ckdeps/pages/bootstrap.py "$(DESTDIR)$(LIBDIR)/ckdeps/pages/bootstrap.py"
	install -Dm644 ckdeps/pages/packages.py "$(DESTDIR)$(LIBDIR)/ckdeps/pages/packages.py"
	install -Dm644 ckdeps/pages/extras.py "$(DESTDIR)$(LIBDIR)/ckdeps/pages/extras.py"
	install -Dm644 ckdeps/pages/progress.py "$(DESTDIR)$(LIBDIR)/ckdeps/pages/progress.py"
	install -Dm644 ckdeps/pages/summary.py "$(DESTDIR)$(LIBDIR)/ckdeps/pages/summary.py"

	# Install CSS
	install -Dm644 ckdeps/resources/style.css "$(DESTDIR)$(CSSDIR)/style.css"

	# Install binary
	install -Dm755 bin/ckdeps "$(DESTDIR)$(BINDIR)/ckdeps"

	# Install desktop file
	install -Dm644 data/com.goodborn.ckdeps.desktop "$(DESTDIR)$(APPDIR)/com.goodborn.ckdeps.desktop"

	# Install icon
	install -Dm644 data/com.goodborn.ckdeps.svg "$(DESTDIR)$(ICONDIR)/com.goodborn.ckdeps.svg"

	# Install metainfo
	install -Dm644 data/com.goodborn.ckdeps.metainfo.xml "$(DESTDIR)$(METADIR)/com.goodborn.ckdeps.metainfo.xml"

uninstall:
	rm -rf "$(DESTDIR)$(LIBDIR)"
	rm -f  "$(DESTDIR)$(BINDIR)/ckdeps"
	rm -f  "$(DESTDIR)$(APPDIR)/com.goodborn.ckdeps.desktop"
	rm -f  "$(DESTDIR)$(ICONDIR)/com.goodborn.ckdeps.svg"
	rm -f  "$(DESTDIR)$(METADIR)/com.goodborn.ckdeps.metainfo.xml"
	rm -f  "$(DESTDIR)$(CSSDIR)/style.css"
	rmdir --ignore-fail-on-non-empty "$(DESTDIR)$(CSSDIR)" 2>/dev/null || true

run:
	python3 -m ckdeps
