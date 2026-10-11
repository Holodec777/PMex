"""SQLite-хранилище, схема и демонстрационный набор данных."""

import os
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Iterator

from app.auth import hash_password

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "shop.db"


class Database:
    def __init__(self, path: str | Path | None = None) -> None:
        configured = path or os.getenv("SHOP_DB_PATH") or DEFAULT_DB_PATH
        self.path = Path(configured).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, timeout=10, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")

    def initialize(self, seed_demo: bool = True) -> None:
        schema_path = PROJECT_ROOT / "database" / "schema.sql"
        self.connection.executescript(schema_path.read_text(encoding="utf-8"))
        if seed_demo:
            self.seed_demo()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            with self.connection:
                yield self.connection
        except sqlite3.Error:
            raise

    def seed_demo(self) -> None:
        with self.transaction() as connection:
            existing = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            if existing:
                return
            role_ids = {
                row["code"]: row["id"]
                for row in connection.execute("SELECT id, code FROM roles").fetchall()
            }
            accounts = [
                ("seller", "seller123", "Анна Соколова", "seller"),
                ("manager", "manager123", "Илья Волков", "manager"),
                ("admin", "admin123", "Мария Орлова", "admin"),
            ]
            for login, password, full_name, role in accounts:
                connection.execute(
                    "INSERT INTO users (login, password_hash, full_name, role_id) VALUES (?, ?, ?, ?)",
                    (login, hash_password(password), full_name, role_ids[role]),
                )

            category_ids = {
                row["name"]: row["id"]
                for row in connection.execute("SELECT id, name FROM categories").fetchall()
            }
            products = [
                ("Ноутбук Northstar 14", "Лёгкий ноутбук для работы и учёбы, экран 14 дюймов.", "Ноутбуки", 74990, 8, 0, 1, 0),
                ("Ноутбук Northstar Pro", "Модель с увеличенной памятью и ярким экраном.", "Ноутбуки", 119990, 3, 0, 1, 0),
                ("Компактная клавиатура K-68", "Механическая клавиатура с тихими переключателями.", "Периферия", 6490, 12, 0, 0, 0),
                ("Мышь Orbit Silent", "Беспроводная мышь с бесшумными кнопками.", "Периферия", 2190, 0, 0, 0, 0),
                ("Монитор Aurora 27", "IPS-монитор с тонкими рамками и регулировкой высоты.", "Периферия", 28990, 5, 0, 0, 0),
                ("Наушники Echo Studio", "Закрытые наушники с мягкими амбушюрами.", "Периферия", 8990, 2, 0, 0, 1),
                ("SSD BluePeak 1 ТБ", "Внутренний NVMe-накопитель для быстрой загрузки.", "Накопители", 7290, 16, 0, 0, 0),
                ("Флеш-накопитель 128 ГБ", "Компактный накопитель с металлическим корпусом.", "Накопители", 990, 0, 0, 0, 1),
                ("Облачный офис — лицензия", "Цифровая лицензия на 12 месяцев. Код выдаётся по email.", "Программное обеспечение", 3990, 999, 1, 1, 0),
                ("Редактор Studio — лицензия", "Цифровой ключ для одного рабочего места.", "Программное обеспечение", 5990, 999, 1, 0, 0),
                ("Уценённая док-станция", "Исправный товар с повреждённой упаковкой.", "Периферия", 3490, 1, 0, 0, 1),
                ("Wi-Fi адаптер Nano", "Компактный адаптер предыдущего поколения.", "Периферия", 890, 4, 0, 0, 1),
            ]
            for name, description, category, price, stock, digital, is_new, slow in products:
                connection.execute(
                    """INSERT INTO products
                       (name, description, category_id, price, stock, is_digital, is_new, is_slow_moving)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (name, description, category_ids[category], price, stock, digital, is_new, slow),
                )

            customers = [
                ("Елена Смирнова", "+7 900 111-22-33", "elena@example.test"),
                ("Дмитрий Кузнецов", "+7 900 222-33-44", "dmitry@example.test"),
                ("Полина Иванова", "+7 900 333-44-55", "polina@example.test"),
                ("Алексей Морозов", "+7 900 444-55-66", "alex@example.test"),
                ("Ольга Фёдорова", "+7 900 555-66-77", "olga@example.test"),
            ]
            connection.executemany(
                "INSERT INTO customers (full_name, phone, email) VALUES (?, ?, ?)", customers
            )
            status_ids = {
                row["code"]: row["id"]
                for row in connection.execute("SELECT id, code FROM order_statuses").fetchall()
            }
            today = date.today()
            sample_orders = [
                (1, "confirmed", -4, 2, "Демо-заказ с просроченной доставкой"),
                (2, "new", 0, 3, "Самовывоз из магазина"),
                (3, "ready", 1, 4, "Позвонить перед выдачей"),
                (4, "issued", -8, 1, "Выдан клиенту"),
                (5, "confirmed", 3, 5, "Доставка курьером"),
                (1, "cancelled", -2, 6, "Отменён клиентом"),
                (3, "new", 2, 7, "Ожидает подтверждения"),
                (5, "confirmed", -1, 8, "Просрочен: связаться с клиентом"),
            ]
            for customer_id, status_code, due_offset, product_id, comment in sample_orders:
                cursor = connection.execute(
                    """INSERT INTO orders (customer_id, status_id, created_at, delivery_date, comment)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        customer_id,
                        status_ids[status_code],
                        (today - timedelta(days=5)).isoformat(),
                        (today + timedelta(days=due_offset)).isoformat(),
                        comment,
                    ),
                )
                connection.execute(
                    "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
                    (cursor.lastrowid, product_id, 1 + cursor.lastrowid % 2, products[product_id - 1][3]),
                )

    def close(self) -> None:
        self.connection.close()
