import io
import asyncio
from pathlib import Path

import qrcode
from qrcode.image.pil import PilImage
from PIL import Image, ImageDraw, ImageFont

from src.core.logger import get_logger
from src.domain.interfaces.qrcode_generator_abc import QrCodeABC


logger = get_logger(__name__)


class QrCode(QrCodeABC):
    padding = (80, 50)
    @classmethod
    async def generate(cls, content, dest: str | Path | io.BytesIO, extra_content: str=""):
        auto_save = not bool(extra_content)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=5,
            border=0 if not auto_save else 4,
        )
        def _(_qr, _content, _dest):
            _qr.add_data(_content)
            _qr.make(fit=True)
            img = _qr.make_image()  #.convert('RGB')
            if auto_save:
                img.save(_dest)
            return img

        image = await asyncio.to_thread(_, qr, content, dest)
        if extra_content:
            await cls.add_extra_to_qrcode(image, extra_content, dest)

    @classmethod
    async def add_extra_to_qrcode(cls, img: PilImage, content: str, dest: str | Path | io.BytesIO):
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except IOError:
            font = ImageFont.load_default()

        img: Image = getattr(img, "_img", img)

        new_width, new_height = img.width + cls.padding[0]*2, img.width + int(cls.padding[1]*2.5)
        clone = Image.new("RGB", (
                new_width,
                new_height
            ), color="white"
        )

        img = img.convert("RGB")
        clone.paste(img, (cls.padding[0], cls.padding[1]))
        draw = ImageDraw.Draw(clone)

        text_bbox = draw.textbbox((0, 0), content, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        text_x = (new_width - text_width) // 2
        text_y = img.width + cls.padding[1] * 1.25 + text_height // 2
        draw.text((text_x, text_y), content, fill="black", font=font)

        clone.save(dest, format="PNG")


if __name__ == '__main__':
    asyncio.run(
        QrCode.generate("https://test/ldofhhdhhdhhd.logkjjdjjdjhhhhdhhdhhdhhhdhhhd", "test.png", "ok")
    )
