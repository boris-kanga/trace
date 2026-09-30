from abc import ABC, abstractmethod

import io
from pathlib import Path


class QrCodeABC(ABC):
    padding = (10, 10)
    @classmethod
    @abstractmethod
    async def generate(cls, content, dest: str | Path | io.BytesIO, extra_content: str=""):
        pass

    @classmethod
    @abstractmethod
    async def add_extra_to_qrcode(cls, img, content: str, dest: str | Path | io.BytesIO):
        pass