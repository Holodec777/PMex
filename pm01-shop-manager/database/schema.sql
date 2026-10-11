PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    login TEXT NOT NULL UNIQUE CHECK (length(login) BETWEEN 3 AND 64),
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL CHECK (length(trim(full_name)) BETWEEN 2 AND 120),
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE CHECK (length(trim(name)) BETWEEN 1 AND 80)
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 120),
    description TEXT NOT NULL DEFAULT '',
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    price REAL NOT NULL CHECK (price > 0),
    stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    is_digital INTEGER NOT NULL DEFAULT 0 CHECK (is_digital IN (0, 1)),
    is_new INTEGER NOT NULL DEFAULT 0 CHECK (is_new IN (0, 1)),
    is_slow_moving INTEGER NOT NULL DEFAULT 0 CHECK (is_slow_moving IN (0, 1)),
    image_path TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL CHECK (length(trim(full_name)) BETWEEN 2 AND 120),
    phone TEXT NOT NULL CHECK (length(trim(phone)) BETWEEN 5 AND 32),
    email TEXT
);

CREATE TABLE IF NOT EXISTS order_statuses (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    status_id INTEGER NOT NULL REFERENCES order_statuses(id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    delivery_date TEXT NOT NULL,
    comment TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price REAL NOT NULL CHECK (unit_price > 0),
    UNIQUE (order_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_orders_delivery ON orders(delivery_date);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id);

INSERT OR IGNORE INTO roles (code, title) VALUES
    ('seller', 'Продавец'), ('manager', 'Менеджер'), ('admin', 'Администратор');

INSERT OR IGNORE INTO order_statuses (code, title) VALUES
    ('new', 'Новый'), ('confirmed', 'Подтверждён'), ('ready', 'Готов к выдаче'),
    ('issued', 'Выдан'), ('cancelled', 'Отменён');

INSERT OR IGNORE INTO categories (name) VALUES
    ('Ноутбуки'), ('Периферия'), ('Накопители'), ('Программное обеспечение');
