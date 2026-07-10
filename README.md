# 🚀 CKDEPS

**CKDEPS — A personal initial (fresh install) app to get CachyOS KDE ready.**

CKDEPS is a personal initial (fresh install) app to my liking to get CachyOS KDE ready for my personal use.

![CKDEPS](https://img.shields.io/badge/GTK4-Adwaita-a855f7?style=for-the-badge)
![License](https://img.shields.io/badge/license-GPL--3.0-green?style=for-the-badge)
![Arch](https://img.shields.io/badge/CachyOS-Arch_Linux-1793d1?style=for-the-badge)

---

## ✨ Features

| 📦 **Smart Packages** | Personalized list of AUR + Pacman + Flatpak apps |
| ⚡ **One-Click Bootstrap** | Automates system updates and manager setup |
| 🎨 **Personal Tweaks** | Custom Fish aliases, shell config, recent files, and performance mode |
| 📊 **Live Progress** | Real-time installation tracking with log output |

## 📋 Package List

### AUR (7)
| Package | Description |
|---------|-------------|
| eden | Modern development tool |
| millennium | Steam skin manager |
| namida-bin | Beautiful music and video player |
| opencode-desktop-bin | AI-powered coding assistant |
| popcorntime | Stream movies |
| vm-curator-bin | VM management tool |
| visual-studio-code-bin | Modern code editor |

> **Note:** `vm-curator-bin` also installs `qemu-full` and `sdl2` as dependencies.

### Pacman (Official) (12)
| Package | Description |
|---------|-------------|
| thefuck | Corrects console commands |
| fzf | Fuzzy finder for the terminal |
| atuin | Magical shell history manager |
| zoxide | Smarter cd command |
| bazaar | Version control system |
| libreoffice-still | Office suite |
| betterbird | Email client |
| qbittorrent | BitTorrent client |
| obs-studio | Live streaming |
| brave-origin-bin | Privacy-focused web browser |
| kolourpaint | Easy-to-use paint program |
| gpu-screen-recorder | Fastest GPU-accelerated screen recorder |
| openrgb | RGB lighting control |

### Flatpak (12)
| Package | Description |
|---------|-------------|
| AnyDesk | Remote desktop |
| AppFlowy | Open-source Notion alternative |
| Blanket | Ambient sound player |
| Bolt Launcher | RuneScape launcher |
| Cozy | Audiobook player |
| Discord | Messaging and voice chat |
| Foliate | Modern e-book reader |
| Haruna | KDE media player |
| Kdenlive | Professional video editor |
| Proton VPN | Secure VPN application |
| Readest | Modern ebook reader |
| Upscayl | AI image upscaler |

---

## 🔧 Installation

### ⚡ One-Tap Run (Arch / CachyOS)
Copy and paste this block to launch:
```bash
git clone https://github.com/goodborn/ckdeps-personal.git && \
cd ckdeps-personal && \
make run
```

### 🚀 How to Run
After installing, you can launch the app anytime by:
1. Typing `ckdeps` in your terminal.
2. Searching for **"CKDEPS"** in your application menu.
3. Running `make run` inside the project folder.

### 🛠️ Run from Source (Development)
To test changes without installing to your system:
```bash
git clone https://github.com/goodborn/ckdeps-personal.git
cd ckdeps-personal
python3 -m ckdeps
```

---

## 🏗️ Dependencies

| Package | Purpose |
|---------|---------|
| `python` | Runtime |
| `python-gobject` | GTK4 bindings (PyGObject) |
| `gtk4` | UI toolkit |
| `libadwaita` | GNOME design language |
| `flatpak` | Flatpak package manager |
| `pacman` | Arch package manager |

---

## 📁 Project Structure

```
ckdeps-personal/
├── ckdeps/
│   ├── __init__.py
│   ├── __main__.py
│   ├── main.py              # Application entry point
│   ├── window.py            # Main window + page navigation
│   ├── backend/
│   │   ├── installer.py     # Threaded shell command execution
│   │   ├── package_data.py  # Package & extras definitions
│   │   └── icon_loader.py   # Async icon fetching
│   ├── pages/
│   │   ├── splash.py        # Splash screen
│   │   ├── welcome.py       # Welcome page
│   │   ├── bootstrap.py     # System preparation page
│   │   ├── packages.py      # Package selection grid
│   │   ├── extras.py        # System configuration extras
│   │   ├── progress.py      # Live installation tracking
│   │   └── summary.py       # Deployment report
│   └── resources/
│       └── style.css        # Premium dark theme CSS
├── bin/
│   └── ckdeps               # CLI entry point
├── data/
│   ├── com.goodborn.ckdeps.desktop
│   ├── com.goodborn.ckdeps.svg
│   └── com.goodborn.ckdeps.metainfo.xml
├── Makefile                 # Install/uninstall targets
├── PKGBUILD                 # AUR build recipe
└── .SRCINFO                 # AUR metadata
```

---

## 🎨 Design

- **Dark theme** with purple/blue gradient backgrounds
- **Glassmorphism** effects with frosted glass cards
- **Staggered fade-in** animations on page transitions
- **Live log output** with monospace terminal styling
- Custom scrollbars, switches, and checkboxes matching the theme

---

## 📄 License

GPL-3.0-or-later — see [LICENSE](LICENSE) for details.

---

**Made with 💜 by Goodborn**
