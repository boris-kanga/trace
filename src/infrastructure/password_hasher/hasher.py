from werkzeug.security import generate_password_hash, check_password_hash

from src.domain.entities.user import User
from src.domain.interfaces.password_hasher_abc import PasswordHasherABC


class PasswordHasher(PasswordHasherABC):

    def password_verify(self, password, password_hash):
        return check_password_hash(password_hash, password)

    def password_hash(self, password):
        return generate_password_hash(password)