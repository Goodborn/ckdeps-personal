"""Package definitions for CKDEPS."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Package:
    """Represents a single installable package."""
    name: str
    display_name: str
    description: str
    icon_name: str
    category: str
    source: str  # "aur", "pacman", or "flatpak"
    domain: Optional[str] = None
    flatpak_id: Optional[str] = None
    installed: bool = False
    selected: bool = False


@dataclass
class ExtraConfig:
    """Represents a system configuration extra."""
    key: str
    title: str
    description: str
    icon_name: str
    selected: bool = False
    status: str = ""


# ---------- AUR Packages ----------
AUR_PACKAGES = [
    Package("eden", "Eden", "Modern development tool", "applications-development", "Development", "aur", domain="github.com"),
    Package("millennium", "Millennium", "Steam skin manager", "steam", "Gaming", "aur", domain="github.com"),
    Package("namida-bin", "Namida", "Beautiful music and video player", "multimedia-audio-player", "Media", "aur", domain="github.com"),
    Package("opencode-desktop-bin", "OpenCode Desktop", "AI-powered coding assistant", "code", "Development", "aur", domain="github.com"),
    Package("visual-studio-code-bin", "VS Code", "Modern code editor", "visual-studio-code", "Development", "aur", domain="code.visualstudio.com"),
]

# ---------- Pacman (Official) Packages ----------
PACMAN_PACKAGES = [
    Package("thefuck", "TheFuck", "Corrects console commands", "utilities-terminal", "Terminal Tools", "pacman", domain="github.com"),
    Package("fzf", "FZF", "Fuzzy finder for the terminal", "edit-find", "Terminal Tools", "pacman", domain="github.com"),
    Package("atuin", "Atuin", "Magical shell history manager", "appointment-soon", "Terminal Tools", "pacman", domain=None),
    Package("zoxide", "Zoxide", "Smarter cd command", "folder", "Terminal Tools", "pacman", domain="github.com"),
    Package("bazaar", "Bazaar", "Version control system", "git", "Terminal Tools", "pacman", domain="gnu.org"),
    Package("anydesk-bin", "AnyDesk", "Remote desktop", "preferences-desktop-remote-desktop", "Remote & Networking", "pacman", domain=None),
    Package("libreoffice-still", "LibreOffice", "Office suite", "libreoffice-main", "Productivity", "pacman", domain="libreoffice.org"),
    Package("betterbird", "Betterbird", "Email client", "mail-client", "Productivity", "pacman", domain="betterbird.eu"),
    Package("popcorntime", "Popcorn Time", "Stream movies", "video-display", "Media", "pacman", domain="popcorntime.app"),
    Package("qbittorrent", "qBittorrent", "BitTorrent client", "qbittorrent", "Networking", "pacman", domain="qbittorrent.org"),
    Package("obs-studio", "OBS Studio", "Live streaming", "obs", "Media", "pacman", domain="obsproject.com"),
    Package("brave-origin-bin", "Brave Browser", "Privacy-focused web browser", "brave-browser", "Internet", "pacman", domain="brave.com"),
    Package("kolourpaint", "KolourPaint", "Easy-to-use paint program", "kolourpaint", "Media", "pacman", domain="kde.org"),
    Package("vm-curator-bin", "VM Curator", "VM management tool", "computer", "Development", "pacman", domain="github.com"),
    Package("gpu-screen-recorder", "GPU Screen Recorder", "Fastest GPU-accelerated screen recorder", "video-display", "Media", "pacman", domain="git.dec05eba.com"),
]

# ---------- Flatpak Packages ----------
FLATPAK_PACKAGES = [
    Package("appflowy", "AppFlowy", "Open-source Notion alternative", "io.appflowy.AppFlowy", "Productivity", "flatpak", domain="appflowy.io",
            flatpak_id="io.appflowy.AppFlowy"),
    Package("blanket", "Blanket", "Ambient sound player", "com.rafaelmardojai.Blanket", "Media", "flatpak", domain=None,
            flatpak_id="com.rafaelmardojai.Blanket"),
    Package("bolt-launcher", "Bolt Launcher", "RuneScape launcher", "com.adamcake.Bolt", "Gaming", "flatpak", domain="adamcake.com",
            flatpak_id="com.adamcake.Bolt"),
    Package("cozy", "Cozy", "Audiobook player", "com.github.geigi.cozy", "Media", "flatpak", domain=None,
            flatpak_id="com.github.geigi.cozy"),
    Package("discord", "Discord", "Messaging and voice chat", "com.discordapp.Discord", "Communication", "flatpak", domain="discord.com",
            flatpak_id="com.discordapp.Discord"),
    Package("foliate", "Foliate", "Modern e-book reader", "com.github.johnfactotum.Foliate", "Productivity", "flatpak", domain=None,
            flatpak_id="com.github.johnfactotum.Foliate"),
    Package("haruna", "Haruna", "KDE media player", "org.kde.haruna", "Media", "flatpak", domain="haruna.kde.org",
            flatpak_id="org.kde.haruna"),
    Package("kdenlive", "Kdenlive", "Professional video editor", "org.kde.kdenlive", "Media", "flatpak", domain="kdenlive.org",
            flatpak_id="org.kde.kdenlive"),
    Package("proton-vpn-gtk-app", "Proton VPN", "Secure VPN application", "network-vpn", "Networking", "flatpak", domain="protonvpn.com",
            flatpak_id="com.protonvpn.www"),
    Package("readest", "Readest", "Modern ebook reader", "com.bilingify.readest", "Productivity", "flatpak", domain=None,
            flatpak_id="com.bilingify.readest"),
    Package("upscayl", "Upscayl", "AI image upscaler", "org.upscayl.Upscayl", "Media", "flatpak", domain="upscayl.org",
            flatpak_id="org.upscayl.Upscayl"),
]

ALL_PACKAGES = AUR_PACKAGES + PACMAN_PACKAGES + FLATPAK_PACKAGES

# ---------- Extras ----------
EXTRAS = [
    ExtraConfig("aliases", "Custom Aliases", "Install ~/CustomScripts/aliases.zsh with useful shortcuts",
                "utilities-terminal"),
    ExtraConfig("disable_recent", "Disable Recent Files", "Turn off GNOME recent file tracking for privacy",
                "preferences-system-privacy"),
    ExtraConfig("performance_mode", "Performance Mode", "Set power profiles to performance (ideal for desktops)",
                "power-profile-performance-symbolic"),
]

# ---------- Category Colors (for UI) ----------
CATEGORY_COLORS = {
    "Terminal Tools": "#a855f7",
    "Desktop": "#6366f1",
    "Remote & Networking": "#0ea5e9",
    "Productivity": "#10b981",
    "Gaming": "#f59e0b",
    "Media": "#ec4899",
    "Development": "#8b5cf6",
    "Networking": "#06b6d4",
    "Communication": "#6366f1",
    "Hardware": "#f97316",
    "Internet": "#ef4444",
}
