import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../src'))

from domain.user import User
from application.user_service import UserService

class MockUserRepository:
    def __init__(self):
        self.users = []
        self.current_id = 1
        
    def save(self, user: User) -> User:
        user.id = self.current_id
        user.created_at = "2026-09-20 12:00:00"
        self.users.append(user)
        self.current_id += 1
        return user
        
    def get_all(self):
        return self.users

class TestUserService(unittest.TestCase):
    def setUp(self):
        self.repo = MockUserRepository()
        self.service = UserService(self.repo)

    def test_create_user_success(self):
        user = self.service.create_user("  Juan Perez  ")
        self.assertEqual(user.name, "Juan Perez")
        self.assertIsNotNone(user.id)
        self.assertEqual(len(self.repo.users), 1)

    def test_create_user_empty_name(self):
        with self.assertRaises(ValueError):
            self.service.create_user("")

    def test_create_user_spaces_only(self):
        with self.assertRaises(ValueError):
            self.service.create_user("   ")
            
    def test_create_user_none(self):
        with self.assertRaises(ValueError):
            self.service.create_user(None)
            
    def test_get_all_users(self):
        self.service.create_user("User A")
        self.service.create_user("User B")
        users = self.service.get_all_users()
        self.assertEqual(len(users), 2)
        self.assertEqual(users[0].name, "User A")
        self.assertEqual(users[1].name, "User B")

if __name__ == '__main__':
    unittest.main()
