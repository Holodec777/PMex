"""Генерирует векторные ER- и GOST-диаграммы вместе с PDF-экспортом."""

from pathlib import Path
from xml.sax.saxutils import escape

import cairosvg

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def svg_open(width: int, height: int, title: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<defs>
 <marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L10,4 L0,8 Z" fill="#344a63"/></marker>
 <style>text{{font-family:Arial,"DejaVu Sans",sans-serif;fill:#1b2a3d}} .connector{{fill:none;stroke:#344a63;stroke-width:2;marker-end:url(#arrow)}} .box{{fill:#fff;stroke:#34546f;stroke-width:2}} .decision{{fill:#edf6f3;stroke:#136a58;stroke-width:2}} .small{{font-size:13px}} .body{{font-size:15px}} .title{{font-size:20px;font-weight:bold}}</style>
</defs><rect width="100%" height="100%" fill="#f4f7fb"/>
<text x="{width / 2}" y="38" text-anchor="middle" class="title">{escape(title)}</text>'''


def svg_text(x: float, y: float, lines: list[str], size: int = 14, bold: bool = False) -> str:
    weight = "bold" if bold else "normal"
    chunks = [f'<text x="{x}" y="{y}" text-anchor="middle" font-size="{size}px" font-weight="{weight}">']
    for index, line in enumerate(lines):
        chunks.append(f'<tspan x="{x}" dy="{0 if index == 0 else 19}">{escape(line)}</tspan>')
    chunks.append("</text>")
    return "".join(chunks)


def entity(x: int, y: int, width: int, title: str, fields: list[str]) -> str:
    row_height = 22
    height = 39 + len(fields) * row_height
    output = [f'<g><rect x="{x}" y="{y}" width="{width}" height="{height}" rx="5" class="box"/>',
              f'<path d="M{x} {y + 38} H{x + width}" stroke="#34546f" stroke-width="2"/>',
              svg_text(x + width / 2, y + 26, [title], 16, True)]
    for index, field in enumerate(fields):
        output.append(f'<text x="{x + 13}" y="{y + 59 + index * row_height}" class="small">{escape(field)}</text>')
    output.append("</g>")
    return "".join(output)


def relation(points: str, one: tuple[int, int], many: tuple[int, int]) -> str:
    return (f'<path d="{points}" class="connector" marker-end="none"/> '
            f'<text x="{one[0]}" y="{one[1]}" class="small" font-weight="bold">1</text> '
            f'<text x="{many[0]}" y="{many[1]}" class="small" font-weight="bold">N</text>')


def create_er() -> str:
    parts = [svg_open(1460, 900, "Northstar Shop Desk · ER-диаграмма (3НФ)")]
    # Связи рисуются под сущностями; подписи у концов показывают кратность 1:N.
    parts.extend([
        relation("M340 160 H430", (354, 151), (410, 151)),
        relation("M355 448 H430", (368, 439), (410, 439)),
        relation("M1330 165 H1380 V720 H1330", (1340, 151), (1338, 705)),
        relation("M1170 440 V650", (1182, 456), (1182, 632)),
        relation("M1000 742 H850", (980, 733), (862, 733)),
        relation("M635 511 V650", (647, 530), (647, 632)),
        '<text x="700" y="855" text-anchor="middle" class="small" fill="#66758d">ФК включены; удаление товара, уже использованного в заказе, ограничено ON DELETE RESTRICT.</text>',
        entity(70, 105, 270, "roles", ["PK  id", "UQ  code", "UQ  title"]),
        entity(430, 105, 360, "users", ["PK  id", "UQ  login", "password_hash", "full_name", "FK  role_id → roles.id", "is_active"]),
        entity(1030, 105, 300, "customers", ["PK  id", "full_name", "phone", "email"]),
        entity(70, 385, 285, "categories", ["PK  id", "UQ  name"]),
        entity(430, 340, 420, "products", ["PK  id", "name, description", "FK  category_id → categories.id", "price > 0, stock ≥ 0", "is_digital, is_new, is_slow_moving", "image_path"]),
        entity(1020, 335, 310, "order_statuses", ["PK  id", "UQ  code", "UQ  title"]),
        entity(430, 650, 420, "order_items", ["PK  id", "FK  order_id → orders.id", "FK  product_id → products.id", "quantity > 0", "unit_price — цена на момент покупки", "UQ  (order_id, product_id)"]),
        entity(1000, 650, 330, "orders", ["PK  id", "FK  customer_id → customers.id", "FK  status_id → order_statuses.id", "created_at, delivery_date", "comment"]),
    ])
    parts.append("</svg>")
    return "".join(parts)


def process(x: int, y: int, width: int, height: int, lines: list[str], color: str = "#34546f") -> str:
    return (f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="2" fill="#fff" stroke="{color}" stroke-width="2"/>'
            + svg_text(x + width / 2, y + height / 2 - (len(lines) - 1) * 9, lines, 14))


def decision(cx: int, cy: int, width: int, height: int, lines: list[str]) -> str:
    points = f"{cx},{cy-height/2} {cx+width/2},{cy} {cx},{cy+height/2} {cx-width/2},{cy}"
    return f'<polygon points="{points}" class="decision"/>' + svg_text(cx, cy - (len(lines) - 1) * 9, lines, 14)


def input_output(x: int, y: int, width: int, height: int, lines: list[str]) -> str:
    skew = 22
    points = f"{x+skew},{y} {x+width},{y} {x+width-skew},{y+height} {x},{y+height}"
    return f'<polygon points="{points}" fill="#fff" stroke="#34546f" stroke-width="2"/>' + svg_text(x + width / 2, y + height / 2 - (len(lines)-1)*9, lines, 14)


def terminal(cx: int, cy: int, rx: int, ry: int, label: str) -> str:
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="#e8f3ef" stroke="#136a58" stroke-width="2"/>' + svg_text(cx, cy + 5, [label], 15, True)


def arrow(path: str, label: str | None = None, label_x: int = 0, label_y: int = 0) -> str:
    text = f'<text x="{label_x}" y="{label_y}" class="small" font-weight="bold">{escape(label)}</text>' if label else ""
    return f'<path d="{path}" class="connector"/>' + text


def create_auth_flow() -> str:
    parts = [svg_open(1120, 1260, "Алгоритм авторизации · ГОСТ 19.701-90")]
    # Ошибки входа и пароля обрабатываются одинаково, поэтому сходятся в один блок.
    parts.extend([
        arrow("M470 103 V128"),
        arrow("M470 218 V275", "Нет", 485, 250),
        arrow("M320 173 H170 V255", "Да", 235, 158),
        arrow("M470 355 V410"),
        arrow("M470 484 V530"),
        arrow("M620 575 H700 V690 H770", "Нет", 660, 562),
        arrow("M470 620 V660", "Да", 485, 642),
        arrow("M470 746 V790"),
        arrow("M620 835 H740 V750 H770", "Нет", 660, 822),
        arrow("M470 880 V915", "Да", 485, 900),
        arrow("M470 989 V1015"),
        arrow("M470 1091 V1110"),
        arrow("M170 333 V1053 H300"),
        process(55, 255, 230, 78, ["Создать гостевую", "сессию (роль Guest)"], "#136a58"),
        input_output(290, 275, 360, 80, ["Ввести логин и пароль", "Пароль скрыт в форме"]),
        process(350, 410, 240, 74, ["Найти активную учётную", "запись в SQLite"]),
        process(335, 660, 270, 86, ["Проверить пароль", "PBKDF2 + compare_digest"]),
        process(340, 915, 260, 74, ["Создать CurrentUser", "и назначить роль"]),
        process(300, 1015, 340, 76, ["Открыть каталог с правами", "выбранной роли"], "#136a58"),
        terminal(470, 1130, 105, 20, "Работа приложения"),
        decision(470, 173, 300, 90, ["Войти как гость?"]),
        decision(470, 575, 300, 90, ["Аккаунт найден?"]),
        decision(470, 835, 300, 90, ["Пароль верен?"]),
        process(770, 665, 310, 112, ["Показать общую ошибку", "очистить пароль", "оставить форму открытой"], "#a9343e"),
        terminal(470, 83, 70, 20, "Начало"),
        '<text x="560" y="1200" text-anchor="middle" class="small" fill="#66758d">ГОСТ 19.701-90 · Овал — начало/завершение · Параллелограмм — ввод/вывод</text>',
        '<text x="560" y="1223" text-anchor="middle" class="small" fill="#66758d">Ромб — решение · Прямоугольник — процесс · Стрелки показывают ход алгоритма</text>',
    ])
    parts.append("</svg>")
    return "".join(parts)


def write_pair(name: str, content: str) -> None:
    svg_path = DOCS / f"{name}.svg"
    pdf_path = DOCS / f"{name}.pdf"
    svg_path.write_text(content, encoding="utf-8")
    cairosvg.svg2pdf(bytestring=content.encode("utf-8"), write_to=str(pdf_path))


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    write_pair("er-diagram", create_er())
    write_pair("auth-flow-gost", create_auth_flow())
    print("Созданы docs/er-diagram.pdf и docs/auth-flow-gost.pdf")


if __name__ == "__main__":
    main()
