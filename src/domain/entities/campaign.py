import uuid
from dataclasses import dataclass, field, asdict
from datetime import date
from enum import Enum

from src.domain.entities.user import User
from src.domain.entities.immobilization import ImmobilizationStatus, Immobilization


class CampaignStatus(str, Enum):
    DRAFT = "DRAFT"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"



@dataclass
class Campaign:
    campaign_id: int = field(init=False)
    title: str

    start_date: date
    end_date: date

    created_by: User
    updated_by: User

    status: CampaignStatus = CampaignStatus.DRAFT

    def to_dict(self):
        d = {
            "title": self.title,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "status": self.status.value,
            "created_by": self.created_by.to_dict()
        }
        if hasattr(self, "campaign_id"):
            d["campaign_id"] = self.campaign_id
        return d


@dataclass
class Inventory:
    campaign: Campaign | int
    immobilization: Immobilization| uuid.UUID | str

    status: ImmobilizationStatus
    last_scanned_by: User
    comment: str | None

    latitude: float | None
    longitude: float | None
    device_id: None | str = None