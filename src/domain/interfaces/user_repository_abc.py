from abc import ABC, abstractmethod

from src.domain.entities.user import User


class UserRepositoryABC(ABC):

    @abstractmethod
    async def get_all(self) -> list[User]:
        pass

    @abstractmethod
    async def get(self, matricule: str) -> User:
        # in the query use deleted_at is not NULL
        pass

    @abstractmethod
    async def delete(self, matricule: str) -> bool:
        # use soft delete update deleted_at
        pass

    @abstractmethod
    async def create(self, user: User, password: str | None=None) -> bool:
        pass

    @abstractmethod
    async def update(self, user: User) -> bool:
        pass



