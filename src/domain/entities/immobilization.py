from dataclasses import dataclass, field, asdict
from datetime import date

from uuid import UUID
from enum import Enum

from src.core.logger import get_logger
from src.domain.entities.user import User
from src.domain.entities.localization import Localization, Agency
from src.domain.entities.suppliers import Supplier, EMPTY

logger = get_logger(__name__)

@dataclass
class ImmobilizationFamily:
    id_family: str
    title: str

    def __post_init__(self):
        self.id_family = self.id_family[:5]


@dataclass
class ImmobilizationSubFamily:
    id_subfamily: str
    title: str | None = None
    family: ImmobilizationFamily | str | None = None

    immo_account: str | None = None
    dotation_account: str | None = None
    depreciation_account: str | None = None

    depreciation_year_rate: float | None = None

    def __post_init__(self):
        self.id_subfamily = self.id_subfamily[:10]

    def to_dict(self):
        d = asdict(self)
        d.pop("family", None)
        f = self.family
        if isinstance(f, ImmobilizationFamily):
            f = f.id_family
        if isinstance(f, (str, int)):
            d["id_family"] = str(f)

        return d

    def __eq__(self, other):
        if isinstance(other, ImmobilizationSubFamily):
            return self.id_subfamily == other.id_subfamily
        if isinstance(other, str):
            return self.id_subfamily == other
        return False


class ImmobilizationStatus(Enum):
    GOOD = "GOOD"
    NOT_FOUND = "NOT_FOUND"
    MOVED = "MOVED"
    DAMAGED = "DAMAGED"
    UNKNOWN = "UNKNOWN"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"


@dataclass
class Immobilization:
    id_immobilization: UUID = field(init=False)
    id_immobilization_amplitude: int | None = None

    title: str | None = None

    localization: Localization | None = None
    sub_family: ImmobilizationSubFamily | None = None
    supplier: Supplier | None = None

    ##############"
    order_number: str | None = None
    order_date: date | None = None

    delivery_note_number: str | None = None
    delivery_note_date: date | None = None

    invoice_number: str | None = None
    invoice_date: date | None = None

    acquittement_date: date | None = None
    acquittement_value: float | None = None

    created_by: User | str | None = None
    updated_by: User | str | None = None

    status: ImmobilizationStatus = ImmobilizationStatus.GOOD
    serial_number: str | None = None
    comment: str | None = None

    ubigreen_number: str | None = None


    @classmethod
    def from_dict(cls, im):

        id_immobilization = im["id_immobilization"]

        if im["id_localization"]:
            loc = Localization(
                im.get("location_code", ""),
                Agency(
                    im.get("code_agency", ""),
                    im.get("a_title", "")
                )
            )
            loc.id_localization = im["id_localization"]
        else:
            loc = None

        ss = im.get("id_supplier") or im.get("s_name")
        if ss:
            if im.get("s_name"):
                s = Supplier(im.get("s_name"))
            else:
                s = Supplier(EMPTY)
            s.address = im.get("address", "")

            if im.get("id_supplier"):
                s.id_supplier = im.get("id_supplier")
        else:
            s = None

        im = Immobilization(
            im["id_immobilization_amplitude"],
            im["title"],
            loc,
            None if im.get("id_subfamily") is None else
            ImmobilizationSubFamily(
                im["id_subfamily"],
                im.get("sub_title", ""),
                None if im.get("id_family") is None else
                ImmobilizationFamily(
                    im.get("id_family"),
                    im.get("f_title")
                )
            ),
            s,
            im["order_number"],
            im["order_date"],
            im["delivery_note_number"],
            im["delivery_note_date"],
            im["invoice_number"],
            im["invoice_date"],
            im["acquittement_date"],
            im["acquittement_value"],

            im["created_by"],
            im["updated_by"],
            ImmobilizationStatus(im["status"]),
            im["serial_number"],
            im["comment"],
            im["ubigreen_number"]
        )
        im.id_immobilization = id_immobilization
        return im

    def to_dict(self):
        d = {
            "id_immobilization_amplitude": self.id_immobilization_amplitude,
            "title": self.title,
            "order_number": self.order_number,
            "order_date": self.order_date,
            "delivery_note_number": self.delivery_note_number,
            "delivery_note_date": self.delivery_note_date,
            "invoice_number": self.invoice_number,
            "invoice_date": self.invoice_date,
            "acquittement_date": self.acquittement_date,
            "acquittement_value": self.acquittement_value,
            "created_by": self.created_by if not isinstance(self.created_by, User) else self.created_by.matricule,
            "updated_by": self.updated_by if not isinstance(self.updated_by, User) else self.updated_by.matricule,
            "status": self.status.value,
            "serial_number": self.serial_number,
            "ubigreen_number": self.ubigreen_number,
            "comment": self.comment,

            "id_localization": None,  # need to be filled for database insertion
            "id_subfamily": None if self.sub_family is None else self.sub_family.id_subfamily,
            "id_supplier": None,
        }
        if self.supplier and hasattr(self.supplier, "id_supplier"):
            d["id_supplier"] = self.supplier.id_supplier
        if hasattr(self.localization, "id_localization"):
            d["id_localization"] = self.localization.id_localization
        if hasattr(self, "id_immobilization"):
            d["id_immobilization"] = self.id_immobilization
        return d
