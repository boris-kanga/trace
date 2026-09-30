from typing import Literal

from src.domain.entities.immobilization import ImmobilizationStatus
from src.domain.entities.user import User, Role

from datetime import date

from werkzeug.datastructures import FileStorage

from pydantic import BaseModel
from pydantic_core import core_schema


class FileTypeSchema:
    filename: str
    content_type: str

    def read(self):
        pass

    @classmethod
    def __get_pydantic_core_schema__(
        cls, *_, **__
    ) -> core_schema.CoreSchema:
        return core_schema.union_schema([
            core_schema.bytes_schema(),
            core_schema.is_instance_schema(FileStorage)
        ])


class LoginSchema(BaseModel):
    username: str
    password: str


class Login200(BaseModel):
    message: str
    token: str
    user: User


class RegisterUser(BaseModel):
    matricule: str
    first_name: str
    last_name: str
    email: str
    role: Role


class PatchUser(BaseModel):
    first_name: str
    last_name: str
    email: str
    role: Role


class LocalizationCreation(BaseModel):
    location_code: str


class ImmoFilters(BaseModel):
    agency_code: str | None = None
    location_code: str | None = None
    limit: int = 20
    cursor: str | None = None
    status: Literal["ALL", "GOOD", "DAMAGED", "ASSOCIED", "NOT_ASSOCIATED"] = "ALL"
    q: str = ""

    min_date: date | None = None
    max_date: date | None = None


class ImmoSubFamilyCreation(BaseModel):
    id_subfamily: str
    title: str

    immo_account: str | None = None
    dotation_account: str | None = None
    depreciation_account: str | None = None

    depreciation_year_rate: float | None = None


class ImmoCreation(BaseModel):
    title: str
    # localization
    id_localization: int | None = None
    location_code: str| None =None
    code_agency: str | None =None
    # family
    id_subfamily: str

    serial_number: str | None = None

    status: str = "GOOD"

    comment: str | None = None

    main_image: FileTypeSchema | None = None

    invoice_file: FileTypeSchema | None = None

    # extra info for admin
    ubigreen_number: str | None = None
    id_immobilization_amplitude: int | None = None
    supplier: str | None = None
    order_number: str | None = None
    order_date: date | None = None

    delivery_note_number: str | None = None
    delivery_note_date: date | None = None

    invoice_number: str | None = None
    invoice_date: date | None = None

    acquittement_date: date | None = None
    acquittement_value: float | None = None


class CampaignFilter(BaseModel):
    year: int | None = None


class CampaignCreation(BaseModel):
    title: str
    start_date: date
    end_date: date
    localization_ids: list[int]


class CampaignInventorist(BaseModel):
    matricule: str
    localization_ids: list[int]


class InventoryMark(BaseModel):
    status: ImmobilizationStatus
    comment: str | None = None
    latitude: float
    longitude: float

    device_id: None | str = None
    current_img: FileTypeSchema | None

    main_image: FileTypeSchema | None = None
    serial_number: str | None = None


class ImmoInventoryArgs(BaseModel):
    limit: int = 5


class CampaignImmobilizationFilter(BaseModel):
    localization_ids: str = ""
    serial_number: str | None = None
    title: str | None = None
    id_immobilization_amplitude: int | None = None


class ImmoGenerateQrCode(BaseModel):
    size: int = 1

    title: str | None = None

    # family
    id_subfamily: str | None = None
    # localization
    id_localization: int | None = None
    location_code: str | None = None
    code_agency: str | None = None

    invoice_file: FileTypeSchema | None = None

    supplier: str | None = None
    order_number: str | None = None
    order_date: date | None = None

    delivery_note_number: str | None = None
    delivery_note_date: date | None = None

    invoice_number: str | None = None
    invoice_date: date | None = None

    acquittement_date: date | None = None
    acquittement_value: float | None = None



class ChangeQrCode(BaseModel):
    id_immobilization: str
