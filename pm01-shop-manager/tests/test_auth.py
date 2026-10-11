from app.auth import UserSession, can, guest_session, hash_password, verify_password


def test_password_hash_and_login(repository):
    role_id = repository.connection.execute("SELECT id FROM roles WHERE code='manager'").fetchone()[0]
    password_hash = hash_password("secure-pass-12")
    repository.connection.execute(
        "INSERT INTO users (login, password_hash, full_name, role_id) VALUES (?, ?, ?, ?)",
        ("manager1", password_hash, "Ирина Тестова", role_id),
    )
    repository.connection.commit()

    user = repository.authenticate("manager1", "secure-pass-12")
    assert user is not None
    assert user.full_name == "Ирина Тестова"
    assert user.role == "manager"
    assert repository.authenticate("manager1", "wrong-password") is None
    assert verify_password("secure-pass-12", password_hash)
    assert password_hash != "secure-pass-12"


def test_guest_has_catalog_but_no_filters_or_orders():
    guest = guest_session()
    assert not can(guest, "catalog_filters")
    assert not can(guest, "orders")
    assert not can(guest, "product_write")


def test_roles_get_only_the_expected_permissions():
    seller = UserSession(1, "seller", "Продавец", "seller", "Продавец")
    manager = UserSession(2, "manager", "Менеджер", "manager", "Менеджер")
    admin = UserSession(3, "admin", "Админ", "admin", "Администратор")
    assert can(seller, "catalog_filters") and not can(seller, "orders")
    assert can(manager, "catalog_filters") and can(manager, "orders")
    assert not can(manager, "product_write")
    assert can(admin, "product_write") and can(admin, "product_delete")
