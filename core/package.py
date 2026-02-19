"""
PureOS Package Manager
Handles package installation, removal, and querying.
"""

import json
import os
import time
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Set
from enum import Enum


class PackageStatus(Enum):
    INSTALLED = "installed"
    AVAILABLE = "available"
    NOT_FOUND = "not_found"


@dataclass
class Package:
    name: str
    version: str
    description: str
    size: int
    dependencies: List[str] = field(default_factory=list)
    installed_size: int = 0
    installed_time: Optional[float] = None
    status: PackageStatus = PackageStatus.AVAILABLE
    author: str = "PureOS Team"
    category: str = "misc"

    def to_dict(self) -> Dict:
        data = asdict(self)
        data['status'] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'Package':
        data['status'] = PackageStatus(data.get('status', 'available'))
        return cls(**data)


class PackageDatabase:
    DEFAULT_PACKAGES = [
        Package(
            name="vim",
            version="8.2",
            description="Enhanced text editor",
            size=2048,
            installed_size=4096,
            dependencies=[],
            category="editors"
        ),
        Package(
            name="nano",
            version="6.0",
            description="Simple text editor",
            size=512,
            installed_size=1024,
            dependencies=[],
            category="editors"
        ),
        Package(
            name="curl",
            version="7.88",
            description="HTTP client tool",
            size=1024,
            installed_size=2048,
            dependencies=[],
            category="network"
        ),
        Package(
            name="wget",
            version="1.21",
            description="Network download utility",
            size=1024,
            installed_size=2048,
            dependencies=[],
            category="network"
        ),
        Package(
            name="git",
            version="2.40",
            description="Version control system",
            size=4096,
            installed_size=8192,
            dependencies=["curl"],
            category="devel"
        ),
        Package(
            name="python3",
            version="3.11",
            description="Python interpreter",
            size=8192,
            installed_size=16384,
            dependencies=[],
            category="lang"
        ),
        Package(
            name="node",
            version="20.0",
            description="JavaScript runtime",
            size=16384,
            installed_size=32768,
            dependencies=[],
            category="lang"
        ),
        Package(
            name="gcc",
            version="12.2",
            description="GNU C Compiler",
            size=32768,
            installed_size=65536,
            dependencies=[],
            category="devel"
        ),
        Package(
            name="make",
            version="4.4",
            description="Build automation tool",
            size=1024,
            installed_size=2048,
            dependencies=[],
            category="devel"
        ),
        Package(
            name="bash",
            version="5.2",
            description="Bourne Again Shell",
            size=2048,
            installed_size=4096,
            dependencies=[],
            category="shells"
        ),
        Package(
            name="zsh",
            version="5.9",
            description="Z Shell",
            size=2048,
            installed_size=4096,
            dependencies=[],
            category="shells"
        ),
        Package(
            name="tmux",
            version="3.3",
            description="Terminal multiplexer",
            size=1024,
            installed_size=2048,
            dependencies=[],
            category="terminal"
        ),
        Package(
            name="screen",
            version="4.9",
            description="Terminal multiplexer",
            size=512,
            installed_size=1024,
            dependencies=[],
            category="terminal"
        ),
        Package(
            name="htop",
            version="3.2",
            description="Interactive process viewer",
            size=512,
            installed_size=1024,
            dependencies=[],
            category="system"
        ),
        Package(
            name="tree",
            version="1.8",
            description="Directory tree display",
            size=256,
            installed_size=512,
            dependencies=[],
            category="utils"
        ),
        Package(
            name="jq",
            version="1.6",
            description="JSON processor",
            size=256,
            installed_size=512,
            dependencies=[],
            category="utils"
        ),
        Package(
            name="zip",
            version="3.0",
            description="ZIP archive utility",
            size=512,
            installed_size=1024,
            dependencies=[],
            category="archive"
        ),
        Package(
            name="unzip",
            version="6.0",
            description="ZIP extraction utility",
            size=256,
            installed_size=512,
            dependencies=[],
            category="archive"
        ),
        Package(
            name="tar",
            version="1.34",
            description="Tape archive utility",
            size=1024,
            installed_size=2048,
            dependencies=[],
            category="archive"
        ),
        Package(
            name="gzip",
            version="1.12",
            description="GNU zip compression",
            size=256,
            installed_size=512,
            dependencies=[],
            category="archive"
        ),
        Package(
            name="openssh",
            version="9.0",
            description="SSH client and server",
            size=2048,
            installed_size=4096,
            dependencies=[],
            category="network"
        ),
        Package(
            name="wireshark",
            version="4.0",
            description="Network protocol analyzer",
            size=204800,
            installed_size=409600,
            dependencies=["gtk"],
            category="network"
        ),
        Package(
            name="nginx",
            version="1.23",
            description="Web server",
            size=10240,
            installed_size=20480,
            dependencies=[],
            category="network"
        ),
        Package(
            name="sqlite",
            version="3.40",
            description="SQLite database",
            size=1024,
            installed_size=2048,
            dependencies=[],
            category="database"
        ),
        Package(
            name="redis",
            version="7.0",
            description="In-memory database",
            size=5120,
            installed_size=10240,
            dependencies=[],
            category="database"
        ),
        Package(
            name="iperf3",
            version="3.14",
            description="Network bandwidth measurement tool",
            size=1024,
            installed_size=2048,
            dependencies=[],
            category="network"
        ),
        Package(
            name="netcat",
            version="1.10",
            description="Network utility for reading/writing network connections",
            size=256,
            installed_size=512,
            dependencies=[],
            category="network"
        ),
        Package(
            name="tcpdump",
            version="4.99",
            description="Packet analyzer",
            size=2048,
            installed_size=4096,
            dependencies=[],
            category="network"
        ),
        Package(
            name="mtr",
            version="0.95",
            description="Network diagnostic tool (traceroute + ping)",
            size=512,
            installed_size=1024,
            dependencies=[],
            category="network"
        ),
    ]

    def __init__(self):
        self.available: Dict[str, Package] = {}
        self.installed: Dict[str, Package] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        for pkg in self.DEFAULT_PACKAGES:
            self.available[pkg.name] = pkg

    def get_available(self, name: str) -> Optional[Package]:
        return self.available.get(name)

    def get_installed(self, name: str) -> Optional[Package]:
        return self.installed.get(name)

    def list_available(self) -> List[Package]:
        return list(self.available.values())

    def list_installed(self) -> List[Package]:
        return list(self.installed.values())

    def add_installed(self, package: Package) -> None:
        package.status = PackageStatus.INSTALLED
        package.installed_time = time.time()
        self.installed[package.name] = package

    def remove_installed(self, name: str) -> Optional[Package]:
        return self.installed.pop(name, None)

    def search(self, query: str) -> List[Package]:
        query = query.lower()
        results = []
        for pkg in self.available.values():
            if (query in pkg.name.lower() or 
                query in pkg.description.lower() or
                query in pkg.category.lower()):
                results.append(pkg)
        return results


class PackageManager:
    def __init__(self, filesystem=None):
        self.fs = filesystem
        self.db = PackageDatabase()
        self.cache_dir = "/var/cache/pkg"
        self.lib_dir = "/var/lib/pkg"

    def _ensure_directories(self) -> None:
        if self.fs:
            self.fs.mkdir(self.lib_dir, create_parents=True)
            self.fs.mkdir(self.cache_dir, create_parents=True)

    def install(self, package_name: str) -> tuple[bool, str]:
        pkg = self.db.get_available(package_name)
        if not pkg:
            return False, f"Package '{package_name}' not found in repository"

        if self.db.get_installed(package_name):
            return True, f"Package '{package_name}' is already installed"

        for dep_name in pkg.dependencies:
            dep = self.db.get_installed(dep_name)
            if not dep:
                success, msg = self.install(dep_name)
                if not success:
                    return False, f"Failed to install dependency '{dep_name}': {msg}"

        self.db.add_installed(pkg)
        return True, f"Installed {package_name} ({pkg.version})"

    def remove(self, package_name: str) -> tuple[bool, str]:
        installed = self.db.get_installed(package_name)
        if not installed:
            return False, f"Package '{package_name}' is not installed"

        for name, pkg in self.db.installed.items():
            if package_name in pkg.dependencies:
                return False, f"Package '{package_name}' is required by '{name}'"

        self.db.remove_installed(package_name)
        return True, f"Removed {package_name}"

    def list_installed(self) -> List[Package]:
        return self.db.list_installed()

    def list_available(self) -> List[Package]:
        return self.db.list_available()

    def search(self, query: str) -> List[Package]:
        return self.db.search(query)

    def info(self, package_name: str) -> Optional[Package]:
        return (self.db.get_installed(package_name) or 
                self.db.get_available(package_name))

    def is_installed(self, package_name: str) -> bool:
        return self.db.get_installed(package_name) is not None

    def get_dependencies(self, package_name: str) -> List[str]:
        pkg = self.db.get_available(package_name)
        if not pkg:
            return []
        return pkg.dependencies

    def total_installed_size(self) -> int:
        total = 0
        for pkg in self.db.installed.values():
            total += pkg.installed_size
        return total
