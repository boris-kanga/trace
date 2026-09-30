import uuid
from datetime import date

from src.core.logger import get_logger
from src.domain.interfaces.campaign_repository_abc import CampaignRepositoryABC
from src.domain.entities.campaign import Campaign, CampaignStatus, Inventory
from src.domain.entities.user import User, Role


logger = get_logger(__name__)


class CampaignService:
    def __init__(self, campaign_repo: CampaignRepositoryABC):
        self.repo = campaign_repo

    async def mark_ended(
            self,
            cpg: Campaign,
    ):
        cpg.status = CampaignStatus.COMPLETED

        _bool = await self.repo.update_campaign(cpg, None)
        if _bool:
            await self.repo.merge_inventory_immo_status(cpg.campaign_id)
        return _bool

    async def create_campaign(self, title, start_date: date, end_date: date, user: User, localization_ids: list[int], _id=None) -> Campaign | str:

        if str(start_date) < str(date.today()):
            return "Start date must be greater than today's date"
        cpg = Campaign(
            title=title,
            start_date=start_date,
            end_date=end_date,
            status=CampaignStatus.DRAFT,
            created_by=user,
            updated_by=user,
        )
        if _id is not None:
            cpg.campaign_id = _id
            await self.repo.update_campaign(cpg, localization_ids)
            return cpg
        await self.repo.create(cpg, localization_ids)
        return cpg

    async def get_campaign_and_stats(self, year=None, _id=None):
        cpg = await self.repo.get(_id=_id, year=year)
        stats = await self.repo.stats(cpg)
        return cpg, stats

    async def add_inventorist(self, campaign_id, matricule, localization_ids: list[int]):
        cpg = await self.repo.get(_id=campaign_id)
        if not cpg:
            return False, "Campaign not found"
        cpg = cpg[0]
        await self.repo.add_inventorist(cpg, matricule, localization_ids)
        return True, "Campaign added"

    async def mark_inventory(self, inventory: Inventory):
        if inventory.last_scanned_by.role == Role.INVENTORIST:
            # check if he can do this
            _id = inventory.campaign
            imm = inventory.immobilization
            res = await self.repo.user_can_mark_inventory(
                _id if isinstance(_id, int) else _id.campaign_id,
                imm if isinstance(imm, (str, uuid.UUID)) else imm.id_immobilization,
                inventory.last_scanned_by.matricule
            )
            if not res:
                return False, "Inventory not found"
        logger.info(inventory)
        res = await self.repo.put_inventory(inventory)

        logger.info(f"-------------------------{res}")
        return res, "Inventory added" if res else "Inventory not found"
