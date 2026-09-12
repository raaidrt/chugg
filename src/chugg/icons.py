"""Regenerate the original installation mark at its existing sizes."""

from io import BytesIO

import resvg_py
from PIL import Image

from chugg.build import ROOT


def build_icons() -> None:
    render = resvg_py.svg_to_bytes
    public = ROOT / "public"
    (public / "icons").mkdir(exist_ok=True)
    mark = (public / "icon.svg").read_text()
    for size, filename in [
        (192, "icons/icon-192.png"),
        (512, "icons/icon-512.png"),
        (180, "apple-touch-icon.png"),
    ]:
        (public / filename).write_bytes(render(svg_string=mark, width=size, height=size))
    inset = Image.open(BytesIO(render(svg_string=mark, width=360, height=360))).convert("RGBA")
    image = Image.new("RGBA", (512, 512), "#244a36")
    image.alpha_composite(inset, (76, 76))
    image.save(public / "icons/icon-maskable-512.png")
    print("Generated all four installation icons.")
