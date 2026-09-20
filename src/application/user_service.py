from typing import List, Optional
from domain.user import User

class UserService:
    def __init__(self, user_repository):
        self.user_repository = user_repository
        self._active_user: Optional[User] = None

    def create_user(self, name: str) -> User:
        if name is None:
            raise ValueError("El nombre no puede estar vacío.")
            
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("El nombre no puede estar vacío.")

        user = User(name=clean_name)
        return self.user_repository.save(user)

    def get_all_users(self) -> List[User]:
        return self.user_repository.get_all()

    def set_active_user(self, user: User):
        self._active_user = user

    def get_active_user(self) -> Optional[User]:
        return self._active_user
