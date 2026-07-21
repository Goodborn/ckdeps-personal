# 🚀 CKDEPS

**CKDEPS — A personal initial (fresh install) app to get CachyOS KDE ready.**

CKDEPS is a personal initial (fresh install) app to my liking to get CachyOS KDE ready for my personal use.

![CKDEPS](https://img.shields.io/badge/GTK4-Adwaita-a855f7?style=for-the-badge)
![License](https://img.shields.io/badge/license-GPL--3.0-green?style=for-the-badge)
![Arch](https://img.shields.io/badge/CachyOS-Arch_Linux-1793d1?style=for-the-badge)

---

## 📋 Package List

### AUR (8)
| Package | Description |
|---------|-------------|
| eden | Modern development tool |
| millennium | Steam skin manager |
| namida-bin | Beautiful music and video player |
| opencode-desktop-bin | AI-powered coding assistant |
| popcorntime | Stream movies |
| spotiflac-bin | Get Spotify tracks in true FLAC from Tidal, Qobuz & Amazon Music |
| vm-curator-bin | VM management tool |
| visual-studio-code-bin | Modern code editor |

> **Note:** `vm-curator-bin` also installs `qemu-full` and `sdl2` as dependencies.

### Pacman (Official) (13)
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
| gnome-disk-utility | Disk management utility for automounting and configuring drives |
| openrgb | RGB lighting control |

### Flatpak (13)
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
| Rufin | Music client for Jellyfin, Subsonic, and Navidrome |
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

## 📄 License

GPL-3.0-or-later — see [LICENSE](LICENSE) for details.
