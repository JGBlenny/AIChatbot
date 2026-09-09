"""W9-4：解壓縮炸彈防線——PIL.Image.MAX_IMAGE_PIXELS 行程級上限。

受測物：app.py 模組匯入層級設定的 `Image.MAX_IMAGE_PIXELS = IMAGE_MAX_PIXELS`（40_000_000），
照片線（services.s3_image_service.downscale_image）與文件頁圖線共用同一道防線。

⚠️ Pillow 語義：像素數 > MAX_IMAGE_PIXELS 只會 warn（DecompressionBombWarning），
   > 2×MAX_IMAGE_PIXELS 才會 raise DecompressionBombError——本檔的反對照案例
   構造 20000×20000（4 億像素）> 2×40M(=80M)，確保會 raise 而非只 warn。
"""
import io
import struct
import zlib

import pytest
from PIL import Image


def _make_png_header_only(width: int, height: int) -> bytes:
    """組一個只有合法 IHDR 宣告寬高的 PNG bytes，⛔ 不實際配置像素資料。

    後續 chunk（IDAT/IEND）內容可以是隨便的占位資料——PIL 的解壓縮炸彈檢查發生在
    `Image.open()` 對 IHDR 解析之後、像素資料解碼之前（lazy 階段），因此不需要
    真的產生 4 億像素的像素資料就能觸發 DecompressionBombError。
    """
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    # IHDR: width, height, bit depth=8, color type=2(RGB), compression=0, filter=0, interlace=0
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    # 最小合法 IDAT（一個空的 zlib stream 即可讓 open() 解析出 IHDR；不需要真的可解碼完整像素）
    idat_data = zlib.compress(b"")
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat_data) + chunk(b"IEND", b"")


def _huge_png_bytes() -> bytes:
    # 20000 x 20000 = 4 億像素 > 2 x 40_000_000（80,000,000）⇒ 必觸發 raise 而非 warn
    return _make_png_header_only(20000, 20000)


def test_max_image_pixels_set_after_app_import():
    """(a) 匯入 app 後 Image.MAX_IMAGE_PIXELS == 40_000_000。"""
    import app  # noqa: F401  匯入即觸發 app.py 模組層級的賦值

    assert Image.MAX_IMAGE_PIXELS == 40_000_000
    assert app.IMAGE_MAX_PIXELS == 40_000_000


def test_normal_small_image_still_opens():
    """(b) 正對照：小圖仍可正常開啟（防線不誤殺合法輸入）。"""
    import app  # noqa: F401

    buf = io.BytesIO()
    Image.new("RGB", (100, 100), color=(255, 0, 0)).save(buf, format="PNG")
    buf.seek(0)

    img = Image.open(buf)
    img.load()
    assert img.size == (100, 100)


def test_huge_declared_png_raises_decompression_bomb_error():
    """(c) 反對照：手工組的 PNG 標頭宣告 20000x20000（4 億像素）⇒ open()/load() 拋
    PIL.Image.DecompressionBombError（不是只 warn，因為超過 2x cap）。"""
    import app  # noqa: F401

    data = _huge_png_bytes()

    with pytest.raises(Image.DecompressionBombError):
        img = Image.open(io.BytesIO(data))
        img.load()


def test_downscale_image_rejects_huge_png_too():
    """(d) 同一張走 services.s3_image_service.downscale_image 也拋，證明照片線受保護。"""
    import app  # noqa: F401
    from services.s3_image_service import downscale_image

    data = _huge_png_bytes()

    with pytest.raises(Image.DecompressionBombError):
        downscale_image(data)
