import pytest

from src.infrastructure.password_hasher.hasher import PasswordHasher
from src.domain.entities.user import User, Role


def test_user_null_matricule(user_dict):
    user_dict["matricule"] = None

    with pytest.raises(TypeError):
        # need to raise error when matricule is Null
        User.from_dict(**user_dict)


def test_user_no_role(user_dict):
    user_dict["role"] = None
    with pytest.raises(TypeError):
        # need to raise error cause role is null
        User.from_dict(**user_dict)

    user_dict.pop("role", None)
    with pytest.raises(TypeError):
        User.from_dict(**user_dict)


def test_user_bad_role(user_dict):
    with pytest.raises(ValueError):
        # role need to be registered in Role Enum.
        user_dict["role"] = "FAKE*ROLE"
        User.from_dict(**user_dict)


def test_user_entity(user_dict):
    user = User.from_dict(**user_dict, password_hasher=PasswordHasher())
    assert user.matricule == user_dict["matricule"]
    assert user.password != user_dict["password"], "Password must not be same"




