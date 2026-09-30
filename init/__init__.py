from src.infrastructure.database.repositories.campaign_repository import CampaignRepository
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.domain.interfaces.immobilization_repository_abc import ImmobilizationRepositoryABC
from src.infrastructure.database.repositories.immobilization_repository import ImmobilizationRepository
from src.infrastructure.qr_code import QrCode
from src.infrastructure.storage import S3StorageAdapter
from src.services.campaign_service import CampaignService
from src.services.immobilization_service import ImmobilizationService
from src.services.user_service import UserService
from src.infrastructure.database.db_object import DBObject
from src.core.config import DB_CONFIG, WORK_DIR, S3_CONFIG
from src.infrastructure.password_hasher.hasher import PasswordHasher


class InitData:
    @classmethod
    async def default_storage(cls, **storage_params):
        s3 = S3StorageAdapter(**storage_params)
        return s3

    @classmethod
    def default_db_class(cls):
        return DBObject

    @classmethod
    async def default_db(cls, **kwargs):
        init_db = kwargs.pop('init_db', False)

        _kwargs = DB_CONFIG.copy()
        _kwargs.update(kwargs)
        dbo = cls.default_db_class()(**_kwargs)
        await dbo.connect()
        if init_db:
            with open(WORK_DIR + "sql" + "schema.sql", encoding="utf-8") as _fp:
                _fp = _fp.read().strip()
                await dbo.execute(
                    _fp
                )
        return dbo

    @classmethod
    async def user_service(cls, db=None) -> UserService:
        if db is None:
            db = await cls.default_db()

        return UserService(UserRepository(db), PasswordHasher())

    @classmethod
    async def immobilization_repo(cls, db=None) -> ImmobilizationRepositoryABC:
        if db is None:
            db = await cls.default_db()
        return ImmobilizationRepository(db)

    @classmethod
    async def immobilization_service(cls, db, storage=None) -> ImmobilizationService:
        return ImmobilizationService(
            await cls.immobilization_repo(db),
            qr_code=QrCode(),
            s3_object=storage,
        )

    @classmethod
    async def campaign_service(cls, db=None) -> CampaignService:
        if db is None:
            db = await cls.default_db()
        return CampaignService(
            CampaignRepository(db),
        )
