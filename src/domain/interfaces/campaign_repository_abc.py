from abc import ABC, abstractmethod
from typing import List, Tuple

from src.domain.entities.campaign import Campaign, Inventory
from src.domain.entities.user import User


class CampaignRepositoryABC(ABC):
    @abstractmethod
    async def get(self, year=None, _id=None, status=None) -> List[Campaign]:
        pass

    @abstractmethod
    async def create(self, campaign: Campaign, localization_ids: list[int]) -> Campaign:
        pass

    async def update_campaign(self, campaign: Campaign, localization_ids: list[int] | None) -> bool:
        pass

    @abstractmethod
    async def add_inventorist(self, campaign: Campaign | int, matricule, localization_ids: list[int]):
        pass

    @abstractmethod
    async def delete_inventorist(self, campaign: Campaign | int, matricule) -> bool:
        pass

    @abstractmethod
    async def stats(self, campaign: list[Campaign | int]):
        pass

    @abstractmethod
    async def campaign_zone(self, campaign_id, matricule=None, full=False):
        pass

    @abstractmethod
    async def put_inventory(self, inv: Inventory):
        pass

    @abstractmethod
    async def user_can_mark_inventory(self, campaign_id, id_immobilization, matricule):
        pass

    @abstractmethod
    async def get_inventory_history(self, campaign_id, matricule=None):
        pass

    @abstractmethod
    async def get_inventory_history_on_immobilization(self, id_immobilization, limit=5):
        pass

    @abstractmethod
    async def delete_campaign(self, campaign: Campaign | int) -> bool:
        pass

    @abstractmethod
    async def get_inventorist(self, campaign: Campaign | int):
        pass

    @abstractmethod
    async def campaign_immobilization(self, campaign_id, matricule=None, localization_ids: list[int] | None = None, **_):
        pass

    @abstractmethod
    async def merge_inventory_immo_status(self, campaign_id: int):
        pass

    @abstractmethod
    async def most_recent_immobilization_status(self, id_immobilization):
        pass





