from typing import Optional
from datetime import datetime
from domain.session import Session
from application.user_service import UserService

class SessionService:
    def __init__(self, session_repository, user_service: UserService):
        self.session_repository = session_repository
        self.user_service = user_service
        self._active_session: Optional[Session] = None

    def start_session(self) -> Session:
        if self._active_session is not None:
            raise ValueError("Ya existe una sesión activa.")
            
        user = self.user_service.get_active_user()
        if not user:
            raise ValueError("No hay usuario activo para iniciar sesión.")
            
        session = Session(user_id=user.id, started_at=datetime.now())
        self._active_session = self.session_repository.save(session)
        return self._active_session

    def end_session(self) -> Session:
        if not self._active_session:
            raise ValueError("No hay sesión activa para finalizar.")
            
        session = self._active_session
        session.ended_at = datetime.now()
        session.duration_seconds = int((session.ended_at - session.started_at).total_seconds())
        
        self.session_repository.save(session)
        self._active_session = None
        return session

    def get_active_session(self) -> Optional[Session]:
        return self._active_session
