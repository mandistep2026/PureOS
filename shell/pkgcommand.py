"""
PureOS Package Manager Shell Command
"""

from typing import List
from shell.shell import ShellCommand


class PkgCommand(ShellCommand):
    def __init__(self, package_manager=None):
        super().__init__("pkg", "Package manager")
        self.pm = package_manager

    def execute(self, args: List[str], shell) -> int:
        if not self.pm:
            self.pm = shell.package_manager

        if not self.pm:
            try:
                from core.package import PackageManager
                self.pm = PackageManager(shell.fs)
            except Exception as e:
                shell.print(f"Error: Package manager not available: {e}")
                return 1

        if not args:
            return self.show_help(shell)

        subcommand = args[0]
        subargs = args[1:]

        if subcommand in ("install", "add"):
            return self.install(subargs, shell)
        elif subcommand in ("remove", "delete", "uninstall", "rm"):
            return self.remove(subargs, shell)
        elif subcommand in ("list", "ls"):
            return self.list_packages(subargs, shell)
        elif subcommand in ("search", "find"):
            return self.search(subargs, shell)
        elif subcommand in ("info", "show"):
            return self.info(subargs, shell)
        elif subcommand in ("update", "refresh"):
            return self.update(shell)
        elif subcommand in ("depends", "deps"):
            return self.depends(subargs, shell)
        elif subcommand in ("-h", "--help", "help"):
            return self.show_help(shell)
        else:
            shell.print(f"Unknown subcommand: {subcommand}")
            return self.show_help(shell)

    def install(self, args: List[str], shell) -> int:
        if not args:
            shell.print("Usage: pkg install <package>")
            return 1

        package_name = args[0]
        shell.print(f"Installing {package_name}...")

        success, message = self.pm.install(package_name)
        shell.print(message)

        return 0 if success else 1

    def remove(self, args: List[str], shell) -> int:
        if not args:
            shell.print("Usage: pkg remove <package>")
            return 1

        package_name = args[0]
        shell.print(f"Removing {package_name}...")

        success, message = self.pm.remove(package_name)
        shell.print(message)

        return 0 if success else 1

    def list_packages(self, args: List[str], shell) -> int:
        all_packages = "-a" in args or "--all" in args

        if all_packages:
            packages = self.pm.list_available()
            shell.print("Available packages:")
            shell.print("-" * 60)
            for pkg in packages:
                status = "[installed]" if self.pm.is_installed(pkg.name) else ""
                shell.print(f"  {pkg.name:15} {pkg.version:8} {pkg.description[:30]} {status}")
        else:
            packages = self.pm.list_installed()
            if not packages:
                shell.print("No packages installed")
                return 0
            shell.print("Installed packages:")
            shell.print("-" * 60)
            total_size = 0
            for pkg in packages:
                shell.print(f"  {pkg.name:15} {pkg.version:8} {pkg.description}")
                total_size += pkg.installed_size
            shell.print("-" * 60)
            shell.print(f"Total installed size: {self._format_size(total_size)}")

        return 0

    def search(self, args: List[str], shell) -> int:
        if not args:
            shell.print("Usage: pkg search <query>")
            return 1

        query = args[0]
        results = self.pm.search(query)

        if not results:
            shell.print(f"No packages found matching '{query}'")
            return 1

        shell.print(f"Packages matching '{query}':")
        shell.print("-" * 60)
        for pkg in results:
            status = "[installed]" if self.pm.is_installed(pkg.name) else ""
            shell.print(f"  {pkg.name:15} {pkg.version:8} {pkg.description} {status}")

        return 0

    def info(self, args: List[str], shell) -> int:
        if not args:
            shell.print("Usage: pkg info <package>")
            return 1

        package_name = args[0]
        pkg = self.pm.info(package_name)

        if not pkg:
            shell.print(f"Package '{package_name}' not found")
            return 1

        installed = self.pm.is_installed(package_name)
        shell.print(f"Package: {pkg.name}")
        shell.print(f"Version: {pkg.version}")
        shell.print(f"Description: {pkg.description}")
        shell.print(f"Category: {pkg.category}")
        shell.print(f"Author: {pkg.author}")
        shell.print(f"Size: {self._format_size(pkg.size)}")
        shell.print(f"Installed Size: {self._format_size(pkg.installed_size)}")
        shell.print(f"Status: {'Installed' if installed else 'Available'}")
        
        if pkg.dependencies:
            shell.print(f"Dependencies: {', '.join(pkg.dependencies)}")
        else:
            shell.print("Dependencies: none")

        if installed and pkg.installed_time:
            import time
            installed_date = time.strftime("%Y-%m-%d %H:%M:%S", 
                                          time.localtime(pkg.installed_time))
            shell.print(f"Installed: {installed_date}")

        return 0

    def update(self, shell) -> int:
        shell.print("Updating package database...")
        shell.print("Package database is up to date.")
        return 0

    def depends(self, args: List[str], shell) -> int:
        if not args:
            shell.print("Usage: pkg depends <package>")
            return 1

        package_name = args[0]
        deps = self.pm.get_dependencies(package_name)

        if not deps:
            shell.print(f"Package '{package_name}' has no dependencies")
            return 0

        shell.print(f"Dependencies for {package_name}:")
        for dep in deps:
            status = "[installed]" if self.pm.is_installed(dep) else "[not installed]"
            shell.print(f"  {dep} {status}")

        return 0

    def show_help(self, shell) -> int:
        shell.print("Package manager commands:")
        shell.print("  pkg install <package>   Install a package")
        shell.print("  pkg remove <package>    Remove a package")
        shell.print("  pkg list                List installed packages")
        shell.print("  pkg list -a             List all available packages")
        shell.print("  pkg search <query>      Search for packages")
        shell.print("  pkg info <package>      Show package information")
        shell.print("  pkg update              Update package database")
        shell.print("  pkg depends <package>   Show package dependencies")
        shell.print("  pkg help                Show this help")
        return 0

    def _format_size(self, size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size}{unit}"
            size //= 1024
        return f"{size}TB"
