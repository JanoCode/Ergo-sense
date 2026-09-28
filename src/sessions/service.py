from typing import Callable, Optional, List
from datetime import datetime
from sessions.models import Session
from users.service import UserService

class SessionService:
    def __init__(
        self,
        session_repository,
        user_service: UserService,
        now_provider: Callable[[], datetime] = datetime.now,
    ):
        self.session_repository = session_repository
        self.user_service = user_service
        self._active_session: Optional[Session] = None
        self._before_end_callbacks: List[Callable[[], None]] = []
        self._now = now_provider

    def add_before_end_callback(self, callback: Callable[[], None]) -> None:
        self._before_end_callbacks.append(callback)

    def start_session(self) -> Session:
        if self._active_session is not None:
            raise ValueError("Ya existe una sesión activa.")
            
        user = self.user_service.get_active_user()
        if not user:
            raise ValueError("No hay usuario activo para iniciar sesión.")
            
        session = Session(user_id=user.id, started_at=self._now())
        self._active_session = self.session_repository.save(session)
        return self._active_session

    def end_session(self) -> Session:
        if not self._active_session:
            raise ValueError("No hay sesión activa para finalizar.")

        for callback in tuple(self._before_end_callbacks):
            callback()
            
        session = self._active_session
        session.ended_at = self._now()
        session.duration_seconds = int((session.ended_at - session.started_at).total_seconds())
        
        self.session_repository.save(session)
        self._active_session = None
        return session

    def get_active_session(self) -> Optional[Session]:
        return self._active_session

    def get_user_sessions(self, user_id: int) -> List[Session]:
        return self.session_repository.get_by_user_id(user_id)
