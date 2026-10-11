"""Проверка и безопасное копирование обложек товаров."""

import shutil
import uuid
from pathlib import Path

from PIL import Image

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MAX_IMAGE_BYTES = 2 * 1024 * 1024


def validate_image(path: str | Path) -> Path:
    image_path = Path(path)
    try:
        size = image_path.stat().st_size
    except OSError as error:
        raise ValueError(f"Файл недоступен: {error}") from None
    if image_path.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Выберите изображение PNG, JPG, GIF или WEBP")
    if size > MAX_IMAGE_BYTES:
        raise ValueError("Размер обложки не должен превышать 2 МБ")
    try:
        with Image.open(image_path) as opened:
            opened.verify()
    except (OSError, ValueError):
        raise ValueError("Файл не является корректным изображением") from None
    return image_path


def copy_uploaded_image(path: str | Path, project_root: str | Path) -> str:
    image_path = validate_image(path)
    upload_dir = Path(project_root) / "assets" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / f"{uuid.uuid4().hex}{image_path.suffix.lower()}"
    shutil.copy2(image_path, target)
    return target.relative_to(Path(project_root)).as_posix()
