"""
PureOS User Management
Multi-user support with user accounts and groups.
Uses only Python standard library.
"""

import hashlib
import secrets
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class User:
    """Represents a user account."""
    username: str
    uid: int
    gid: int
    home_dir: str
    shell: str
    password_hash: str = ""
    salt: str = ""
    is_active: bool = True
    created: float = field(default_factory=time.time)
    last_login: Optional[float] = None
    
    def to_passwd_line(self) -> str:
        """Convert to /etc/passwd format."""
        return f"{self.username}:x:{self.uid}:{self.gid}:{self.home_dir}:{self.shell}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "username": self.username,
            "uid": self.uid,
            "gid": self.gid,
            "home_dir": self.home_dir,
            "shell": self.shell,
            "password_hash": self.password_hash,
            "salt": self.salt,
            "is_active": self.is_active,
            "created": self.created,
            "last_login": self.last_login,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Create User from dictionary."""
        return cls(**data)


@dataclass
class Group:
    """Represents a user group."""
    name: str
    gid: int
    members: List[str] = field(default_factory=list)
    
    def to_group_line(self) -> str:
        """Convert to /etc/group format."""
        members_str = ",".join(self.members)
        return f"{self.name}:x:{self.gid}:{members_str}"


class UserManager:
    """Manages user accounts and authentication."""
    
    def __init__(self, filesystem):
        self.fs = filesystem
        self.users: Dict[str, User] = {}
        self.groups: Dict[str, Group] = {}
        self.next_uid = 1000
        self.next_gid = 1000
        
        # Initialize with root user
        self._initialize_system()
    
    def _refresh_etc_files(self) -> None:
        """Write current user/group data to /etc/passwd and /etc/group."""
        try:
            passwd_content = self.export_passwd() + "\n"
            self.fs.write_file("/etc/passwd", passwd_content.encode())
            group_content = self.export_group() + "\n"
            self.fs.write_file("/etc/group", group_content.encode())
        except Exception:
            pass

    def _initialize_system(self) -> None:
        """Initialize system with default users and groups."""
        # Create root user (UID 0)
        root = User(
            username="root",
            uid=0,
            gid=0,
            home_dir="/root",
            shell="/bin/sh",
            password_hash="",
            salt=""
        )
        self.users["root"] = root
        
        # Create root group (GID 0)
        root_group = Group(name="root", gid=0, members=["root"])
        self.groups["root"] = root_group
        
        # Create standard groups
        self.groups["users"] = Group(name="users", gid=100)
        self.groups["sudo"]  = Group(name="sudo",  gid=27,  members=["root"])
        self.groups["disk"]  = Group(name="disk",  gid=6,   members=["root"])
        self.groups["wheel"] = Group(name="wheel", gid=10,  members=["root"])
        
        # Create default regular user 'alice'
        self._create_default_user("alice", "password123", "/home/alice")
        # Refresh system files to reflect all users/groups
        self._refresh_etc_files()
    
    def _create_default_user(self, username: str, password: str, home_dir: str) -> None:
        """Create a default user with home directory."""
        # Generate password hash
        salt = secrets.token_hex(16)
        password_hash = self._hash_password(password, salt)
        
        # Create user
        user = User(
            username=username,
            uid=self.next_uid,
            gid=self.next_uid,  # Primary group same as UID
            home_dir=home_dir,
            shell="/bin/sh",
            password_hash=password_hash,
            salt=salt
        )
        self.users[username] = user
        self.next_uid += 1
        
        # Create user's primary group
        group = Group(name=username, gid=user.gid, members=[username])
        self.groups[username] = group
        self.next_gid += 1
        
        # Add to users group
        if "users" in self.groups:
            self.groups["users"].members.append(username)
        
        # Create home directory
        self.fs.mkdir(home_dir, parents=True)
        self.fs.chown(home_dir, username, username)
    
    def _hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt using SHA-256."""
        # Combine password and salt, hash multiple times for security
        hash_value = password + salt
        for _ in range(1000):  # 1000 iterations
            hash_value = hashlib.sha256(hash_value.encode()).hexdigest()
        return hash_value
    
    def verify_password(self, username: str, password: str) -> bool:
        """Verify password for user."""
        user = self.users.get(username)
        if not user or not user.is_active:
            return False
        
        if not user.password_hash or not user.salt:
            # No password set - only allow if password is empty
            return password == ""
        
        computed_hash = self._hash_password(password, user.salt)
        return computed_hash == user.password_hash
    
    def create_user(self, username: str, password: str = "", 
                   home_dir: Optional[str] = None, 
                   shell: str = "/bin/sh",
                   create_home: bool = True) -> Tuple[bool, str]:
        """Create a new user account.
        
        Returns:
            (success: bool, message: str)
        """
        # Validate username
        if not username or not username.isalnum() or username[0].isdigit():
            return False, "Invalid username (must be alphanumeric, not starting with digit)"
        
        if username in self.users:
            return False, f"User '{username}' already exists"
        
        # Set default home directory
        if home_dir is None:
            home_dir = f"/home/{username}"
        
        # Generate password hash
        salt = secrets.token_hex(16)
        password_hash = self._hash_password(password, salt) if password else ""
        
        # Create user
        user = User(
            username=username,
            uid=self.next_uid,
            gid=self.next_uid,
            home_dir=home_dir,
            shell=shell,
            password_hash=password_hash,
            salt=salt if password else ""
        )
        self.users[username] = user
        self.next_uid += 1
        
        # Create primary group
        group = Group(name=username, gid=user.gid, members=[username])
        self.groups[username] = group
        self.next_gid += 1
        
        # Add to users group
        if "users" in self.groups:
            self.groups["users"].members.append(username)
        
        # Create home directory if requested
        if create_home:
            if not self.fs.exists(home_dir):
                self.fs.mkdir(home_dir, parents=True)
                self.fs.chown(home_dir, username, username)
        
        return True, f"User '{username}' created successfully"
    
    def delete_user(self, username: str, remove_home: bool = False) -> Tuple[bool, str]:
        """Delete a user account.
        
        Returns:
            (success: bool, message: str)
        """
        if username not in self.users:
            return False, f"User '{username}' does not exist"
        
        if username == "root":
            return False, "Cannot delete root user"
        
        user = self.users[username]
        
        # Remove from groups
        for group in self.groups.values():
            if username in group.members:
                group.members.remove(username)
        
        # Delete primary group
        if username in self.groups:
            del self.groups[username]
        
        # Remove home directory if requested
        if remove_home and self.fs.exists(user.home_dir):
            # Note: In a real implementation, we'd need recursive rmdir
            # For now, just mark as deletion requested
            pass
        
        # Delete user
        del self.users[username]
        
        return True, f"User '{username}' deleted successfully"
    
    def change_password(self, username: str, new_password: str) -> Tuple[bool, str]:
        """Change user's password."""
        if username not in self.users:
            return False, f"User '{username}' does not exist"
        
        user = self.users[username]
        
        # Generate new salt and hash
        salt = secrets.token_hex(16)
        password_hash = self._hash_password(new_password, salt)
        
        user.password_hash = password_hash
        user.salt = salt
        
        return True, "Password updated successfully"
    
    def get_user(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self.users.get(username)
    
    def get_user_by_uid(self, uid: int) -> Optional[User]:
        """Get user by UID."""
        for user in self.users.values():
            if user.uid == uid:
                return user
        return None
    
    def list_users(self) -> List[User]:
        """List all users."""
        return list(self.users.values())
    
    def user_exists(self, username: str) -> bool:
        """Check if user exists."""
        return username in self.users
    
    def get_group(self, name: str) -> Optional[Group]:
        """Get group by name."""
        return self.groups.get(name)
    
    def get_group_by_gid(self, gid: int) -> Optional[Group]:
        """Get group by GID."""
        for group in self.groups.values():
            if group.gid == gid:
                return group
        return None
    
    def list_groups(self) -> List[Group]:
        """List all groups."""
        return list(self.groups.values())
    
    def is_user_in_group(self, username: str, groupname: str) -> bool:
        """Check if user is member of group."""
        group = self.groups.get(groupname)
        if not group:
            return False
        return username in group.members
    
    def get_user_groups(self, username: str) -> List[str]:
        """Get list of groups user belongs to."""
        groups = []
        for group in self.groups.values():
            if username in group.members:
                groups.append(group.name)
        return groups
    
    def export_passwd(self) -> str:
        """Export users to /etc/passwd format."""
        lines = []
        for user in sorted(self.users.values(), key=lambda u: u.uid):
            lines.append(user.to_passwd_line())
        return "\n".join(lines)
    
    def export_group(self) -> str:
        """Export groups to /etc/group format."""
        lines = []
        for group in sorted(self.groups.values(), key=lambda g: g.gid):
            lines.append(group.to_group_line())
        return "\n".join(lines)
    
    def to_dict(self) -> dict:
        """Export all data to dictionary."""
        return {
            "users": {name: user.to_dict() for name, user in self.users.items()},
            "groups": {name: {"name": g.name, "gid": g.gid, "members": g.members} 
                      for name, g in self.groups.items()},
            "next_uid": self.next_uid,
            "next_gid": self.next_gid,
        }
    
    def from_dict(self, data: dict) -> None:
        """Import data from dictionary."""
        # Import users
        self.users.clear()
        for name, user_data in data.get("users", {}).items():
            self.users[name] = User.from_dict(user_data)
        
        # Import groups
        self.groups.clear()
        for name, group_data in data.get("groups", {}).items():
            self.groups[name] = Group(
                name=group_data["name"],
                gid=group_data["gid"],
                members=group_data.get("members", [])
            )
        
        # Import counters
        self.next_uid = data.get("next_uid", 1000)
        self.next_gid = data.get("next_gid", 1000)
