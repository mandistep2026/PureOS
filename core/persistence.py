"""
PureOS Persistence Module
Save and load system state to/from disk.
Uses JSON for human-readable storage.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class PersistenceManager:
    """Manages saving and loading PureOS state."""
    
    def __init__(self, state_dir: Optional[str] = None):
        """Initialize persistence manager.
        
        Args:
            state_dir: Directory to store state files. Defaults to ~/.pureos
        """
        if state_dir is None:
            state_dir = os.path.expanduser("~/.pureos")
        
        self.state_dir = Path(state_dir)
        self.state_file = self.state_dir / "state.json"
        self.ensure_state_dir()
    
    def ensure_state_dir(self) -> None:
        """Create state directory if it doesn't exist."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
    
    def save_state(self, filesystem, shell, kernel) -> bool:
        """Save complete system state to disk.
        
        Args:
            filesystem: FileSystem instance
            shell: Shell instance
            kernel: Kernel instance
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Collect DNS resolver config from shell's network manager
            dns_config = {}
            nm = getattr(shell, 'network_manager', None) if shell else None
            if nm is not None:
                rc = nm.get_resolver_config()
                dns_config = {
                    "nameservers": rc.nameservers,
                    "search": rc.search,
                }

            state = {
                "version": "1.0",
                "filesystem": self._serialize_filesystem(filesystem),
                "environment": shell.environment if shell else {},
                "aliases": getattr(shell, 'aliases', {}) if shell else {},
                "history": getattr(shell, 'history', []) if shell else [],
                "current_directory": filesystem.get_current_directory() if filesystem else "/",
                "dns_config": dns_config,
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving state: {e}")
            return False
    
    def load_state(self, filesystem, shell, kernel) -> bool:
        """Load system state from disk.
        
        Args:
            filesystem: FileSystem instance
            shell: Shell instance
            kernel: Kernel instance
        
        Returns:
            True if successful, False otherwise
        """
        if not self.state_file.exists():
            return False
        
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            # Restore filesystem
            if filesystem and "filesystem" in state:
                self._deserialize_filesystem(filesystem, state["filesystem"])
            
            # Restore environment
            if shell and "environment" in state:
                shell.environment.update(state["environment"])

            # Restore aliases
            if shell and "aliases" in state:
                shell.aliases = state["aliases"]
            
            # Restore history
            if shell and "history" in state:
                shell.history = state["history"]
                shell.history_position = len(state["history"])
            
            # Restore current directory
            if filesystem and "current_directory" in state:
                filesystem.change_directory(state["current_directory"])

            # Restore DNS resolver config
            dns_cfg = state.get("dns_config")
            if dns_cfg and shell:
                nm = getattr(shell, 'network_manager', None)
                if nm is not None:
                    from core.network import ResolverConfig
                    rc = ResolverConfig(
                        nameservers=dns_cfg.get("nameservers", ["8.8.8.8", "8.8.4.4"]),
                        search=dns_cfg.get("search", []),
                    )
                    nm.set_resolver_config(rc)
                    # Sync /etc/resolv.conf with restored config
                    if filesystem:
                        filesystem.write_file(
                            "/etc/resolv.conf",
                            rc.to_resolv_conf().encode("utf-8"),
                        )

            return True
        except Exception as e:
            print(f"Error loading state: {e}")
            return False
    
    def _serialize_filesystem(self, filesystem) -> Dict[str, Any]:
        """Serialize filesystem to dictionary."""
        data = {
            "inodes": {},
            "current_directory": filesystem.get_current_directory()
        }
        
        for path, inode in filesystem.inodes.items():
            from core.filesystem import FileType
            
            inode_data = {
                "name": inode.name,
                "type": inode.type.value,
                "parent": inode.parent,
                "created": inode.created,
                "modified": inode.modified,
                "size": inode.size,
                "permissions": inode.permissions,
                "owner": inode.owner,
                "group": inode.group,
            }
            
            # Handle content based on type
            if inode.type == FileType.DIRECTORY and isinstance(inode.content, dict):
                inode_data["content"] = inode.content
            elif isinstance(inode.content, bytes):
                # Store binary content as base64
                import base64
                inode_data["content"] = base64.b64encode(inode.content).decode('ascii')
                inode_data["content_encoding"] = "base64"
            else:
                inode_data["content"] = str(inode.content)
            
            data["inodes"][path] = inode_data
        
        return data
    
    def _deserialize_filesystem(self, filesystem, data: Dict[str, Any]) -> None:
        """Deserialize filesystem from dictionary."""
        from core.filesystem import Inode, FileType
        
        # Clear existing filesystem
        filesystem.inodes.clear()
        
        # Restore inodes
        for path, inode_data in data.get("inodes", {}).items():
            file_type = FileType(inode_data["type"])
            
            # Handle content based on type and encoding
            if file_type == FileType.DIRECTORY:
                content = inode_data.get("content", {})
            elif inode_data.get("content_encoding") == "base64":
                import base64
                content = base64.b64decode(inode_data["content"])
            elif isinstance(inode_data.get("content"), str):
                content = inode_data["content"].encode('utf-8')
            else:
                content = b""
            
            inode = Inode(
                name=inode_data["name"],
                type=file_type,
                parent=inode_data.get("parent"),
                content=content,
                created=inode_data.get("created", 0),
                modified=inode_data.get("modified", 0),
                size=inode_data.get("size", 0),
                permissions=inode_data.get("permissions", "rw-r--r--"),
                owner=inode_data.get("owner", "root"),
                group=inode_data.get("group", "root"),
            )
            
            filesystem.inodes[path] = inode
        
        # Restore current directory
        if "current_directory" in data:
            filesystem.current_directory = data["current_directory"]
    
    def state_exists(self) -> bool:
        """Check if a saved state exists."""
        return self.state_file.exists()
    
    def get_state_info(self) -> Optional[Dict[str, Any]]:
        """Get information about saved state without loading it."""
        if not self.state_file.exists():
            return None
        
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            # Count files and directories
            inodes = state.get("filesystem", {}).get("inodes", {})
            files = sum(1 for i in inodes.values() if i.get("type") == "regular")
            dirs = sum(1 for i in inodes.values() if i.get("type") == "directory")
            
            return {
                "version": state.get("version", "unknown"),
                "files": files,
                "directories": dirs,
                "total_items": len(inodes),
                "current_directory": state.get("current_directory", "/"),
                "history_count": len(state.get("history", [])),
            }
        except Exception:
            return None
    
    def delete_state(self) -> bool:
        """Delete saved state file."""
        try:
            if self.state_file.exists():
                self.state_file.unlink()
            return True
        except Exception as e:
            print(f"Error deleting state: {e}")
            return False
