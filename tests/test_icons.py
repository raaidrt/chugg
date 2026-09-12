import shutil
from pathlib import Path

from PIL import Image
from pytest import MonkeyPatch

from chugg import icons


def test_icon_regeneration_preserves_dimensions_and_maskable_padding(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    (tmp_path / "public").mkdir()
    shutil.copyfile(icons.ROOT / "public/icon.svg", tmp_path / "public/icon.svg")
    monkeypatch.setattr(icons, "ROOT", tmp_path)
    icons.build_icons()
    for name, size in [
        ("apple-touch-icon.png", 180),
        ("icons/icon-192.png", 192),
        ("icons/icon-512.png", 512),
        ("icons/icon-maskable-512.png", 512),
    ]:
        with Image.open(tmp_path / "public" / name) as image:
            assert image.size == (size, size)
    with Image.open(tmp_path / "public/icons/icon-maskable-512.png") as mask:
        assert mask.getpixel((0, 0)) == (36, 74, 54, 255)
