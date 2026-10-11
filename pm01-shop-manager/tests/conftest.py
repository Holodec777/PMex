import pytest

from app.database import Database
from app.repository import Repository


@pytest.fixture
def repository(tmp_path):
    database = Database(tmp_path / "test-shop.db")
    database.initialize(seed_demo=False)
    repo = Repository(database)
    yield repo
    database.close()


@pytest.fixture
def category_id(repository):
    return repository.categories()[0]["id"]


def create_product(repository, category_id, **overrides):
    values = {
        "name": "Тестовый товар",
        "description": "Для проверки поиска",
        "category": next(row["name"] for row in repository.categories() if row["id"] == category_id),
        "price": "1250",
        "stock": "4",
        "is_digital": False,
        "is_new": False,
        "is_slow_moving": False,
        "image_path": None,
    }
    values.update(overrides)
    return repository.save_product(values)
