import pytest

from tests.conftest import create_product


def test_order_update_is_saved(repository, category_id):
    product_id = create_product(repository, category_id)
    customer = repository.connection.execute(
        "INSERT INTO customers (full_name, phone, email) VALUES ('Клиент Тестов', '+7 900 000-00-00', 'test@example.test')"
    )
    status_id = repository.connection.execute("SELECT id FROM order_statuses WHERE code='new'").fetchone()[0]
    order = repository.connection.execute(
        "INSERT INTO orders (customer_id, status_id, delivery_date) VALUES (?, ?, '2030-01-01')",
        (customer.lastrowid, status_id),
    )
    repository.connection.execute(
        "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, 2, 1250)",
        (order.lastrowid, product_id),
    )
    repository.connection.commit()

    repository.update_order(order.lastrowid, "Подтверждён", "2030-01-08")
    saved = repository.orders()[0]
    assert saved["status"] == "Подтверждён"
    assert saved["delivery_date"] == "2030-01-08"
    assert saved["customer_name"] == "Клиент Тестов"
    assert saved["total"] == 2500


def test_order_date_and_status_are_validated(repository):
    with pytest.raises(ValueError, match="формате"):
        repository.update_order(1, "Новый", "08.01.2030")
