"""
PureOS Authentication and Session Management
Handles user login/logout and session tracking.
"""

import time
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from core.user import UserManager, User


@dataclass
class Session:
    """Represents an authenticated user session."""
    username: str
    uid: int
    gid: int
    login_time: float = field(default_factory=time.time)
    is_authenticated: bool = True
    terminal: Optional[str] = None
    
    def get_prompt(self, cwd: str = "/") -> str:
        """Generate shell prompt."""
        return f"{self.username}@pureos:{cwd}$ "


class Authenticator:
    """Handles user authentication."""
    
    def __init__(self, user_manager: UserManager):
        self.um = user_manager
        self.current_session: Optional[Session] = None
        self.sessions: List[Session] = []
    
    def login(self, username: str, password: str) -> tuple:
        """Authenticate user and create session.
        
        Returns:
            (success: bool, session_or_message: Session|str)
        """
        # Check if user exists
        user = self.um.get_user(username)
        if not user:
            return False, "Invalid username or password"
        
        if not user.is_active:
            return False, "Account is disabled"
        
        # Verify password
        if not self.um.verify_password(username, password):
            return False, "Invalid username or password"
        
        # Create session
        session = Session(
            username=username,
            uid=user.uid,
            gid=user.gid
        )
        
        # Update last login time
        user.last_login = time.time()
        
        # Add to sessions list
        self.sessions.append(session)
        self.current_session = session
        
        return True, session
    
    def logout(self) -> bool:
        """Logout current user."""
        if self.current_session:
            self.current_session.is_authenticated = False
            if self.current_session in self.sessions:
                self.sessions.remove(self.current_session)
            self.current_session = None
            return True
        return False
    
    def switch_user(self, username: str, password: str) -> tuple:
        """Switch to different user (like su command).
        
        Returns:
            (success: bool, session_or_message: Session|str)
        """
        return self.login(username, password)
    
    def is_authenticated(self) -> bool:
        """Check if there's an active authenticated session."""
        return (self.current_session is not None and 
                self.current_session.is_authenticated)
    
    def get_current_user(self) -> Optional[str]:
        """Get current username."""
        if self.current_session:
            return self.current_session.username
        return None
    
    def get_current_uid(self) -> Optional[int]:
        """Get current user ID."""
        if self.current_session:
            return self.current_session.uid
        return None
    
    def get_current_gid(self) -> Optional[int]:
        """Get current group ID."""
        if self.current_session:
            return self.current_session.gid
        return None
    
    def get_session_info(self) -> Dict:
        """Get information about current session."""
        if not self.current_session:
            return {}
        
        return {
            "username": self.current_session.username,
            "uid": self.current_session.uid,
            "gid": self.current_session.gid,
            "login_time": self.current_session.login_time,
            "is_authenticated": self.current_session.is_authenticated,
        }
    
    def list_active_sessions(self) -> List[Dict]:
        """List all active sessions."""
        return [
            {
                "username": s.username,
                "uid": s.uid,
                "login_time": s.login_time,
            }
            for s in self.sessions
            if s.is_authenticated
        ]
    
    def require_auth(self) -> bool:
        """Check if authentication is required.
        
        In PureOS, we require authentication unless explicitly disabled.
        """
        return True
    
    def get_user_home(self) -> str:
        """Get home directory of current user."""
        if not self.current_session:
            return "/"
        
        user = self.um.get_user(self.current_session.username)
        if user:
            return user.home_dir
        return "/"
    
    def check_permission(self, required_uid: int = None, 
                        required_gid: int = None) -> bool:
        """Check if current user has required permissions.
        
        Args:
            required_uid: Required user ID (None = any)
            required_gid: Required group ID (None = any)
        
        Returns:
            True if user has permission
        """
        if not self.current_session:
            return False
        
        # Root (UID 0) has all permissions
        if self.current_session.uid == 0:
            return True
        
        # Check UID
        if required_uid is not None:
            if self.current_session.uid != required_uid:
                return False
        
        # Check GID
        if required_gid is not None:
            if self.current_session.gid != required_gid:
                # Also check supplementary groups
                user = self.um.get_user(self.current_session.username)
                if user:
                    user_groups = self.um.get_user_groups(user.username)
                    user_gids = [self.um.get_group(g).gid for g in user_groups 
                               if self.um.get_group(g)]
                    if required_gid not in user_gids:
                        return False
        
        return True
    
    def can_read_file(self, file_owner: str, file_group: str, 
                     permissions: str) -> bool:
        """Check if current user can read a file.
        
        Args:
            file_owner: Username of file owner
            file_group: Group name of file
            permissions: Permission string (e.g., 'rw-r--r--')
        
        Returns:
            True if user can read the file
        """
        if not self.current_session:
            return False
        
        current_user = self.current_session.username
        current_uid = self.current_session.uid
        
        # Root can read everything
        if current_uid == 0:
            return True
        
        # Parse permissions (format: rwxrwxrwx)
        owner_perm = permissions[0:3]
        group_perm = permissions[3:6]
        other_perm = permissions[6:9]
        
        # Check if owner
        if file_owner == current_user:
            return 'r' in owner_perm
        
        # Check if in group
        user_groups = self.um.get_user_groups(current_user)
        if file_group in user_groups:
            return 'r' in group_perm
        
        # Others
        return 'r' in other_perm
    
    def can_write_file(self, file_owner: str, file_group: str,
                      permissions: str) -> bool:
        """Check if current user can write to a file."""
        if not self.current_session:
            return False
        
        current_user = self.current_session.username
        current_uid = self.current_session.uid
        
        # Root can write everything
        if current_uid == 0:
            return True
        
        # Parse permissions
        owner_perm = permissions[0:3]
        group_perm = permissions[3:6]
        other_perm = permissions[6:9]
        
        # Check if owner
        if file_owner == current_user:
            return 'w' in owner_perm
        
        # Check if in group
        user_groups = self.um.get_user_groups(current_user)
        if file_group in user_groups:
            return 'w' in group_perm
        
        # Others
        return 'w' in other_perm
    
    def can_execute_file(self, file_owner: str, file_group: str,
                        permissions: str) -> bool:
        """Check if current user can execute a file."""
        if not self.current_session:
            return False
        
        current_user = self.current_session.username
        current_uid = self.current_session.uid
        
        # Root can execute everything
        if current_uid == 0:
            return True
        
        # Parse permissions
        owner_perm = permissions[0:3]
        group_perm = permissions[3:6]
        other_perm = permissions[6:9]
        
        # Check if owner
        if file_owner == current_user:
            return 'x' in owner_perm
        
        # Check if in group
        user_groups = self.um.get_user_groups(current_user)
        if file_group in user_groups:
            return 'x' in group_perm
        
        # Others
        return 'x' in other_perm
