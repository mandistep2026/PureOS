"""
PureOS Virtual File System
In-memory filesystem using only Python standard library.
"""

import os
import time
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union
from pathlib import Path
from enum import Enum


class FileType(Enum):
    REGULAR = "regular"
    DIRECTORY = "directory"
    SYMLINK = "symlink"


@dataclass
class Inode:
    """Represents a file or directory inode."""
    name: str
    type: FileType
    parent: Optional[str] = None
    content: Union[bytes, Dict[str, str]] = field(default_factory=bytes)
    created: float = field(default_factory=time.time)
    modified: float = field(default_factory=time.time)
    size: int = 0
    permissions: str = "rw-r--r--"
    owner: str = "root"
    group: str = "root"
    target: Optional[str] = None  # For symlinks


class FileSystem:
    """Virtual in-memory file system."""
    
    def __init__(self):
        self.inodes: Dict[str, Inode] = {}
        self.current_directory = "/"
        self._initialize_root()
    
    def _initialize_root(self) -> None:
        """Create root directory."""
        root = Inode(
            name="/",
            type=FileType.DIRECTORY,
            parent=None,
            content={}
        )
        self.inodes["/"] = root
        
        # Create standard directories
        self.mkdir("/bin")
        self.mkdir("/etc")
        self.mkdir("/home")
        self.mkdir("/tmp")
        self.mkdir("/var")
        self.mkdir("/proc")
        self.mkdir("/proc/net")
        self.mkdir("/dev")
        self.mkdir("/root")
    
    def _normalize_path(self, path: str) -> str:
        """Normalize a path to absolute form."""
        if not path.startswith("/"):
            path = os.path.join(self.current_directory, path)
        
        # Handle . and ..
        parts = path.split("/")
        normalized = []
        for part in parts:
            if part == "" or part == ".":
                continue
            elif part == "..":
                if normalized:
                    normalized.pop()
            else:
                normalized.append(part)
        
        return "/" + "/".join(normalized)
    
    def _get_parent(self, path: str) -> Optional[str]:
        """Get parent directory of a path."""
        if path == "/":
            return None
        parent = os.path.dirname(path)
        return parent if parent else "/"
    
    def _add_to_parent(self, path: str, name: str) -> bool:
        """Add entry to parent directory."""
        parent_path = self._get_parent(path)
        if parent_path is None or parent_path not in self.inodes:
            return False
        
        parent = self.inodes[parent_path]
        if parent.type != FileType.DIRECTORY:
            return False
        
        if isinstance(parent.content, dict):
            parent.content[name] = path
            parent.modified = time.time()
            return True
        return False
    
    def _remove_from_parent(self, path: str, name: str) -> bool:
        """Remove entry from parent directory."""
        parent_path = self._get_parent(path)
        if parent_path is None or parent_path not in self.inodes:
            return False
        
        parent = self.inodes[parent_path]
        if parent.type != FileType.DIRECTORY:
            return False
        
        if isinstance(parent.content, dict) and name in parent.content:
            del parent.content[name]
            parent.modified = time.time()
            return True
        return False
    
    def mkdir(self, path: str, parents: bool = False) -> bool:
        """Create a directory."""
        path = self._normalize_path(path)
        
        if path in self.inodes:
            return False
        
        parent_path = self._get_parent(path)
        if parent_path is None:
            return False
        if parent_path not in self.inodes:
            if not parents:
                return False
            # Create parent directories recursively
            if not self.mkdir(parent_path, parents=True):
                return False
        
        name = os.path.basename(path) or "/"
        inode = Inode(
            name=name,
            type=FileType.DIRECTORY,
            parent=parent_path,
            content={}
        )
        
        self.inodes[path] = inode
        return self._add_to_parent(path, name)
    
    def rmdir(self, path: str) -> bool:
        """Remove a directory."""
        path = self._normalize_path(path)
        
        if path not in self.inodes:
            return False
        
        inode = self.inodes[path]
        if inode.type != FileType.DIRECTORY:
            return False
        
        if inode.content:
            return False  # Directory not empty
        
        name = os.path.basename(path) or "/"
        self._remove_from_parent(path, name)
        del self.inodes[path]
        return True

    def remove_tree(self, path: str) -> bool:
        """Recursively remove a file or directory tree."""
        path = self._normalize_path(path)

        if path == "/" or path not in self.inodes:
            return False

        inode = self.inodes[path]

        if inode.type == FileType.DIRECTORY:
            entries = inode.content if isinstance(inode.content, dict) else {}
            child_paths = list(entries.values())
            for child_path in child_paths:
                if not self.remove_tree(child_path):
                    return False

        name = os.path.basename(path) or "/"
        self._remove_from_parent(path, name)
        del self.inodes[path]
        return True
    
    def create_file(self, path: str, content: bytes = b"") -> bool:
        """Create a regular file."""
        path = self._normalize_path(path)
        
        if path in self.inodes:
            return False
        
        parent_path = self._get_parent(path)
        if parent_path not in self.inodes:
            return False
        
        name = os.path.basename(path)
        inode = Inode(
            name=name,
            type=FileType.REGULAR,
            parent=parent_path,
            content=content,
            size=len(content)
        )
        
        self.inodes[path] = inode
        return self._add_to_parent(path, name)
    
    def write_file(self, path: str, content: bytes) -> bool:
        """Write content to a file."""
        path = self._normalize_path(path)
        
        if path not in self.inodes:
            return self.create_file(path, content)
        
        inode = self.inodes[path]
        if inode.type != FileType.REGULAR:
            return False
        
        inode.content = content
        inode.size = len(content)
        inode.modified = time.time()
        return True
    
    def read_file(self, path: str) -> Optional[bytes]:
        """Read content from a file."""
        path = self._normalize_path(path)
        
        if path not in self.inodes:
            return None
        
        inode = self.inodes[path]
        if inode.type == FileType.SYMLINK:
            # Follow symlink
            return self.read_file(inode.target) if inode.target else None
        
        if inode.type != FileType.REGULAR:
            return None
        
        content = inode.content
        if isinstance(content, bytes):
            return content
        return None
    
    def delete_file(self, path: str) -> bool:
        """Delete a file."""
        path = self._normalize_path(path)
        
        if path not in self.inodes:
            return False
        
        inode = self.inodes[path]
        if inode.type != FileType.REGULAR:
            return False
        
        name = os.path.basename(path)
        self._remove_from_parent(path, name)
        del self.inodes[path]
        return True
    
    def list_directory(self, path: Optional[str] = None) -> Optional[List[Inode]]:
        """List contents of a directory."""
        if path is None:
            path = self.current_directory
        
        path = self._normalize_path(path)
        
        if path not in self.inodes:
            return None
        
        inode = self.inodes[path]
        if inode.type != FileType.DIRECTORY:
            return None
        
        dir_content = inode.content
        if isinstance(dir_content, dict):
            return [self.inodes[p] for p in dir_content.values() if p in self.inodes]
        return []
    
    def change_directory(self, path: str) -> bool:
        """Change current directory."""
        path = self._normalize_path(path)
        
        if path not in self.inodes:
            return False
        
        inode = self.inodes[path]
        if inode.type != FileType.DIRECTORY:
            return False
        
        self.current_directory = path
        return True
    
    def get_current_directory(self) -> str:
        """Get current working directory."""
        return self.current_directory
    
    def exists(self, path: str) -> bool:
        """Check if path exists."""
        path = self._normalize_path(path)
        return path in self.inodes
    
    def is_directory(self, path: str) -> bool:
        """Check if path is a directory."""
        path = self._normalize_path(path)
        if path not in self.inodes:
            return False
        return self.inodes[path].type == FileType.DIRECTORY
    
    def is_file(self, path: str) -> bool:
        """Check if path is a regular file."""
        path = self._normalize_path(path)
        if path not in self.inodes:
            return False
        return self.inodes[path].type == FileType.REGULAR
    
    def get_inode(self, path: str) -> Optional[Inode]:
        """Get inode information."""
        path = self._normalize_path(path)
        return self.inodes.get(path)
    
    def stat(self, path: str) -> Optional[Dict]:
        """Get file/directory statistics."""
        path = self._normalize_path(path)
        inode = self.inodes.get(path)
        
        if not inode:
            return None
        
        return {
            "name": inode.name,
            "type": inode.type.value,
            "size": inode.size,
            "created": inode.created,
            "modified": inode.modified,
            "permissions": inode.permissions,
            "owner": inode.owner,
            "group": inode.group,
        }
    
    def chmod(self, path: str, permissions: str) -> bool:
        """Change file permissions."""
        path = self._normalize_path(path)
        if path not in self.inodes:
            return False
        
        self.inodes[path].permissions = permissions
        self.inodes[path].modified = time.time()
        return True
    
    def chown(self, path: str, owner: str, group: Optional[str] = None) -> bool:
        """Change file owner and group."""
        path = self._normalize_path(path)
        if path not in self.inodes:
            return False
        
        self.inodes[path].owner = owner
        if group:
            self.inodes[path].group = group
        self.inodes[path].modified = time.time()
        return True
    
    def get_size(self) -> int:
        """Get total filesystem size in bytes."""
        total = 0
        for inode in self.inodes.values():
            if inode.type == FileType.REGULAR:
                total += inode.size
            total += 256  # Metadata overhead per inode
        return total
    
    def export_to_json(self) -> str:
        """Export filesystem to JSON."""
        data = {}
        for path, inode in self.inodes.items():
            if inode.type == FileType.DIRECTORY and isinstance(inode.content, dict):
                content_data: Union[Dict[str, str], str] = inode.content
            elif isinstance(inode.content, bytes):
                content_data = inode.content.decode('utf-8', errors='replace')
            else:
                content_data = str(inode.content)
            
            data[path] = {
                "name": inode.name,
                "type": inode.type.value,
                "parent": inode.parent,
                "content": content_data,
                "created": inode.created,
                "modified": inode.modified,
                "size": inode.size,
                "permissions": inode.permissions,
                "owner": inode.owner,
                "group": inode.group,
            }
        return json.dumps(data, indent=2)
    
    def import_from_json(self, json_data: str) -> bool:
        """Import filesystem from JSON."""
        try:
            data = json.loads(json_data)
            self.inodes.clear()
            
            for path, info in data.items():
                inode = Inode(
                    name=info["name"],
                    type=FileType(info["type"]),
                    parent=info["parent"],
                    content=info["content"] if info["type"] == "directory" 
                            else info["content"].encode('utf-8'),
                    created=info["created"],
                    modified=info["modified"],
                    size=info["size"],
                    permissions=info["permissions"],
                    owner=info["owner"],
                    group=info["group"],
                )
                self.inodes[path] = inode
            
            return True
        except (json.JSONDecodeError, KeyError):
            return False
