from datetime import datetime

from src.domain.entities.user import User

from src.domain.interfaces.user_repository_abc import UserRepositoryABC
from src.domain.interfaces.password_hasher_abc import PasswordHasherABC


class UserService:
    def  __init__(self, user_repo: UserRepositoryABC, password_hasher: PasswordHasherABC):
        self.user_repo = user_repo
        self.password_hasher = password_hasher

    async def from_matricule(self, matricule):
        user = await self.user_repo.get(
            matricule
        )
        user._password_hasher = self.password_hasher
        return user

    async def notify_login(self, user: User):
        user.last_login_at = datetime.now()
        return await self.user_repo.update(user)

    async def create_user(self, user_as_dict: dict):
        if not "password" in user_as_dict:
            user_as_dict["password"] = User.default_password(user_as_dict)
        user = User.from_dict(**{**user_as_dict, "password_hasher": self.password_hasher})

        return bool(await self.user_repo.create(user))
