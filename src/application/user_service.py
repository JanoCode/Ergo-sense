from typing import List
from domain.user import User

class UserService:
    def __init__(self, user_repository):
        self.user_repository = user_repository

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
