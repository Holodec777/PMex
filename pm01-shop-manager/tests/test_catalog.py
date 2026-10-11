import pytest
from PIL import Image

from tests.conftest import create_product
from app.media import copy_uploaded_image, validate_image


def test_search_stock_filter_and_sort(repository, category_id):
    create_product(repository, category_id, name="Alpha keyboard", description="quiet switches", price="2000", stock="0")
    create_product(repository, category_id, name="Beta mouse", description="wireless pointing device", price="1000", stock="5")

    assert [row["name"] for row in repository.products(search="wireless")] == ["Beta mouse"]
    assert [row["name"] for row in repository.products(only_in_stock=True)] == ["Beta mouse"]
    assert [row["name"] for row in repository.products(sort="Цена: по возрастанию")] == ["Beta mouse", "Alpha keyboard"]


def test_product_validation_and_update(repository, category_id):
    product_id = create_product(repository, category_id, price="1 250,50", is_new=True)
    row = repository.connection.execute("SELECT price, is_new FROM products WHERE id=?", (product_id,)).fetchone()
    assert row["price"] == 1250.5
    assert row["is_new"] == 1
    with pytest.raises(ValueError, match="больше нуля"):
        create_product(repository, category_id, price="0")
    with pytest.raises(ValueError, match="отрицательным"):
        create_product(repository, category_id, stock="-1")


def test_product_delete_is_blocked_when_order_references_it(repository, category_id):
    product_id = create_product(repository, category_id)
    customer = repository.connection.execute(
        "INSERT INTO customers (full_name, phone) VALUES ('Тестовый клиент', '+7 900 000-00-00')"
    )
    status_id = repository.connection.execute("SELECT id FROM order_statuses WHERE code='new'").fetchone()[0]
    order = repository.connection.execute(
        "INSERT INTO orders (customer_id, status_id, delivery_date) VALUES (?, ?, '2030-01-01')",
        (customer.lastrowid, status_id),
    )
    repository.connection.execute(
        "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, 1, 1250)",
        (order.lastrowid, product_id),
    )
    repository.connection.commit()
    with pytest.raises(ValueError, match="удаление заблокировано"):
        repository.delete_product(product_id)


def test_csv_import_is_atomic(repository, tmp_path):
    csv_path = tmp_path / "products.csv"
    csv_path.write_text(
        "name,description,category,price,stock,is_digital,is_new,is_slow_moving\n"
        "Импорт 1,Проверка,Накопители,500,2,false,true,false\n"
        "Импорт 2,Ошибочная строка,Новая категория,не-цена,2,false,false,false\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Строка 3"):
        repository.import_products_csv(csv_path)
    assert repository.products(search="Импорт")==[]
    assert "Новая категория" not in {row["name"] for row in repository.categories()}


def test_csv_import_creates_categories(repository, tmp_path):
    csv_path = tmp_path / "new-category.csv"
    csv_path.write_text(
        "name,description,category,price,stock,is_digital,is_new,is_slow_moving\n"
        "Планшет,Тест,Планшеты,8500,3,false,true,false\n",
        encoding="utf-8",
    )
    assert repository.import_products_csv(csv_path) == 1
    assert repository.products(search="Планшет")[0]["category_name"] == "Планшеты"


def test_image_copy_and_size_limit(tmp_path):
    source = tmp_path / "cover.png"
    Image.new("RGB", (4, 4), "#136a58").save(source)
    relative = copy_uploaded_image(source, tmp_path / "project")
    assert (tmp_path / "project" / relative).is_file()
    oversized = tmp_path / "large.png"
    oversized.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match="2 МБ"):
        validate_image(oversized)
