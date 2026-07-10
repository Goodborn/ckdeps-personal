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

    def bootstrap_system(self, on_step: Callable, on_output: Callable,
                         on_complete: Callable):
        """Run full system bootstrap in background."""
        def _work():
            steps = []

            # Step 1: System update
            GLib.idle_add(on_step, "Updating system packages...", 0)
            success, _ = self._run_command(
                ["sudo", "pacman", "-Syu", "--noconfirm"], on_output
            )
            steps.append(("System Update", success))

            if self._cancel:
                GLib.idle_add(on_complete, steps)
                return

            # Step 2: Base dependencies
            GLib.idle_add(on_step, "Installing base dependencies...", 1)
            success, _ = self._run_command(
                ["sudo", "pacman", "-S", "--needed", "--noconfirm",
                 "git", "base-devel", "flatpak"], on_output
            )
            steps.append(("Base Dependencies", success))

            if self._cancel:
                GLib.idle_add(on_complete, steps)
                return

            # Step 3: Install yay if missing
            if not self.has_yay():
                GLib.idle_add(on_step, "Installing yay AUR helper...", 2)
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
                steps.append(("Yay AUR Helper", success))
                try:
                    import shutil as sh
                    sh.rmtree(tmpdir, ignore_errors=True)
                except Exception:
                    pass
            else:
                GLib.idle_add(on_step, "Yay AUR helper already installed", 2)
                steps.append(("Yay AUR Helper", True))

            if self._cancel:
                GLib.idle_add(on_complete, steps)
                return

            # Step 4: Enable Flathub
            GLib.idle_add(on_step, "Enabling Flathub repository...", 3)
            success, _ = self._run_command(
                ["flatpak", "remote-add", "--if-not-exists", "flathub",
                 "https://flathub.org/repo/flathub.flatpakrepo"], on_output
            )
            steps.append(("Flathub Repository", success))

            GLib.idle_add(on_complete, steps)

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
                   on_extra_complete: Callable, on_all_complete: Callable):
        """Run selected configuration extras in background."""
        def _work():
            results = []

            for extra in extras:
                if self._cancel:
                    break

                if extra.key == "aliases":
                    result = self._setup_aliases()
                elif extra.key == "disable_recent":
                    result = self._disable_recent_files()
                elif extra.key == "performance_mode":
                    result = self._set_performance_mode()
                else:
                    result = ("skipped", "Unknown extra")

                results.append((extra.title, result))
                GLib.idle_add(on_extra_complete, extra.title, result)

            # Bolt Launcher Java dependency
            if "bolt-launcher" in installed_packages:
                result = self._install_java()
                results.append(("Java Runtime (Bolt)", result))
                GLib.idle_add(on_extra_complete, "Java Runtime (Bolt)", result)

            GLib.idle_add(on_all_complete, results)

        self._run_in_thread(_work)

    def _setup_aliases(self) -> tuple[str, str]:
        """Set up custom aliases."""
        home = Path.home()
        alias_file = home / "CustomScripts" / "aliases.zsh"

        if alias_file.exists():
            return ("exists", "File already exists")

        alias_file.parent.mkdir(parents=True, exist_ok=True)
        alias_file.write_text(
            "alias update='yay -Syu'\nalias weather='curl wttr.in'\n"
        )

        # Source in shell configs
        for rc_name in [".bashrc", ".zshrc"]:
            rc = home / rc_name
            if rc.exists():
                content = rc.read_text()
                if "aliases.zsh" not in content:
                    with open(rc, "a") as f:
                        f.write(
                            "\n[[ -f ~/CustomScripts/aliases.zsh ]] && "
                            "source ~/CustomScripts/aliases.zsh\n"
                        )

        return ("success", "Aliases configured")

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

