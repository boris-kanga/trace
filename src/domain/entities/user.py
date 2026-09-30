from dataclasses import dataclass, field

from enum import Enum
from datetime import datetime

from src.domain.interfaces.password_hasher_abc import PasswordHasherABC


class Role(Enum):
    INVENTORIST = "INVENTORIST"
    BACKOFFICE = "BACKOFFICE"


class UserException(Exception):
    pass


class UserNotFound(UserException):
    pass


@dataclass
class User:
    _matricule: str = field(init=True)

    first_name: str
    last_name: str
    email: str
    _password_hash: str = field(init=False)

    _password_hasher: PasswordHasherABC = field(init=False)

    def set_hashed_password(
            self, password_hasher: PasswordHasherABC
    ) -> None:
        self._password_hasher = password_hasher

    @property
    def matricule(self):
        return self._matricule

    @property
    def password(self):
        return self._password_hash

    @property
    def password_hash(self):
        return self._password_hash

    @password.setter
    def password(self, password: str):
        if not hasattr(self, "_password_hasher"):
            raise RuntimeError("User has not password_hasher")
        self._password_hash = self._password_hasher.password_hash(password)

    role: Role

    is_active: bool = True

    last_login_at: datetime | None = None
    last_password_modification_date: datetime | None = None

    deleted_at: datetime | None = None

    def is_user_active(self) -> bool:
        return self.is_active and self.deleted_at is None

    def __post_init__(self):
        if self.matricule is None:
            raise TypeError("matricule is null")

        if isinstance(self.role, str):
            self.role = Role(self.role)
        if not isinstance(self.role, Role):
            raise TypeError("role must be of type Role")

    def __hash__(self) -> int:
        return hash(self.matricule)

    def __repr__(self) -> str:
        return f"<User %s>"%(self.matricule,)

    @classmethod
    def default_password(cls, user_as_dict):
        return user_as_dict.get("password") or user_as_dict.get("matricule") + "_test"

    @classmethod
    def from_dict(cls, data: dict | None=None, **kwargs) -> 'User':
        data = (data or {}).copy()
        data.update(kwargs)
        matricule = data.pop("matricule")
        password_hasher = data.pop("password_hasher", None)

        # password
        p = h = None
        if "password" in data:
            p = data.pop("password")
        if "password_hash" in data:
            h = data.pop("password_hash")

        data = {
            k: v for k, v in data.items()
            if k in cls.__annotations__
        }

        u = User(_matricule=matricule, **data)
        # adding password
        if password_hasher is not None:
            u.set_hashed_password(password_hasher)
        if p is not None:
            u.password = p
        if h is not None:
            u._password_hash = h
        return u

    def to_dict(self, full=True) -> dict:
        d = {
            "matricule": self.matricule,
            "role": self.role.value,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "is_active": self.is_active,
            "last_login_at": self.last_login_at,
            "deleted_at": self.deleted_at,
            "last_password_modification_date": self.last_password_modification_date,
        }
        if full and hasattr(self, "_password_hash"):
            d["password_hash"] = self._password_hash
        return d

    def __eq__(self, other, **kwargs) -> bool:
        if isinstance(other, str):
            if hasattr(self, "_password_hasher"):
                print()
                return self._password_hasher.password_verify(other, self.password)

        assert isinstance(other, User)

        return (
            self.matricule == other.matricule and
            self.role == other.role
        )





