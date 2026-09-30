from abc import ABC, abstractmethod


class PasswordHasherABC(ABC):
    @abstractmethod
    def password_hash(self, password):
        pass

    @abstractmethod
    def password_verify(self, password, password_hash):
        pass
