"""Проверки данных и SQL-запросы предметной области."""

import csv
import math
import sqlite3
from datetime import date
from pathlib import Path

from app.auth import UserSession, verify_password
from app.database import Database

SORTS = {
    "По названию А—Я": "p.name COLLATE NOCASE ASC",
    "Цена: по возрастанию": "p.price ASC, p.name COLLATE NOCASE ASC",
    "Цена: по убыванию": "p.price DESC, p.name COLLATE NOCASE ASC",
    "Остаток: сначала больше": "p.stock DESC, p.name COLLATE NOCASE ASC",
}
CSV_FIELDS = {
    "name", "description", "category", "price", "stock",
    "is_digital", "is_new", "is_slow_moving",
}


class ProductInUseError(ValueError):
    """Товар нельзя удалить, пока он встречается в строках заказов."""


class Repository:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.connection = database.connection

    def authenticate(self, login: str, password: str) -> UserSession | None:
        row = self.connection.execute(
            """SELECT u.id, u.login, u.password_hash, u.full_name, r.code, r.title
               FROM users u JOIN roles r ON r.id = u.role_id
               WHERE u.login = ? AND u.is_active = 1""",
            (login.strip(),),
        ).fetchone()
        if not row or not verify_password(password, row["password_hash"]):
            return None
        return UserSession(row["id"], row["login"], row["full_name"], row["code"], row["title"])

    def categories(self) -> list[sqlite3.Row]:
        return self.connection.execute("SELECT id, name FROM categories ORDER BY name COLLATE NOCASE").fetchall()

    def statuses(self) -> list[sqlite3.Row]:
        return self.connection.execute("SELECT id, code, title FROM order_statuses ORDER BY id").fetchall()

    def products(
        self, search: str = "", category_id: int | None = None,
        sort: str = "По названию А—Я", only_in_stock: bool = False,
    ) -> list[sqlite3.Row]:
        clauses: list[str] = []
        values: list[object] = []
        if search.strip():
            pattern = f"%{search.strip()}%"
            clauses.append("(p.name LIKE ? COLLATE NOCASE OR p.description LIKE ? COLLATE NOCASE)")
            values.extend((pattern, pattern))
        if category_id is not None:
            clauses.append("p.category_id = ?")
            values.append(category_id)
        if only_in_stock:
            clauses.append("p.stock > 0")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        order_by = SORTS.get(sort, SORTS["По названию А—Я"])
        return self.connection.execute(
            """SELECT p.*, c.name AS category_name
               FROM products p JOIN categories c ON c.id = p.category_id"""
            + where + " ORDER BY " + order_by,
            values,
        ).fetchall()

    def normalize_product(self, data: dict) -> tuple:
        category_ids = {row["name"]: row["id"] for row in self.categories()}
        return self._normalize_product_row(data, category_ids)

    @staticmethod
    def _normalize_product_row(data: dict, category_ids: dict[str, int]) -> tuple:
        name = str(data.get("name", "")).strip()
        description = str(data.get("description", "")).strip()
        category = str(data.get("category", "")).strip()
        try:
            price = float(str(data.get("price", "")).replace(" ", "").replace(",", "."))
            stock = int(str(data.get("stock", "")))
        except (TypeError, ValueError):
            raise ValueError("Цена должна быть числом, а остаток — целым числом") from None
        if not name or len(name) > 120:
            raise ValueError("Название обязательно и должно быть не длиннее 120 символов")
        if len(description) > 2000:
            raise ValueError("Описание должно быть не длиннее 2000 символов")
        if not math.isfinite(price) or price <= 0:
            raise ValueError("Цена должна быть больше нуля")
        if stock < 0:
            raise ValueError("Остаток не может быть отрицательным")
        if category not in category_ids:
            raise ValueError("Выберите существующую категорию")
        return (
            name, description, category_ids[category], price, stock,
            int(bool(data.get("is_digital"))), int(bool(data.get("is_new"))),
            int(bool(data.get("is_slow_moving"))), data.get("image_path"),
        )

    def save_product(self, data: dict, product_id: int | None = None) -> int:
        values = self.normalize_product(data)
        with self.database.transaction() as connection:
            if product_id is None:
                cursor = connection.execute(
                    """INSERT INTO products
                       (name, description, category_id, price, stock, is_digital, is_new, is_slow_moving, image_path)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    values,
                )
                return int(cursor.lastrowid)
            exists = connection.execute("SELECT 1 FROM products WHERE id = ?", (product_id,)).fetchone()
            if not exists:
                raise ValueError("Товар уже удалён")
            connection.execute(
                """UPDATE products SET name=?, description=?, category_id=?, price=?, stock=?,
                   is_digital=?, is_new=?, is_slow_moving=?, image_path=? WHERE id=?""",
                values + (product_id,),
            )
        return product_id

    def delete_product(self, product_id: int) -> None:
        references = self.connection.execute(
            "SELECT COUNT(*) FROM order_items WHERE product_id = ?", (product_id,)
        ).fetchone()[0]
        if references:
            raise ProductInUseError("Товар есть в заказах; удаление заблокировано")
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM products WHERE id = ?", (product_id,))

    def orders(self) -> list[sqlite3.Row]:
        return self.connection.execute(
            """SELECT o.id, o.created_at, o.delivery_date, o.comment,
                      c.full_name AS customer_name, c.phone AS customer_phone, c.email AS customer_email,
                      s.title AS status, s.code AS status_code,
                      COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS total,
                      GROUP_CONCAT(p.name || ' × ' || oi.quantity, ', ') AS items
               FROM orders o JOIN customers c ON c.id = o.customer_id
               JOIN order_statuses s ON s.id = o.status_id
               LEFT JOIN order_items oi ON oi.order_id = o.id
               LEFT JOIN products p ON p.id = oi.product_id
               GROUP BY o.id ORDER BY o.id DESC"""
        ).fetchall()

    def update_order(self, order_id: int, status: str, delivery_date: str) -> None:
        try:
            parsed_date = date.fromisoformat(delivery_date.strip())
        except ValueError:
            raise ValueError("Дата доставки должна быть в формате ГГГГ-ММ-ДД") from None
        if not status.strip():
            raise ValueError("Статус не может быть пустым")
        with self.database.transaction() as connection:
            status_row = connection.execute(
                "SELECT id FROM order_statuses WHERE title = ?", (status.strip(),)
            ).fetchone()
            if not status_row:
                raise ValueError("Выберите статус из списка")
            cursor = connection.execute(
                "UPDATE orders SET status_id = ?, delivery_date = ? WHERE id = ?",
                (status_row["id"], parsed_date.isoformat(), order_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Заказ не найден")

    def import_products_csv(self, path: str | Path) -> int:
        with Path(path).open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            headers = set(reader.fieldnames or [])
            missing = CSV_FIELDS - headers
            if missing:
                raise ValueError("В CSV не хватает столбцов: " + ", ".join(sorted(missing)))
            source_rows = list(reader)
        with self.database.transaction() as connection:
            for row_number, row in enumerate(source_rows, start=2):
                category = str(row.get("category", "")).strip()
                if not category or len(category) > 80:
                    raise ValueError(f"Строка {row_number}: название категории обязательно (до 80 символов)")
                connection.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (category,))
            category_ids = {row["name"]: row["id"] for row in self.categories()}
            normalized = []
            for row_number, row in enumerate(source_rows, start=2):
                try:
                    parsed = dict(row)
                    for field in ("is_digital", "is_new", "is_slow_moving"):
                        parsed[field] = str(parsed.get(field, "")).strip().lower() in {"1", "true", "yes", "да"}
                    parsed["image_path"] = None
                    normalized.append(self._normalize_product_row(parsed, category_ids))
                except ValueError as error:
                    raise ValueError(f"Строка {row_number}: {error}") from None
            connection.executemany(
                """INSERT INTO products
                   (name, description, category_id, price, stock, is_digital, is_new, is_slow_moving, image_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                normalized,
            )
        return len(normalized)
