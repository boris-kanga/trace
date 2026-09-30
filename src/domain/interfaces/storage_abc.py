from abc import ABC, abstractmethod
from contextlib import asynccontextmanager


class StorageABC(ABC):

    is_minio = True
    _public_host = None

    @abstractmethod
    async def copy_between_bucket(self, bucket_source, key_source, bucket_dest, key_dest, _s3=None):
        pass

    @abstractmethod
    @asynccontextmanager
    async def get_session(self):
        pass

    @abstractmethod
    async def upload(self, bucket, file_source, remote_name, content_type=None, public=False, retrieve_url=False, **_):
        pass

    @abstractmethod
    async def delete_all_storage(self, **_):
        pass

    @abstractmethod
    async def file_exists(self, bucket_name, filename, **_):
        pass

    @abstractmethod
    async def create_bucket(self, bucket_name, **_):
        pass

    @abstractmethod
    async def download(self, bucket, remote_name, local_path, **_):
        pass

    @abstractmethod
    async def delete(self, bucket, remote_name, **_):
        pass

    @abstractmethod
    async def delete_bucket(self, bucket_name, **_):
        pass

    @abstractmethod
    async def get_presigned_url(self, bucket, remote_name, expires=3600, base_url=None, **_):
        pass

    @abstractmethod
    async def list_files(self, bucket, prefix="", **_):
        pass
