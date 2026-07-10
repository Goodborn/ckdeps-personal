"""Backend installer — runs all shell commands in background threads."""

import subprocess
import shutil
import os
import threading
from pathlib import Path
from typing import Callable, Optional

import gi
gi.require_version("GLib", "2.0")
from gi.repository import GLib

from .package_data import Package, ExtraConfig


class Installer:
    """Manages package installation and system configuration in background threads."""

    def __init__(self):
        self._cancel = False
        self.sudo_password = None

    def cancel(self):
        """Request cancellation of current operations."""
        self._cancel = True

    # ─── Status Checks ───────────────────────────────────────────

    def is_pacman_installed(self, pkg_name: str) -> bool:
        """Check if a package is installed via pacman."""
        try:
            result = subprocess.run(
                ["pacman", "-Qi", pkg_name],
                capture_output=True, timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def is_flatpak_installed(self, flatpak_id: str) -> bool:
        """Check if a Flatpak app is installed."""
        try:
            result = subprocess.run(
                ["flatpak", "list", "--app", "--columns=application"],
                capture_output=True, text=True, timeout=10
            )
            return flatpak_id in result.stdout.split('\n')
        except Exception:
            return False

    def is_installed(self, pkg: Package) -> bool:
        """Check if a package is installed via any method."""
        if self.is_pacman_installed(pkg.name):
            return True
        if pkg.flatpak_id and self.is_flatpak_installed(pkg.flatpak_id):
            return True
        return False

    def has_yay(self) -> bool:
        """Check if yay AUR helper is available."""
        return shutil.which("yay") is not None

    def has_flatpak(self) -> bool:
        """Check if flatpak is available."""
        return shutil.which("flatpak") is not None

    # ─── Async Runners ───────────────────────────────────────────

    def _run_in_thread(self, func, *args):
        """Run a function in a background thread."""
        thread = threading.Thread(target=func, args=args, daemon=True)
        thread.start()
        return thread

    def _run_command(self, cmd: list[str], on_output: Optional[Callable] = None,
                     use_pkexec: bool = False) -> tuple[bool, str]:
        """Run a command, optionally streaming output. Returns (success, full_output)."""
        if use_pkexec:
            cmd = ["pkexec"] + cmd

        use_stdin = False
        if self.sudo_password:
            if cmd[0] == "sudo":
                cmd.insert(1, "-S")
                use_stdin = True
            elif cmd[0] == "yay":
                cmd = ["yay", "--sudoflags", "-S"] + cmd[1:]
                use_stdin = True

        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE if use_stdin else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            if use_stdin:
                process.stdin.write(self.sudo_password + "\n")
                process.stdin.flush()
                process.stdin.close()

            output_lines = []
            for line in iter(process.stdout.readline, ""):
                if self._cancel:
                    process.terminate()
                    return False, "Cancelled"
                output_lines.append(line.rstrip())
                if on_output:
                    GLib.idle_add(on_output, line.rstrip())

            process.wait()
            return process.returncode == 0, "\n".join(output_lines)

        except FileNotFoundError:
            msg = f"Command not found: {cmd[0]}"
            if on_output:
                GLib.idle_add(on_output, msg)
            return False, msg
        except Exception as e:
            msg = f"Error: {str(e)}"
            if on_output:
                GLib.idle_add(on_output, msg)
            return False, msg

    # ─── Bootstrap ───────────────────────────────────────────────

    def bootstrap_system(self, selected_steps: list[str], on_step: Callable,
                         on_output: Callable, on_complete: Callable):
        """Run selected bootstrap steps in background."""
        def _work():
            results = []
            step_map = {
                "system_update": ("System Update", ["sudo", "pacman", "-Syu", "--noconfirm"]),
                "base_deps": ("Base Dependencies", ["sudo", "pacman", "-S", "--needed", "--noconfirm",
                              "git", "base-devel", "flatpak"]),
            }

            for key in selected_steps:
                if self._cancel:
                    break

                if key == "aur_helper":
                    GLib.idle_add(on_step, "Installing yay AUR helper...", key)
                    if self.has_yay():
                        results.append(("Yay AUR Helper", True))
                    else:
                        import tempfile
                        tmpdir = tempfile.mkdtemp()
                        success, _ = self._run_command(
                            ["git", "clone", "https://aur.archlinux.org/yay.git",
                             os.path.join(tmpdir, "yay")], on_output
                        )
                        if success:
                            success, _ = self._run_command(
                                ["bash", "-c",
                                 f"cd {os.path.join(tmpdir, 'yay')} && makepkg -si --noconfirm"],
                                on_output
                            )
                        results.append(("Yay AUR Helper", success))
                        try:
                            import shutil as sh
                            sh.rmtree(tmpdir, ignore_errors=True)
                        except Exception:
                            pass

                elif key == "flathub":
                    GLib.idle_add(on_step, "Adding Flathub repository...", key)
                    success, _ = self._run_command(
                        ["flatpak", "remote-add", "--if-not-exists", "flathub",
                         "https://flathub.org/repo/flathub.flatpakrepo"], on_output
                    )
                    results.append(("Flathub Repository", success))

                elif key in step_map:
                    name, cmd = step_map[key]
                    GLib.idle_add(on_step, f"Running {name}...", key)
                    success, _ = self._run_command(cmd, on_output)
                    results.append((name, success))

            GLib.idle_add(on_complete, results)

        self._run_in_thread(_work)

    # ─── Package Installation ────────────────────────────────────

    def install_package(self, pkg: Package, on_output: Callable,
                        on_complete: Callable):
        """Install a single package in background."""
        def _work():
            if self.is_installed(pkg):
                GLib.idle_add(on_complete, pkg, "skipped")
                return

            if pkg.source == "flatpak" and pkg.flatpak_id:
                success, _ = self._run_command(
                    ["sudo", "flatpak", "install", "-y", "flathub", pkg.flatpak_id],
                    on_output
                )
            elif pkg.source == "pacman":
                success, _ = self._run_command(
                    ["sudo", "pacman", "-S", "--needed", "--noconfirm", pkg.name],
                    on_output
                )
            else:
                success, _ = self._run_command(
                    ["yay", "-S", "--needed", "--noconfirm", pkg.name],
                    on_output
                )

            status = "installed" if success else "failed"
            GLib.idle_add(on_complete, pkg, status)

        self._run_in_thread(_work)

    def install_packages_sequential(self, packages: list[Package],
                                    on_package_start: Callable,
                                    on_output: Callable,
                                    on_package_complete: Callable,
                                    on_all_complete: Callable):
        """Install multiple packages sequentially in background."""
        def _work():
            results = []
            for i, pkg in enumerate(packages):
                if self._cancel:
                    break

                GLib.idle_add(on_package_start, pkg, i, len(packages))

                if self.is_installed(pkg):
                    GLib.idle_add(on_package_complete, pkg, "skipped", i, len(packages))
                    results.append((pkg, "skipped"))
                    continue

                if pkg.source == "flatpak" and pkg.flatpak_id:
                    success, _ = self._run_command(
                        ["sudo", "flatpak", "install", "-y", "flathub", pkg.flatpak_id],
                        on_output
                    )
                elif pkg.source == "pacman":
                    success, _ = self._run_command(
                        ["sudo", "pacman", "-S", "--needed", "--noconfirm", pkg.name],
                        on_output
                    )
                else:
                    success, _ = self._run_command(
                        ["yay", "-S", "--needed", "--noconfirm", pkg.name],
                        on_output
                    )

                status = "installed" if success else "failed"
                GLib.idle_add(on_package_complete, pkg, status, i, len(packages))
                results.append((pkg, status))

            GLib.idle_add(on_all_complete, results)

        self._run_in_thread(_work)

    # ─── Extras ──────────────────────────────────────────────────

    def run_extras(self, extras: list[ExtraConfig], installed_packages: list[str],
                   newly_installed: list[str] = None,
                   on_extra_complete: Callable = None, on_all_complete: Callable = None):
        """Run selected configuration extras in background."""
        if newly_installed is None:
            newly_installed = []
        def _work():
            results = []

            for extra in extras:
                if self._cancel:
                    break

                if extra.key == "aliases":
                    result = self._setup_aliases()
                elif extra.key == "fish_config":
                    result = self._setup_fish_config()
                elif extra.key == "disable_recent":
                    result = self._disable_recent_files()
                elif extra.key == "performance_mode":
                    result = self._set_performance_mode()
                else:
                    result = ("skipped", "Unknown extra")

                results.append((extra.title, result))
                GLib.idle_add(on_extra_complete, extra.title, result)

            # Bolt Launcher Java dependency — only if bolt was newly installed this session
            if "bolt-launcher" in newly_installed:
                result = self._install_java()
                results.append(("Java Runtime (Bolt)", result))
                GLib.idle_add(on_extra_complete, "Java Runtime (Bolt)", result)

            GLib.idle_add(on_all_complete, results)

        self._run_in_thread(_work)

    def _setup_aliases(self) -> tuple[str, str]:
        """Set up custom aliases."""
        home = Path.home()
        alias_file = home / "CustomScripts" / "aliases.fish"

        if alias_file.exists():
            return ("exists", "File already exists")

        alias_file.parent.mkdir(parents=True, exist_ok=True)
        alias_file.write_text(r"""# Weather function (defaults to Gjilan unless a location is provided)
function weather
    set -l location Gjilan

    if test (count $argv) -gt 0
        set location $argv[1]
    end

    curl "wttr.in/$location"
end

######################################################

alias ls='eza --icons --group-directories-first --grid'

######################################################

# Update system (yay -Syu)
function system_update
    sudo pacman -Syu
end

function aur_update
    yay -Syu
end

######################################################

# App removal function (yay -Rns)
function remove
    if test (count $argv) -eq 0
        set_color red
        echo "Usage: remove <package>"
        set_color normal
        return 1
    end

    set -l pkg $argv[1]

    set_color blue
    echo "Removing package: $pkg..."
    set_color normal

    yay -Rns "$pkg"
    or return 1

    set_color green
    echo "Package removed: $pkg"
    set_color normal

    echo
    set_color blue
    echo "Post-removal cleanup options:"
    set_color normal
    echo "  [1] Remove orphaned dependencies (yay -Yc)"
    echo "  [2] Clean package cache (sudo paccache -r)"
    echo "  [3] Remove user leftovers (~/.config, ~/.cache, ~/.local/share)"
    echo "  [Enter] Do nothing"
    echo

    read -P "Choose options (e.g. 1 2 3): " choices

    if test -z "$choices"
        set_color green
        echo "No cleanup performed."
        set_color normal
        return 0
    end

    for choice in $choices
        switch $choice

            case 1
                set_color blue
                echo "Removing orphaned dependencies..."
                set_color normal
                yay -Yc

            case 2
                set_color blue
                echo "Cleaning package cache..."
                set_color normal
                sudo paccache -r

            case 3
                set_color blue
                echo "Checking leftovers for: $pkg"
                set_color normal

                set -l found 0

                set -l dirs \
                    "$HOME/.config/$pkg" \
                    "$HOME/.cache/$pkg" \
                    "$HOME/.local/share/$pkg"

                for dir in $dirs
                    if test -e "$dir"
                        set_color yellow
                        echo "Found: $dir"
                        set_color normal
                        set found 1
                    end
                end

                if test $found -eq 1
                    read -P "Remove these directories? [y/N]: " confirm

                    if string match -qr '^[Yy]$' -- $confirm
                        for dir in $dirs
                            if test -e "$dir"
                                rm -rf "$dir"
                            end
                        end

                        set_color green
                        echo "Leftovers removed."
                        set_color normal
                    end
                else
                    set_color green
                    echo "No leftovers found."
                    set_color normal
                end

            case '*'
                set_color red
                echo "Unknown option: $choice"
                set_color normal
        end
    end

    set_color green
    echo "Done."
    set_color normal
end

######################################################

# alias train='sl'
# Run the train in terminal

######################################################

# Edit this file, reload it, and show aliases (if mylist exists)
alias editalias='micro ~/CustomScripts/aliases.fish; and source ~/CustomScripts/aliases.fish; and functions -q mylist; and mylist'
""")

        # Source in fish config
        fish_config = home / ".config" / "fish" / "config.fish"
        if fish_config.exists():
            content = fish_config.read_text()
            if "aliases.fish" not in content:
                with open(fish_config, "a") as f:
                    f.write(
                        "\n# CKDEPS aliases\n"
                        "test -f ~/CustomScripts/aliases.fish && "
                        "source ~/CustomScripts/aliases.fish\n"
                    )

        return ("success", "Fish aliases configured")

    def _setup_fish_config(self) -> tuple[str, str]:
        """Set up fish config.fish with Starship, TheFuck, Atuin, Zoxide, aliases, and command duration."""
        home = Path.home()
        fish_dir = home / ".config" / "fish"
        fish_config = fish_dir / "config.fish"
        fish_dir.mkdir(parents=True, exist_ok=True)

        # Check if already configured
        if fish_config.exists():
            content = fish_config.read_text()
            if "CKDEPS" in content:
                return ("exists", "Fish config already configured")

        config_content = r"""# ═══════════════════════════════════════════════════════
# CKDEPS — Fish Shell Configuration
# ═══════════════════════════════════════════════════════

# overwrite greeting
# potentially disabling fastfetch
#function fish_greeting
#    # smth smth
#end

# Starship
starship init fish | source

# The Fuck
thefuck --alias fk | source

# Atuin
atuin init fish | source

# Zoxide
zoxide init fish | source

# My custom aliases
source ~/CustomScripts/aliases.fish

# ───────── Command duration (right prompt) ─────────

set -g __cmd_start 0
set -g __cmd_duration ""

function __cmd_timer_start --on-event fish_preexec
    set -g __cmd_start (date +%s%N)
end

function __cmd_timer_end --on-event fish_postexec
    set -l end (date +%s%N)
    set -l elapsed_ms (math "($end - $__cmd_start) / 1000000")

    if test $elapsed_ms -lt 500
        set -g __cmd_duration ""
        return
    end

    if test $elapsed_ms -ge 60000
        set -l mins (math -s0 "$elapsed_ms / 60000")
        set -l secs (math -s0 "($elapsed_ms % 60000) / 1000")
        set -g __cmd_duration "󱎫 $mins m $secs s"
    else
        set -l secs (math -s2 "$elapsed_ms / 1000")
        set -g __cmd_duration "󱎫 $secs s"
    end
end

function fish_right_prompt
    if test -n "$__cmd_duration"
        set_color yellow
        echo -n "$__cmd_duration"
        set_color normal
    end
end
"""

        # Backup existing config
        if fish_config.exists():
            import shutil
            backup = fish_config.with_suffix(".fish.bak")
            shutil.copy2(fish_config, backup)

        fish_config.write_text(config_content)
        return ("success", "Fish config written (backup saved as config.fish.bak)")

    def _setup_solaar(self, installed: list[str]) -> tuple[str, str]:
        """Add Solaar to Hyprland startup."""
        if "solaar" not in installed:
            return ("skipped", "Solaar not installed")

        cfg = Path.home() / ".config" / "hypr" / "UserConfigs" / "Startup_Apps.conf"
        cfg.parent.mkdir(parents=True, exist_ok=True)

        if cfg.exists() and "solaar" in cfg.read_text():
            return ("exists", "Startup entry already exists")

        with open(cfg, "a") as f:
            f.write("exec-once = solaar -w hide\n")

        return ("success", "Added to Hyprland startup")

    def _disable_recent_files(self) -> tuple[str, str]:
        """Disable GNOME recent files tracking."""
        try:
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.privacy",
                 "remember-recent-files"],
                capture_output=True, text=True, timeout=5
            )
            if "false" in result.stdout:
                return ("exists", "Already disabled")

            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.privacy",
                 "remember-recent-files", "false"],
                capture_output=True, timeout=5
            )
            return ("success", "Recent files disabled")
        except Exception as e:
            return ("failed", str(e))

    def _set_performance_mode(self) -> tuple[str, str]:
        """Set power profile to performance."""
        if not shutil.which("powerprofilesctl"):
            return ("failed", "powerprofilesctl not found")
        
        success, _ = self._run_command(["powerprofilesctl", "set", "performance"])
        if success:
            return ("success", "Performance mode enabled")
        return ("failed", "Failed to set performance mode")

    def _install_java(self) -> tuple[str, str]:
        """Install JRE for Bolt Launcher."""
        if self.is_pacman_installed("jre-openjdk"):
            return ("exists", "Already installed")

        success, _ = self._run_command(
            ["yay", "-S", "--needed", "--noconfirm", "jre-openjdk"]
        )
        if success:
            return ("success", "jre-openjdk installed for Bolt Launcher")
        return ("failed", "Failed to install jre-openjdk")

    # ─── Status Check All Packages ───────────────────────────────

    def check_all_status(self, packages: list[Package],
                         on_complete: Callable):
        """Check installation status of all packages in background."""
        def _work():
            for pkg in packages:
                pkg.installed = self.is_installed(pkg)
            GLib.idle_add(on_complete, packages)

        self._run_in_thread(_work)

