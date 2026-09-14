"""Distro detection — reads /etc/os-release to identify the current Linux distribution."""

import os
from functools import lru_cache


@lru_cache(maxsize=1)
def _read_os_release() -> dict:
    """Parse /etc/os-release into a dict."""
    info = {}
    paths = ["/etc/os-release", "/usr/lib/os-release"]
    for path in paths:
        if os.path.isfile(path):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if "=" in line:
                        key, _, value = line.partition("=")
                        info[key] = value.strip('"')
            break
    return info


@lru_cache(maxsize=1)
def distro_id() -> str:
    """Return the distro ID (e.g. 'cachyos', 'manjaro', 'endeavouros', 'arch')."""
    return _read_os_release().get("ID", "").lower()


@lru_cache(maxsize=1)
def distro_name() -> str:
    """Return the human-readable distro name (e.g. 'CachyOS', 'Manjaro')."""
    return _read_os_release().get("PRETTY_NAME", distro_id().title())


@lru_cache(maxsize=1)
def distro_like() -> str:
    """Return the ID_LIKE field (e.g. 'arch', 'archlinux')."""
    return _read_os_release().get("ID_LIKE", "").lower()


@lru_cache(maxsize=1)
def is_arch_based() -> bool:
    """Check if the distro is Arch-based."""
    did = distro_id()
    dlike = distro_like()
    return did in ("arch", "cachyos", "manjaro", "endeavouros", "garuda", "artix", "arco") or "arch" in dlike


@lru_cache(maxsize=1)
def friendly_name() -> str:
    """Return a short, user-friendly distro name for UI display."""
    did = distro_id()
    name_map = {
        "cachyos": "CachyOS",
        "manjaro": "Manjaro",
        "endeavouros": "EndeavourOS",
        "garuda": "Garuda Linux",
        "arch": "Arch Linux",
        "arco": "ArcoLinux",
        "artix": "Artix Linux",
    }
    return name_map.get(did, distro_name())
