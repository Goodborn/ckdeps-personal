"""Backend installer — runs all shell commands in background threads."""

import socket
import subprocess
import shutil
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import gi
gi.require_version("GLib", "2.0")
from gi.repository import GLib

from .package_data import Package, ExtraConfig
from .distro import is_arch_based, distro_name

# Dependencies that need to be installed alongside certain packages
PACKAGE_DEPENDENCIES = {
    "vm-curator-bin": ["qemu-full", "sdl2"],
}


class Installer:
    """Manages package installation and system configuration in background threads."""

    def __init__(self):
        self._cancel = False
        self.sudo_password = None
        # True while a bootstrap/install/extras run is active — used to
        # guard against quitting mid-operation and leaving the system
        # (e.g. pacman's db lock) in an inconsistent state.
        self.busy = False
        self._keepalive_stop = None
        self._keepalive_thread = None
        self.log_path = self._init_log_file()
        self._log(f"CKDEPS run started — distro: {distro_name() or 'unknown'}, "
                   f"arch_based: {is_arch_based()}")

    def forget_password(self):
        """Drop the sudo password from memory once no further privileged
        work is expected (e.g. once we've reached the summary page)."""
        self.sudo_password = None

    # ─── Sudo Credential Keep-Alive ───────────────────────────────
    #
    # A run can chain many AUR builds and package installs back to back,
    # easily outlasting sudo's default timestamp lifetime (commonly 5-15
    # minutes). Without this, a long run can fail deep into a build with
    # a silent "no TTY to read password" error even though the user
    # already typed it in. Refresh the cached credential periodically
    # for the duration of any privileged run.

    def _start_sudo_keepalive(self):
        if self._keepalive_thread is not None:
            return
        stop_event = threading.Event()
        self._keepalive_stop = stop_event

        def _work():
            while not stop_event.wait(60):
                if not self.sudo_password:
                    continue
                try:
                    proc = subprocess.Popen(
                        ["sudo", "-S", "-v"],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        text=True,
                    )
                    proc.communicate(self.sudo_password + "\n", timeout=15)
                except Exception:
                    pass

        self._keepalive_thread = threading.Thread(target=_work, daemon=True)
        self._keepalive_thread.start()

    def _stop_sudo_keepalive(self):
        if self._keepalive_stop is not None:
            self._keepalive_stop.set()
        self._keepalive_thread = None

    def cancel(self):
        """Request cancellation of current operations."""
        self._cancel = True

    @property
    def was_cancelled(self) -> bool:
        """Whether the most recent run was stopped via cancel(). Callers that
        chain stages (packages -> extras) should check this before starting
        the next stage, since bootstrap/install/run_extras each reset the
        flag for themselves at the start of their own run."""
        return self._cancel

    def reset_cancel(self):
        """Clear a pending cancellation so the next stage can run normally."""
        self._cancel = False

    # ─── Persistent Logging ──────────────────────────────────────
    #
    # A live log is written incrementally to a hidden XDG-state location
    # while a run is in progress, so a crash mid-run is still diagnosable.
    # Once a run finishes cleanly, finalize_log() copies it to a visible
    # folder in the user's home directory for easy access.

    FINAL_LOG_DIR = Path.home() / "ckdeps-logs"

    def _init_log_file(self) -> Optional[Path]:
        """Create a per-run live log file under ~/.local/state."""
        try:
            log_dir = Path.home() / ".local" / "state" / "ckdeps" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            self._prune_old_logs(log_dir)

            path = log_dir / f"ckdeps-{datetime.now():%Y%m%d-%H%M%S}.log"
            path.touch()
            return path
        except Exception:
            return None

    @staticmethod
    def _prune_old_logs(log_dir: Path, keep: int = 10):
        """Keep only the most recent `keep` log files in a directory."""
        try:
            existing = sorted(log_dir.glob("ckdeps-*.log"))
            for old in existing[:-(keep - 1)] if keep > 1 else existing:
                old.unlink(missing_ok=True)
        except Exception:
            pass

    def _log(self, line: str):
        """Best-effort append to the live log file."""
        if not self.log_path:
            return
        try:
            with open(self.log_path, "a") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def finalize_log(self) -> Optional[Path]:
        """Copy the live log to a visible folder in the user's home
        directory (~/ckdeps-logs/) once a run completes. Returns the final
        path, or the hidden live-log path if finalizing fails."""
        if not self.log_path:
            return None
        try:
            self.FINAL_LOG_DIR.mkdir(parents=True, exist_ok=True)
            self._prune_old_logs(self.FINAL_LOG_DIR)
            final_path = self.FINAL_LOG_DIR / self.log_path.name
            shutil.copy2(self.log_path, final_path)
            return final_path
        except Exception:
            return self.log_path

    # ─── Preflight Checks ─────────────────────────────────────────

    def verify_sudo_password(self, password: str, on_result: Callable):
        """Validate a sudo password without running any privileged command.
        Prevents silently blasting through every install step with a wrong
        password and only finding out from a wall of failures."""
        def _work():
            try:
                proc = subprocess.Popen(
                    ["sudo", "-S", "-k", "-v"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                try:
                    proc.communicate(password + "\n", timeout=15)
                    ok = proc.returncode == 0
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.communicate()
                    ok = False
            except Exception:
                ok = False
            GLib.idle_add(on_result, ok)

        self._run_in_thread(_work)

    def check_environment(self, on_result: Callable):
        """Run best-effort environment sanity checks in the background and
        report back a list of (level, message) issues, where level is
        'error' or 'warning'. Nothing here is fatal by itself — the caller
        decides whether to block or let the user proceed."""
        def _work():
            issues = []

            if not is_arch_based():
                issues.append((
                    "error",
                    f"This doesn't look like an Arch-based system (detected: "
                    f"{distro_name() or 'unknown'}). CKDEPS drives pacman/yay "
                    f"directly and may fail or misbehave here."
                ))

            if not self._has_network():
                issues.append((
                    "warning",
                    "No internet connection detected — package installs will "
                    "likely fail."
                ))

            free_gb = self._free_disk_gb("/")
            if free_gb is not None and free_gb < 2:
                issues.append((
                    "warning",
                    f"Low disk space: only {free_gb:.1f} GB free on /."
                ))

            if Path("/var/lib/pacman/db.lck").exists():
                issues.append((
                    "warning",
                    "A pacman lock file exists (/var/lib/pacman/db.lck) — "
                    "another package manager may be running, or a previous "
                    "run crashed without cleaning up."
                ))

            for level, msg in issues:
                self._log(f"[preflight:{level}] {msg}")

            GLib.idle_add(on_result, issues)

        self._run_in_thread(_work)

    def _has_network(self, timeout: float = 3.0) -> bool:
        for host, port in (("archlinux.org", 443), ("1.1.1.1", 443)):
            try:
                socket.create_connection((host, port), timeout=timeout).close()
                return True
            except OSError:
                continue
        return False

    def _free_disk_gb(self, path: str) -> Optional[float]:
        try:
            usage = shutil.disk_usage(path)
            return usage.free / (1024 ** 3)
        except Exception:
            return None

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
                text = line.rstrip()
                output_lines.append(text)
                self._log(text)
                if on_output:
                    GLib.idle_add(on_output, text)
                if self._cancel:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    return False, "Cancelled"

            process.wait()
            return process.returncode == 0, "\n".join(output_lines)

        except FileNotFoundError:
            msg = f"Command not found: {cmd[0]}"
            self._log(msg)
            if on_output:
                GLib.idle_add(on_output, msg)
            return False, msg
        except Exception as e:
            msg = f"Error: {str(e)}"
            self._log(msg)
            if on_output:
                GLib.idle_add(on_output, msg)
            return False, msg

    # ─── Bootstrap ───────────────────────────────────────────────

    def bootstrap_system(self, selected_steps: list[str], on_step: Callable,
                         on_output: Callable, on_complete: Callable):
        """Run selected bootstrap steps in background."""
        self._cancel = False
        self.busy = True
        self._start_sudo_keepalive()

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
                            # Prime the sudo credential right before makepkg
                            # runs — makepkg's own internal "sudo pacman -U"
                            # call has no TTY and no piped password, so it
                            # only succeeds off an already-cached timestamp.
                            self._run_command(["sudo", "-v"], on_output)
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

            self.busy = False
            self._stop_sudo_keepalive()
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
        self._cancel = False
        self.busy = True
        self._start_sudo_keepalive()

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

                # Install dependencies if package was installed successfully
                if success and pkg.name in PACKAGE_DEPENDENCIES:
                    for dep in PACKAGE_DEPENDENCIES[pkg.name]:
                        GLib.idle_add(on_output, f"Installing dependency: {dep}")
                        dep_success, _ = self._run_command(
                            ["sudo", "pacman", "-S", "--needed", "--noconfirm", dep],
                            on_output
                        )
                        if not dep_success:
                            GLib.idle_add(on_output, f"Warning: failed to install dependency {dep}")

            self.busy = False
            self._stop_sudo_keepalive()
            GLib.idle_add(on_all_complete, results)

        self._run_in_thread(_work)

    # ─── Extras ──────────────────────────────────────────────────

    def run_extras(self, extras: list[ExtraConfig], installed_packages: list[str],
                   newly_installed: list[str] = None,
                   on_extra_complete: Callable = None, on_all_complete: Callable = None):
        """Run selected configuration extras in background."""
        if newly_installed is None:
            newly_installed = []
        self._cancel = False
        self.busy = True
        self._start_sudo_keepalive()

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
                elif extra.key == "localsend_ufw":
                    result = self._setup_localsend_ufw()
                else:
                    result = ("skipped", "Unknown extra")

                results.append((extra.title, result))
                GLib.idle_add(on_extra_complete, extra.title, result)

            # Bolt Launcher Java dependency — only if bolt is installed AND java is missing
            if "bolt-launcher" in installed_packages and not self.is_pacman_installed("jre-openjdk"):
                result = self._install_java()
                results.append(("Java Runtime (Bolt)", result))
                GLib.idle_add(on_extra_complete, "Java Runtime (Bolt)", result)

            self.busy = False
            self._stop_sudo_keepalive()
            GLib.idle_add(on_all_complete, results)

        self._run_in_thread(_work)

    def check_extras_status(self, extras: list[ExtraConfig], on_complete: Callable):
        """Check which configuration extras are already applied, so the UI
        can show accurate state instead of blindly re-offering everything
        as if nothing had been done yet."""
        def _work():
            status = {}
            for extra in extras:
                if extra.key == "aliases":
                    status[extra.key] = (Path.home() / "CustomScripts" / "aliases.fish").exists()
                elif extra.key == "fish_config":
                    status[extra.key] = self._fish_config_is_complete()
                elif extra.key == "disable_recent":
                    status[extra.key] = self._is_recent_files_disabled()
                elif extra.key == "performance_mode":
                    status[extra.key] = self._is_performance_mode_active()
                elif extra.key == "localsend_ufw":
                    status[extra.key] = self._ufw_has_localsend_rules()
                else:
                    status[extra.key] = False

            GLib.idle_add(on_complete, status)

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

    def _fish_config_is_complete(self) -> bool:
        """Check whether config.fish already wires up everything the
        fish_config extra would write — checked by substance (does it
        actually init starship/thefuck/atuin/zoxide, source the aliases
        file, and define the duration widget?), not by a literal "CKDEPS"
        marker comment, since a hand-written config with the same content
        should count as already done regardless of who wrote it."""
        cfg = Path.home() / ".config" / "fish" / "config.fish"
        if not cfg.exists():
            return False
        try:
            content = cfg.read_text()
        except Exception:
            return False

        required = (
            "starship init fish",
            "thefuck --alias",
            "atuin init fish",
            "zoxide init fish",
            "CustomScripts/aliases.fish",
            "__cmd_timer_start",
        )
        return all(marker in content for marker in required)

    def _setup_fish_config(self) -> tuple[str, str]:
        """Set up fish config.fish with Starship, TheFuck, Atuin, Zoxide, aliases, and command duration."""
        home = Path.home()
        fish_dir = home / ".config" / "fish"
        fish_config = fish_dir / "config.fish"
        fish_dir.mkdir(parents=True, exist_ok=True)

        if self._fish_config_is_complete():
            return ("exists", "Fish config already has everything this extra provides")

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

    def _is_recent_files_disabled(self) -> bool:
        try:
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.privacy",
                 "remember-recent-files"],
                capture_output=True, text=True, timeout=5
            )
            return "false" in result.stdout
        except Exception:
            return False

    def _disable_recent_files(self) -> tuple[str, str]:
        """Disable GNOME recent files tracking."""
        try:
            if self._is_recent_files_disabled():
                return ("exists", "Already disabled")

            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.privacy",
                 "remember-recent-files", "false"],
                capture_output=True, timeout=5
            )
            return ("success", "Recent files disabled")
        except Exception as e:
            return ("failed", str(e))

    def _is_performance_mode_active(self) -> bool:
        if not shutil.which("powerprofilesctl"):
            return False
        try:
            result = subprocess.run(
                ["powerprofilesctl", "get"], capture_output=True, text=True, timeout=5
            )
            return "performance" in result.stdout.strip().lower()
        except Exception:
            return False

    def _set_performance_mode(self) -> tuple[str, str]:
        """Set power profile to performance."""
        if not shutil.which("powerprofilesctl"):
            return ("failed", "powerprofilesctl not found")

        if self._is_performance_mode_active():
            return ("exists", "Already in performance mode")

        success, _ = self._run_command(["powerprofilesctl", "set", "performance"])
        if success:
            return ("success", "Performance mode enabled")
        return ("failed", "Failed to set performance mode")

    def _ufw_has_localsend_rules(self) -> bool:
        if not shutil.which("ufw"):
            return False
        _, output = self._run_command(["sudo", "ufw", "status", "verbose"])
        return "53317/tcp" in output and "53317/udp" in output

    def _setup_localsend_ufw(self) -> tuple[str, str]:
        """Allow LocalSend (port 53317) through UFW on the local network."""
        if not shutil.which("ufw"):
            return ("skipped", "ufw not installed, not needed")

        subnet = self._detect_lan_subnet()
        if not subnet:
            return ("failed", "Could not detect local network subnet")

        _, output = self._run_command(
            ["sudo", "ufw", "status", "verbose"]
        )

        existing_ok = True
        added = 0
        for proto in ("tcp", "udp"):
            if f"53317/{proto}" in output:
                continue
            success, _ = self._run_command(
                ["sudo", "ufw", "allow", "from", subnet,
                 "to", "any", "port", "53317", "proto", proto]
            )
            if success:
                added += 1
            else:
                existing_ok = False

        if added == 0 and existing_ok:
            return ("exists", "UFW rules already allow LocalSend")
        if existing_ok:
            return ("success", f"UFW allows LocalSend from {subnet}")
        return ("failed", "Failed to add all UFW rules")

    def _detect_lan_subnet(self) -> Optional[str]:
        """Detect the local /24 subnet from the default route."""
        try:
            result = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True, text=True, timeout=5
            )
            parts = result.stdout.split()
            if "via" in parts:
                gateway = parts[parts.index("via") + 1]
                return ".".join(gateway.split(".")[:3]) + ".0/24"
        except Exception:
            pass
        return None

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

    def _pacman_installed_set(self) -> set[str]:
        """All installed pacman package names, queried once instead of
        once per package — `pacman -Qi` per package is a full DB scan
        each time and dominates the packages-page loading spinner."""
        try:
            result = subprocess.run(
                ["pacman", "-Qq"], capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                return set(result.stdout.split())
        except Exception:
            pass
        return set()

    def _flatpak_installed_set(self) -> set[str]:
        """All installed Flatpak app IDs, queried once instead of once
        per Flatpak package."""
        try:
            result = subprocess.run(
                ["flatpak", "list", "--app", "--columns=application"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                return {line.strip() for line in result.stdout.splitlines() if line.strip()}
        except Exception:
            pass
        return set()

    def check_all_status(self, packages: list[Package],
                         on_complete: Callable):
        """Check installation status of all packages in background."""
        def _work():
            pacman_set = self._pacman_installed_set()
            flatpak_set = self._flatpak_installed_set()
            for pkg in packages:
                installed = pkg.name in pacman_set
                if not installed and pkg.flatpak_id:
                    installed = pkg.flatpak_id in flatpak_set
                pkg.installed = installed
            GLib.idle_add(on_complete, packages)

        self._run_in_thread(_work)

