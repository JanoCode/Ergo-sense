import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../src'))

from users.models import User
from sessions.models import Session
from sessions.service import SessionService
from users.service import UserService

class MockUserRepository:
    def __init__(self):
        self.users = []
        self.current_id = 1
    def save(self, user: User) -> User:
        user.id = self.current_id
        self.users.append(user)
        self.current_id += 1
        return user
    def get_all(self):
        return self.users

class MockSessionRepository:
    def __init__(self):
        self.sessions = []
        self.current_id = 1
    def save(self, session: Session) -> Session:
        if session.id is None:
            session.id = self.current_id
            self.current_id += 1
            self.sessions.append(session)
        return session
    def get_by_user_id(self, user_id: int):
        return sorted([s for s in self.sessions if s.user_id == user_id], 
                     key=lambda s: s.started_at, reverse=True)

class TestSessionService(unittest.TestCase):
    def setUp(self):
        self.user_repo = MockUserRepository()
        self.user_service = UserService(self.user_repo)
        self.session_repo = MockSessionRepository()
        self.session_service = SessionService(self.session_repo, self.user_service)

    def test_start_session_no_user(self):
        with self.assertRaises(ValueError):
            self.session_service.start_session()
            
    def test_start_session_success(self):
        user = self.user_service.create_user("Test User")
        self.user_service.set_active_user(user)
        
        session = self.session_service.start_session()
        self.assertIsNotNone(session)
        self.assertEqual(session.user_id, user.id)
        self.assertIsNotNone(session.started_at)
        
    def test_end_session(self):
        user = self.user_service.create_user("Test User")
        self.user_service.set_active_user(user)
        
        self.session_service.start_session()
        ended_session = self.session_service.end_session()
        
        self.assertIsNotNone(ended_session.ended_at)
        self.assertIsNotNone(ended_session.duration_seconds)
        self.assertIsNone(self.session_service.get_active_session())

    def test_get_user_sessions(self):
        user = self.user_service.create_user("Test User")
        self.user_service.set_active_user(user)
        
        self.session_service.start_session()
        self.session_service.end_session()
        
        self.session_service.start_session()
        self.session_service.end_session()
        
        sessions = self.session_service.get_user_sessions(user.id)
        self.assertEqual(len(sessions), 2)

if __name__ == '__main__':
    unittest.main()
