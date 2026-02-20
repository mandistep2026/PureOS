"""
tests/unit/test_user.py
========================
Unit tests for the :class:`~core.user.UserManager` class.

Covers:
- /etc/passwd and /etc/group system file population (Test 47)
- User group membership via get_user_groups / is_user_in_group (Test 49)
- create_user: success, duplicate, invalid username
- delete_user: success, root protection, nonexistent user
- change_password: success and subsequent authentication validation
"""

import unittest

from tests.base import BaseTestCase
from core.filesystem import FileSystem
from core.user import UserManager, User, Group


# ---------------------------------------------------------------------------
# /etc/passwd and /etc/group system files
# ---------------------------------------------------------------------------

class TestUserManagerEtcFiles(BaseTestCase):
    """Verify /etc/passwd and /etc/group are written by UserManager (Test 47)."""

    def setUp(self):
        super().setUp()
        self.fs = self.create_filesystem()
        self.um = self.create_user_manager(self.fs)

    def test_etc_passwd_exists(self):
        """UserManager initialisation should (re)write /etc/passwd."""
        self.assertFileExists(
            self.fs, "/etc/passwd",
            "/etc/passwd must exist after UserManager is initialised.",
        )

    def test_etc_passwd_contains_root(self):
        """root must appear as an entry in /etc/passwd."""
        self.assertFileContains(
            self.fs, "/etc/passwd", b"root",
            "/etc/passwd should contain a root entry.",
        )

    def test_etc_passwd_contains_alice(self):
        """The default 'alice' account must appear in /etc/passwd."""
        self.assertFileContains(
            self.fs, "/etc/passwd", b"alice",
            "/etc/passwd should contain the default alice entry.",
        )

    def test_etc_passwd_format_uses_colons(self):
        """Each /etc/passwd entry should use the colon-separated format."""
        content = self.fs.read_file("/etc/passwd")
        self.assertIsNotNone(content, "/etc/passwd must be readable.")
        # Every non-empty line should contain field separators
        for line in content.decode().splitlines():
            if line.strip():
                self.assertIn(
                    ":",
                    line,
                    f"/etc/passwd line should use ':' separators: {line!r}",
                )

    def test_etc_group_exists(self):
        """UserManager initialisation should (re)write /etc/group."""
        self.assertFileExists(
            self.fs, "/etc/group",
            "/etc/group must exist after UserManager is initialised.",
        )

    def test_etc_group_contains_root_group(self):
        """The root group must appear in /etc/group."""
        self.assertFileContains(
            self.fs, "/etc/group", b"root",
            "/etc/group should contain the root group entry.",
        )

    def test_etc_group_updated_after_create_user(self):
        """Creating a user should update /etc/group with the new primary group."""
        self.um.create_user("newperson", "pass123")
        self.assertFileContains(
            self.fs, "/etc/group", b"newperson",
            "/etc/group should contain the new user's primary group after create_user.",
        )

    def test_etc_passwd_updated_after_create_user(self):
        """Creating a user should update /etc/passwd with the new entry."""
        self.um.create_user("newperson", "pass123")
        self.assertFileContains(
            self.fs, "/etc/passwd", b"newperson",
            "/etc/passwd should contain the new user entry after create_user.",
        )

    def test_etc_passwd_updated_after_delete_user(self):
        """Deleting a user should remove them from /etc/passwd."""
        self.um.create_user("tempuser", "temppass")
        self.um.delete_user("tempuser")
        content = self.fs.read_file("/etc/passwd")
        self.assertNotIn(
            b"tempuser",
            content,
            "/etc/passwd should not contain a deleted user.",
        )


# ---------------------------------------------------------------------------
# User group membership
# ---------------------------------------------------------------------------

class TestUserManagerGroupMembership(BaseTestCase):
    """Tests for group membership queries (Test 49 — groups command logic)."""

    def setUp(self):
        super().setUp()
        self.fs = self.create_filesystem()
        self.um = self.create_user_manager(self.fs)

    def test_alice_belongs_to_own_primary_group(self):
        """alice should be a member of the 'alice' primary group."""
        self.assertTrue(
            self.um.is_user_in_group("alice", "alice"),
            "alice should be a member of the 'alice' group.",
        )

    def test_alice_belongs_to_users_group(self):
        """alice should be a member of the 'users' group."""
        self.assertTrue(
            self.um.is_user_in_group("alice", "users"),
            "alice should be a member of the 'users' group.",
        )

    def test_root_belongs_to_root_group(self):
        """root should be a member of the 'root' group."""
        self.assertTrue(
            self.um.is_user_in_group("root", "root"),
            "root should be a member of the 'root' group.",
        )

    def test_get_user_groups_returns_list(self):
        """get_user_groups should return a list of group names."""
        groups = self.um.get_user_groups("alice")
        self.assertIsInstance(groups, list, "get_user_groups should return a list.")
        self.assertGreater(len(groups), 0, "alice should belong to at least one group.")

    def test_get_user_groups_contains_primary_group(self):
        """get_user_groups should include the user's own primary group."""
        groups = self.um.get_user_groups("alice")
        self.assertIn(
            "alice",
            groups,
            "alice's primary group should be in get_user_groups('alice').",
        )

    def test_is_user_in_group_false_for_nonmember(self):
        """is_user_in_group should return False if the user is not in the group."""
        result = self.um.is_user_in_group("alice", "wheel")
        self.assertFalse(
            result,
            "alice should not be in the 'wheel' group by default.",
        )

    def test_is_user_in_group_false_for_nonexistent_group(self):
        """is_user_in_group should return False for a group that does not exist."""
        result = self.um.is_user_in_group("alice", "nonexistent_group")
        self.assertFalse(
            result,
            "is_user_in_group should return False for a nonexistent group.",
        )

    def test_new_user_belongs_to_users_group(self):
        """A newly created user should automatically be added to the 'users' group."""
        self.um.create_user("charlie", "charliepass")
        self.assertTrue(
            self.um.is_user_in_group("charlie", "users"),
            "A newly created user should be in the 'users' group.",
        )


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------

class TestUserManagerCreateUser(BaseTestCase):
    """Tests for the create_user factory method."""

    def setUp(self):
        super().setUp()
        self.um = self.create_user_manager()

    def test_create_user_success(self):
        """create_user with valid inputs should return (True, message)."""
        success, message = self.um.create_user("bob", "bobpass")
        self.assertTrue(success, f"create_user should succeed. Got: {message}")

    def test_create_user_makes_user_findable(self):
        """After create_user the user should be discoverable via user_exists."""
        self.um.create_user("carol", "carolpass")
        self.assertUserExists(self.um, "carol")

    def test_create_user_creates_home_directory(self):
        """create_user should create the user's home directory by default."""
        fs = self.create_filesystem()
        um = self.create_user_manager(fs)
        um.create_user("dave", "davepass")
        self.assertTrue(
            fs.exists("/home/dave"),
            "create_user should create the home directory /home/dave.",
        )

    def test_create_user_duplicate_fails(self):
        """create_user with an existing username should return (False, message)."""
        self.um.create_user("bob", "bobpass")
        success, message = self.um.create_user("bob", "anotherpass")
        self.assertFalse(
            success,
            "create_user should fail when the username already exists.",
        )

    def test_create_user_invalid_username_starting_with_digit(self):
        """A username that starts with a digit should be rejected."""
        success, message = self.um.create_user("1invalid", "pass")
        self.assertFalse(
            success,
            "create_user should reject usernames that start with a digit.",
        )

    def test_create_user_empty_username_fails(self):
        """An empty username should be rejected by create_user."""
        success, message = self.um.create_user("", "pass")
        self.assertFalse(success, "create_user should reject an empty username.")

    def test_create_user_assigns_unique_uid(self):
        """Two different users should receive distinct UIDs."""
        self.um.create_user("user1", "pass1")
        self.um.create_user("user2", "pass2")
        uid1 = self.um.get_user("user1").uid
        uid2 = self.um.get_user("user2").uid
        self.assertNotEqual(uid1, uid2, "Different users should have distinct UIDs.")

    def test_create_user_custom_home_dir(self):
        """create_user should respect a custom home_dir parameter."""
        fs = self.create_filesystem()
        um = self.create_user_manager(fs)
        um.create_user("frank", "frankpass", home_dir="/srv/frank")
        user = um.get_user("frank")
        self.assertEqual(
            user.home_dir,
            "/srv/frank",
            "User home_dir should match the custom value passed to create_user.",
        )


# ---------------------------------------------------------------------------
# delete_user
# ---------------------------------------------------------------------------

class TestUserManagerDeleteUser(BaseTestCase):
    """Tests for the delete_user method."""

    def setUp(self):
        super().setUp()
        self.um = self.create_user_manager()
        self.um.create_user("deleteme", "dpass")

    def test_delete_user_success(self):
        """delete_user should return (True, message) for a valid username."""
        success, message = self.um.delete_user("deleteme")
        self.assertTrue(success, f"delete_user should succeed. Got: {message}")

    def test_delete_user_removes_from_user_table(self):
        """After delete_user the user should no longer appear in user_exists."""
        self.um.delete_user("deleteme")
        self.assertUserNotExists(self.um, "deleteme")

    def test_delete_root_is_rejected(self):
        """delete_user should refuse to delete the root account."""
        success, message = self.um.delete_user("root")
        self.assertFalse(
            success,
            "delete_user('root') should be rejected with a failure response.",
        )
        self.assertUserExists(self.um, "root",
                              "root must still exist after a refused delete_user call.")

    def test_delete_nonexistent_user_fails(self):
        """delete_user for an unknown username should return (False, message)."""
        success, message = self.um.delete_user("ghost_user")
        self.assertFalse(
            success,
            "delete_user should return False for a username that does not exist.",
        )

    def test_delete_user_removes_from_groups(self):
        """Deleting a user should remove them from all groups they belonged to."""
        self.um.delete_user("deleteme")
        for group in self.um.list_groups():
            self.assertNotIn(
                "deleteme",
                group.members,
                f"Deleted user should not remain in group '{group.name}'.",
            )


# ---------------------------------------------------------------------------
# change_password
# ---------------------------------------------------------------------------

class TestUserManagerChangePassword(BaseTestCase):
    """Tests for the change_password method and subsequent authentication."""

    def setUp(self):
        super().setUp()
        self.um = self.create_user_manager()

    def test_change_password_success(self):
        """change_password should return (True, message) for a valid username."""
        success, message = self.um.change_password("alice", "newpass456")
        self.assertTrue(success, f"change_password should succeed. Got: {message}")

    def test_changed_password_authenticates_correctly(self):
        """After change_password, verify_password should accept the new password."""
        self.um.change_password("alice", "brandnewpass")
        result = self.um.verify_password("alice", "brandnewpass")
        self.assertTrue(
            result,
            "verify_password should return True for the newly set password.",
        )

    def test_old_password_rejected_after_change(self):
        """After change_password, the old password should no longer authenticate."""
        self.um.change_password("alice", "brandnewpass")
        result = self.um.verify_password("alice", "password123")
        self.assertFalse(
            result,
            "verify_password should return False for the old password after change.",
        )

    def test_change_password_nonexistent_user_fails(self):
        """change_password for an unknown username should return (False, message)."""
        success, message = self.um.change_password("nobody", "somepass")
        self.assertFalse(
            success,
            "change_password should fail for a username that does not exist.",
        )

    def test_verify_password_wrong_password_returns_false(self):
        """verify_password with an incorrect password should return False."""
        result = self.um.verify_password("alice", "wrong_password")
        self.assertFalse(
            result,
            "verify_password should return False when the password is incorrect.",
        )

    def test_verify_password_correct_password_returns_true(self):
        """verify_password with the correct password should return True."""
        result = self.um.verify_password("alice", "password123")
        self.assertTrue(
            result,
            "verify_password should return True for the correct password.",
        )


# ---------------------------------------------------------------------------
# UserManager query helpers
# ---------------------------------------------------------------------------

class TestUserManagerQueries(BaseTestCase):
    """Tests for the various query methods on UserManager."""

    def setUp(self):
        super().setUp()
        self.um = self.create_user_manager()

    def test_user_exists_true_for_root(self):
        """user_exists should return True for the built-in root account."""
        self.assertTrue(self.um.user_exists("root"))

    def test_user_exists_true_for_alice(self):
        """user_exists should return True for the default alice account."""
        self.assertTrue(self.um.user_exists("alice"))

    def test_user_exists_false_for_unknown(self):
        """user_exists should return False for a username that was never created."""
        self.assertFalse(self.um.user_exists("unknown_xyz"))

    def test_get_user_returns_user_object(self):
        """get_user should return a User instance for a known username."""
        user = self.um.get_user("alice")
        self.assertIsNotNone(user, "get_user('alice') should not return None.")
        self.assertIsInstance(user, User)

    def test_get_user_returns_none_for_unknown(self):
        """get_user should return None for an unknown username."""
        result = self.um.get_user("nobody")
        self.assertIsNone(result, "get_user should return None for unknown users.")

    def test_get_user_by_uid_root_is_uid_zero(self):
        """root should have UID 0."""
        root = self.um.get_user("root")
        self.assertEqual(root.uid, 0, "root must have UID 0.")

    def test_list_users_contains_root_and_alice(self):
        """list_users should include both root and alice."""
        usernames = {u.username for u in self.um.list_users()}
        self.assertIn("root", usernames)
        self.assertIn("alice", usernames)

    def test_get_group_returns_group_object(self):
        """get_group should return a Group instance for a known group name."""
        group = self.um.get_group("root")
        self.assertIsNotNone(group, "get_group('root') should not return None.")
        self.assertIsInstance(group, Group)

    def test_get_group_returns_none_for_unknown(self):
        """get_group should return None for an unknown group name."""
        result = self.um.get_group("no_such_group_xyz")
        self.assertIsNone(result, "get_group should return None for an unknown group.")

    def test_list_groups_is_non_empty(self):
        """list_groups should return at least the default system groups."""
        groups = self.um.list_groups()
        self.assertGreater(len(groups), 0, "list_groups should return at least one group.")

    def test_export_passwd_contains_all_users(self):
        """export_passwd should contain an entry for every user in the manager."""
        content = self.um.export_passwd()
        for username in ("root", "alice"):
            self.assertIn(
                username,
                content,
                f"export_passwd should include an entry for '{username}'.",
            )

    def test_export_group_contains_all_groups(self):
        """export_group should contain an entry for every group in the manager."""
        content = self.um.export_group()
        self.assertIn("root", content, "export_group should include the 'root' group.")


if __name__ == "__main__":
    unittest.main()
