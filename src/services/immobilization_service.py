import asyncio
import io
import uuid
from datetime import datetime
from typing import Literal
from uuid import UUID

from src.core.config import CONFIG
from src.core.logger import get_logger
from src.domain.entities.immobilization import Immobilization, ImmobilizationStatus
from src.domain.entities.localization import Agency, Localization
from src.domain.interfaces.immobilization_repository_abc import ImmobilizationRepositoryABC
from src.domain.interfaces.qrcode_generator_abc import QrCodeABC
from src.domain.interfaces.storage_abc import StorageABC


logger = get_logger(__name__)


class ImmobilizationService:
    def __init__(self, repository: ImmobilizationRepositoryABC, qr_code: QrCodeABC, s3_object: StorageABC|None=None):
        self.repo = repository
        self.s3_object = s3_object
        self.qr_code = qr_code

    async def create_agency(self, agency: Agency):
        return await self.repo.create_agency(agency)

    async def delete_agency(self, agency_code):
        size = await self.repo.get(agency_code=agency_code,_as="size")
        if size > 0:
            return size, False
        res = await self.repo.delete(
            Agency(agency_code, "")
        )
        return size, res.size == 1

    async def delete_localization(self, agency_code, location_code):
        size = await self.repo.get(agency_code=agency_code, location_code=location_code, _as="size")
        if size > 0:
            return size, False
        res = await self.repo.delete(
            Localization(
                location_code,
                Agency(agency_code, "")
            )
        )
        return size, res.size == 1

    async def get_full(self, entity: Literal["agency", 'localization', "sub-family", "family", "supplier"]):
        if entity == "agency":
            return await self.repo.get_agency()
        if entity == "localization":
            return await self.repo.get_localization()
        if entity == "sub-family":
            return await self.repo.get_subfamily()
        if entity == "family":
            return await self.repo.get_family()
        if entity == "supplier":
            return await self.repo.get_supplier()
        return []

    async def generate_qr_code(self, immo: Immobilization, url=CONFIG.get("DEFAULT_HOST", "")):
        url = url + "?immobilization="
        dst = io.BytesIO()
        extra = ""
        if isinstance(immo, str):
            immo = (await self.repo.get(id_immobilization=immo))[0]
        if immo.status == ImmobilizationStatus.UNKNOWN:
            if immo.sub_family is not None:
                extra = immo.sub_family.id_subfamily

        await self.qr_code.generate(
            f"{url}{immo.id_immobilization}",
            dst,
            extra
        )
        dst.seek(0)
        return dst

    async def get_images_url(self, immobilization: Immobilization, url=None):
        if self.s3_object is None:
            raise RuntimeError("no s3 object")

        if url:
            url = url.rstrip("/")
            if self.s3_object.is_minio and self.s3_object._public_host:
                url_obj = self.s3_object._public_host.split(":")
                url = url.split(":")[0]
                if url_obj[0] in ("localhost", "127.0.0.1"):
                    url = str(url) + ":" + str(url_obj[1])
                else:
                    url = self.s3_object._public_host

        _id = str(immobilization.id_immobilization)
        img_keys = await self.s3_object.list_files(
            _id
        )

        async def _(key):
            return key, await self.s3_object.get_presigned_url(_id, key, base_url=url)
        res = await asyncio.gather(*[_(k) for k in img_keys])
        return {
            ("main" if k.startswith("main") else k): v for k, v in res
        }

    async def put_file(
            self,
            immobilization: Immobilization | str | UUID,
            img: bytes,
            file_type="main",
            content_type=None,
            ext="png"
    ):
        if self.s3_object is None:
            raise RuntimeError("no s3 object")
        if isinstance(immobilization, Immobilization):
            immobilization = str(immobilization.id_immobilization)
        _id = str(immobilization)
        if file_type in ("main", "invoice"):
            remote_name = file_type + "." +ext
        else:
            remote_name  = datetime.now().strftime("%Y%m%d%H%M%S") + "." +ext
        await self.s3_object.upload(
            _id, img, remote_name, content_type=content_type
        )
        return True

    async def create_batch_immobilization(self, size=1, invoice_file=None, **imm_kwargs):
        user = imm_kwargs.pop("user", None)
        imm = Immobilization(
            **imm_kwargs, status=ImmobilizationStatus.UNKNOWN,
            created_by=user, updated_by=user
        )
        _ids = []
        for _ in range(size):
            _ids.append(await self.repo.save(imm))
            delattr(imm, "id_immobilization")
            if invoice_file is not None:
                await self.put_file(
                    _ids[-1],
                    invoice_file.read(),
                    file_type="invoice",
                    content_type=invoice_file.content_type,
                    ext=invoice_file.filename.split(".")[-1]
                )

        return _ids

    async def change_immo_id(self, immobilization: Immobilization, new_id: uuid.UUID):
        if self.s3_object is None:
            raise RuntimeError("no s3 object")

        if immobilization.status == ImmobilizationStatus.UNKNOWN:
            return False
        res = await self.repo.update_id(immobilization, new_id)

        smp = asyncio.Semaphore(50)
        tasks = []

        bucket_source = str(immobilization.id_immobilization)
        bucket_dest = str(new_id)
        async with self.s3_object.get_session() as s3:
            await self.s3_object.create_bucket(bucket_dest, _s3=s3)
            async def _(k, _smp, s3_object: StorageABC):
                async with _smp:
                    logger.info(f"uploading {k} to {bucket_dest}")
                    await s3_object.copy_between_bucket(
                        bucket_source, k,
                        bucket_dest, k,
                        _s3=s3
                    )
                    logger.info(f"finished uploading {k} to {bucket_dest}")

            for key in await self.s3_object.list_files(bucket_source, _s3=s3):
                tasks.append(
                    asyncio.create_task(
                        _(key, smp, self.s3_object)
                    )
                )
            if tasks:
                await asyncio.gather(*tasks)
            await self.s3_object.delete_bucket(bucket_source, _s3=s3)
        return res



if __name__ == '__main__':
    pass