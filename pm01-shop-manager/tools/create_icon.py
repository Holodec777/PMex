"""Создаёт простой векторный значок приложения средствами Pillow."""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    image = Image.new("RGBA", (256, 256), "#12243a")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((22, 22, 234, 234), radius=48, fill="#136a58")
    draw.rounded_rectangle((54, 68, 202, 202), radius=18, fill="#ffffff")
    draw.polygon(((48, 82), (128, 35), (208, 82)), fill="#73dbc0")
    draw.rectangle((72, 111, 112, 151), fill="#cdeee5")
    draw.rectangle((145, 111, 185, 151), fill="#cdeee5")
    draw.rounded_rectangle((111, 146, 145, 202), radius=6, fill="#136a58")
    image.save(ASSETS / "shopdesk.png")
    image.save(ASSETS / "shopdesk.ico", sizes=[(256, 256), (64, 64), (32, 32), (16, 16)])
    print("Значок создан в assets/shopdesk.png и assets/shopdesk.ico")


if __name__ == "__main__":
    main()
