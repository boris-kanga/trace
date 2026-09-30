from abc import ABC, abstractmethod
from typing import Literal, Any
from uuid import UUID

from src.domain.entities.immobilization import Immobilization, ImmobilizationSubFamily, ImmobilizationFamily
from src.domain.entities.localization import Localization, Agency
from src.domain.entities.suppliers import Supplier


class ImmobilizationRepositoryABC(ABC):
    @abstractmethod
    async def __aenter__(self) -> dict:
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    @abstractmethod
    async def create_supplier(self, supplier: Supplier, **_):
        pass

    @abstractmethod
    async def create_agency(self, agency: Agency, **_):
        pass

    @abstractmethod
    async def create_localization(self, localization: Localization, **_):
        pass

    @abstractmethod
    async def insert_family(self, family: list[ImmobilizationFamily], **_):
        pass

    @abstractmethod
    async def insert_subfamily(self, subfamily: list[ImmobilizationSubFamily], **_):
        pass

    @abstractmethod
    async def update_id(self, immobilization: Immobilization, new_id: UUID):
        pass

    @abstractmethod
    async def save(self, immobilization: Immobilization):
        pass

    @abstractmethod
    async def massive_save(self, immobilizations: list[Immobilization]):
        pass

    @abstractmethod
    async def _get(self, _as: Literal["items","size"]="items", **kwargs) -> list[Immobilization] | int:
        """kwargs is a dict of immobilization details use to filter in database
            _as values in (items|size) default items
        """
        pass

    async def get(self, _as: Literal["items","size"]="items", **kwargs) -> list[Immobilization] | int:
        if "id_immobilization" in kwargs:
            item = kwargs.pop("id_immobilization")
            if not isinstance(item, UUID):
                if "?" in item:
                    item = item.split("?")[1]
            kwargs["id_immobilization"] = item
        return await self._get(_as=_as, **kwargs)

    @abstractmethod
    async def delete(self, obj: Agency|Localization|Immobilization|Supplier):
        pass

    @abstractmethod
    async def get_agency(self):
        pass

    @abstractmethod
    async def get_localization(self):
        pass

    @abstractmethod
    async def get_family(self):
        pass

    @abstractmethod
    async def get_subfamily(self):
        pass

    @abstractmethod
    async def get_supplier(self):
        pass

