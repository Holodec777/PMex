"""Рабочий интерфейс каталога, заказов и форм администратора."""

from datetime import date
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from app.auth import UserSession, can, guest_session
from app.database import PROJECT_ROOT
from app.media import copy_uploaded_image, validate_image
from app.repository import ProductInUseError, Repository, SORTS

BG = "#edf2f8"
INK = "#17253b"
MUTED = "#66758d"
ACCENT = "#136a58"
ACCENT_DARK = "#0e5145"
WHITE = "#ffffff"
RED_BG = "#fff0f0"
RED_TEXT = "#a9343e"
GREEN = "#168354"


class ShopApplication:
    def __init__(self, root: tk.Tk, repository: Repository) -> None:
        self.root = root
        self.repository = repository
        self.user: UserSession | None = None
        self.screen: tk.Frame | None = None
        self.root.title("Northstar · управление магазином")
        self.root.geometry("1240x790")
        self.root.minsize(980, 660)
        self.root.configure(bg=BG)
        self.root.option_add("*Font", ("Segoe UI", 10))
        self._set_icon()
        self.show_login()

    def _set_icon(self) -> None:
        icon = PROJECT_ROOT / "assets" / "shopdesk.png"
        if icon.exists():
            try:
                self.icon = tk.PhotoImage(file=str(icon))
                self.root.iconphoto(True, self.icon)
            except tk.TclError:
                pass

    def _clear(self) -> None:
        if self.screen is not None:
            self.screen.destroy()
        self.screen = None

    def show_login(self) -> None:
        self.user = None
        self._clear()
        self.root.title("Northstar · вход")
        screen = tk.Frame(self.root, bg=BG)
        screen.pack(fill="both", expand=True)
        screen.grid_columnconfigure(0, weight=1)
        screen.grid_rowconfigure(0, weight=1)
        card = tk.Frame(screen, bg=WHITE, padx=38, pady=34,
                        highlightbackground="#d8e1ec", highlightthickness=1)
        card.grid(row=0, column=0)
        tk.Label(card, text="NORTHSTAR", bg=WHITE, fg=ACCENT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(card, text="Управление магазином", bg=WHITE, fg=INK,
                 font=("Segoe UI", 24, "bold")).pack(anchor="w", pady=(6, 2))
        tk.Label(card, text="Войдите в систему или откройте каталог как гость.",
                 bg=WHITE, fg=MUTED).pack(anchor="w", pady=(0, 24))

        tk.Label(card, text="Логин", bg=WHITE, fg=INK).pack(anchor="w")
        self.login_var = tk.StringVar()
        login = ttk.Entry(card, textvariable=self.login_var, width=42)
        login.pack(fill="x", pady=(5, 14), ipady=5)
        tk.Label(card, text="Пароль", bg=WHITE, fg=INK).pack(anchor="w")
        self.password_var = tk.StringVar()
        password = ttk.Entry(card, textvariable=self.password_var, show="•", width=42)
        password.pack(fill="x", pady=(5, 18), ipady=5)
        password.bind("<Return>", lambda _event: self.login())
        ttk.Button(card, text="Войти", style="Accent.TButton", command=self.login).pack(fill="x", ipady=5)
        ttk.Button(card, text="Продолжить как гость", command=self.login_as_guest).pack(fill="x", pady=(9, 0), ipady=4)
        tk.Label(card, text="Пароли хранятся в базе в виде PBKDF2-хэша.",
                 bg=WHITE, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(18, 0))
        self.screen = screen
        login.focus_set()

    def login(self) -> None:
        user = self.repository.authenticate(self.login_var.get(), self.password_var.get())
        if user is None:
            messagebox.showerror("Вход не выполнен", "Проверьте логин и пароль.", parent=self.root)
            self.password_var.set("")
            return
        self.show_main(user)

    def login_as_guest(self) -> None:
        self.show_main(guest_session())

    def show_main(self, user: UserSession) -> None:
        self.user = user
        self._clear()
        self.root.title(f"Northstar · {user.full_name} · {user.role_title}")
        screen = tk.Frame(self.root, bg=BG)
        screen.pack(fill="both", expand=True)
        header = tk.Frame(screen, bg=INK, padx=24, pady=15)
        header.pack(fill="x")
        tk.Label(header, text="NORTHSTAR", bg=INK, fg="#73dbc0",
                 font=("Segoe UI", 12, "bold")).pack(side="left")
        tk.Label(header, text="  /  Магазин техники", bg=INK, fg=WHITE,
                 font=("Segoe UI", 14, "bold")).pack(side="left")
        tk.Label(header, text=f"{user.full_name}  ·  {user.role_title}", bg=INK,
                 fg="#d1deed", font=("Segoe UI", 10)).pack(side="right", padx=(12, 4))
        ttk.Button(header, text="Выйти", command=self.show_login).pack(side="right")

        self.notebook = ttk.Notebook(screen)
        self.notebook.pack(fill="both", expand=True, padx=18, pady=16)
        self.catalog_page = CatalogPage(self.notebook, self.repository, user, self.root)
        self.notebook.add(self.catalog_page, text="  Каталог  ")
        if can(user, "orders"):
            self.orders_page = OrdersPage(self.notebook, self.repository, self.root)
            self.notebook.add(self.orders_page, text="  Заказы  ")
        else:
            self.orders_page = None
        footer = tk.Frame(screen, bg=BG, padx=20, pady=5)
        footer.pack(fill="x")
        tk.Label(footer, text="Локальная база данных SQLite · данные хранятся на этом компьютере",
                 bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="left")
        self.screen = screen


class CatalogPage(ttk.Frame):
    def __init__(self, parent, repository: Repository, user: UserSession, root: tk.Tk) -> None:
        super().__init__(parent, style="Page.TFrame")
        self.repository = repository
        self.user = user
        self.root = root
        self.category_rows = repository.categories()
        self.category_ids = {row["name"]: row["id"] for row in self.category_rows}
        self.category_options = ["Все категории"] + list(self.category_ids)
        self.photo_refs: list[ImageTk.PhotoImage] = []
        self._build_toolbar()
        self._build_catalog()
        self.render_products()

    def _build_toolbar(self) -> None:
        heading = tk.Frame(self, bg=BG)
        heading.pack(fill="x", padx=20, pady=(18, 10))
        tk.Label(heading, text="Каталог товаров", bg=BG, fg=INK,
                 font=("Segoe UI", 21, "bold")).pack(side="left")
        if can(self.user, "product_write"):
            ttk.Button(heading, text="＋ Добавить товар", style="Accent.TButton",
                       command=self._add_product).pack(side="right", padx=(8, 0))
            ttk.Button(heading, text="Импорт CSV", command=self._import_csv).pack(side="right")

        if can(self.user, "catalog_filters"):
            tools = tk.Frame(self, bg=WHITE, padx=12, pady=11,
                             highlightbackground="#dce4ed", highlightthickness=1)
            tools.pack(fill="x", padx=20, pady=(0, 12))
            self.search_var = tk.StringVar()
            search = ttk.Entry(tools, textvariable=self.search_var, width=29)
            search.pack(side="left", padx=(0, 9), ipady=4)
            self.search_var.trace_add("write", lambda *_: self.render_products())
            self.category_var = tk.StringVar(value="Все категории")
            category = ttk.Combobox(tools, textvariable=self.category_var,
                                    values=self.category_options, state="readonly", width=23)
            self.category_box = category
            category.pack(side="left", padx=5)
            category.bind("<<ComboboxSelected>>", lambda _event: self.render_products())
            self.sort_var = tk.StringVar(value="По названию А—Я")
            sort = ttk.Combobox(tools, textvariable=self.sort_var,
                                values=list(SORTS), state="readonly", width=25)
            sort.pack(side="left", padx=5)
            sort.bind("<<ComboboxSelected>>", lambda _event: self.render_products())
            self.stock_var = tk.BooleanVar(value=False)
            ttk.Checkbutton(tools, text="Только в наличии", variable=self.stock_var,
                            command=self.render_products).pack(side="left", padx=(10, 5))
            ttk.Button(tools, text="Сбросить", command=self._reset_filters).pack(side="right")
            search.insert(0, "Название или описание")
            search.configure(foreground=MUTED)
            search.bind("<FocusIn>", lambda _event: self._clear_search_hint(search))
            self.search_entry = search
        else:
            tk.Label(self, text="Гостевой режим · доступен только просмотр каталога",
                     bg="#e7eef6", fg=MUTED, padx=12, pady=9).pack(fill="x", padx=20, pady=(0, 12))

        summary = tk.Frame(self, bg=BG)
        summary.pack(fill="x", padx=22, pady=(0, 7))
        self.result_label = tk.Label(summary, text="", bg=BG, fg=MUTED,
                                     font=("Segoe UI", 9))
        self.result_label.pack(side="left")

    def _clear_search_hint(self, entry: ttk.Entry) -> None:
        if entry.get() == "Название или описание":
            entry.delete(0, "end")
            entry.configure(foreground=INK)

    def _reset_filters(self) -> None:
        self.search_var.set("")
        self.search_entry.configure(foreground=INK)
        self.category_var.set("Все категории")
        self.sort_var.set("По названию А—Я")
        self.stock_var.set(False)
        self.render_products()

    def _build_catalog(self) -> None:
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        self.canvas = tk.Canvas(body, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.cards_frame = tk.Frame(self.canvas, bg=BG)
        self.frame_window = self.canvas.create_window((0, 0), window=self.cards_frame, anchor="nw")
        self.cards_frame.bind("<Configure>", lambda _event: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._resize_cards)
        self.canvas.bind("<MouseWheel>", lambda event: self.canvas.yview_scroll(-1 * (event.delta // 120), "units"))

    def _resize_cards(self, event) -> None:
        self.canvas.itemconfigure(self.frame_window, width=event.width)
        columns = max(1, min(4, event.width // 300))
        changed = columns != getattr(self, "_grid_columns", columns)
        self._grid_columns = columns
        for column in range(self._grid_columns):
            self.cards_frame.grid_columnconfigure(column, weight=1, uniform="cards")
        if changed and self.cards_frame.winfo_children():
            self.render_products()

    def _current_filters(self) -> tuple:
        if not can(self.user, "catalog_filters"):
            return "", None, "По названию А—Я", False
        search = self.search_var.get().strip()
        if search == "Название или описание":
            search = ""
        category_id = self.category_ids.get(self.category_var.get())
        return search, category_id, self.sort_var.get(), self.stock_var.get()

    def render_products(self) -> None:
        if not hasattr(self, "cards_frame"):
            return
        for child in self.cards_frame.winfo_children():
            child.destroy()
        self.photo_refs = []
        products = self.repository.products(*self._current_filters())
        self.result_label.configure(text=f"Найдено товаров: {len(products)}")
        columns = getattr(self, "_grid_columns", 3)
        if not products:
            tk.Label(self.cards_frame, text="По заданным условиям товары не найдены.",
                     bg=BG, fg=MUTED, font=("Segoe UI", 12)).grid(row=0, column=0, pady=45)
            return
        for index, product in enumerate(products):
            card = ProductCard(self.cards_frame, product, self.user, self.root,
                               self.repository, self.render_products, self._open_editor)
            card.grid(row=index // columns, column=index % columns, sticky="nsew", padx=7, pady=7)

    def _add_product(self) -> None:
        self._open_editor(None)

    def _open_editor(self, product_id: int | None) -> None:
        if product_id is None:
            product = None
        else:
            product = next((row for row in self.repository.products() if row["id"] == product_id), None)
        ProductForm(self.root, self.repository, product, on_saved=self.render_products)

    def _import_csv(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root, title="Импорт товаров из CSV",
            filetypes=[("CSV", "*.csv"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        try:
            imported = self.repository.import_products_csv(path)
        except (OSError, ValueError) as error:
            messagebox.showerror("Ошибка импорта", str(error), parent=self.root)
            return
        messagebox.showinfo("Импорт завершён", f"Добавлено товаров: {imported}", parent=self.root)
        self.category_rows = self.repository.categories()
        self.category_ids = {row["name"]: row["id"] for row in self.category_rows}
        self.category_options = ["Все категории"] + list(self.category_ids)
        if can(self.user, "catalog_filters"):
            self.category_box.configure(values=self.category_options)
        self.render_products()


class ProductCard(tk.Frame):
    def __init__(self, parent, product, user, root, repository, refresh, open_editor) -> None:
        color = RED_BG if product["is_slow_moving"] else WHITE
        super().__init__(parent, bg=color, padx=12, pady=12,
                         highlightbackground="#e3c6c8" if product["is_slow_moving"] else "#dce4ed",
                         highlightthickness=1)
        self.product = product
        self.user = user
        self.root = root
        self.repository = repository
        self.refresh = refresh
        self.open_editor = open_editor
        self._build()

    def _build(self) -> None:
        image_box = tk.Frame(self, bg="#e9eff6", height=132)
        image_box.pack(fill="x", pady=(0, 12))
        image_box.pack_propagate(False)
        image = self._load_image(self.product["image_path"])
        if image is None:
            tk.Label(image_box, text="◇\nОБЛОЖКА ТОВАРА", bg="#e9eff6", fg="#8797aa",
                     font=("Segoe UI", 11, "bold")).pack(expand=True)
        else:
            self.photo = image
            tk.Label(image_box, image=image, bg="#e9eff6").pack(expand=True)

        badges = []
        if self.product["is_new"]:
            badges.append(("НОВИНКА", GREEN))
        if self.product["is_digital"]:
            badges.append(("ЦИФРОВОЙ", ACCENT))
        if self.product["is_slow_moving"]:
            badges.append(("УЦЕНКА", RED_TEXT))
        if badges:
            badge_row = tk.Frame(self, bg=self["bg"])
            badge_row.pack(fill="x", pady=(0, 7))
            for text, color in badges:
                tk.Label(badge_row, text=text, bg=self["bg"], fg=color,
                         font=("Segoe UI", 8, "bold")).pack(side="left", padx=(0, 8))

        title_color = GREEN if self.product["is_new"] else INK
        title_weight = "bold" if self.product["is_new"] else "normal"
        tk.Label(self, text=self.product["name"], bg=self["bg"], fg=title_color,
                 font=("Segoe UI", 12, title_weight), anchor="w", justify="left",
                 wraplength=270).pack(fill="x")
        tk.Label(self, text=self.product["category_name"], bg=self["bg"], fg=MUTED,
                 font=("Segoe UI", 9), anchor="w").pack(fill="x", pady=(3, 5))
        description = self.product["description"] or "Описание не заполнено."
        tk.Label(self, text=description, bg=self["bg"], fg="#46566c", anchor="w",
                 justify="left", wraplength=270, height=3).pack(fill="x")

        line = tk.Frame(self, bg=self["bg"])
        line.pack(fill="x", pady=(10, 4))
        price = f"{self.product['price']:,.0f} ₽".replace(",", " ")
        tk.Label(line, text=price, bg=self["bg"], fg=INK,
                 font=("Segoe UI", 15, "bold")).pack(side="left")
        if self.product["stock"]:
            stock_text, stock_color = f"Остаток: {self.product['stock']}", ACCENT
        else:
            stock_text, stock_color = "Нет в наличии", RED_TEXT
        if self.product["is_digital"]:
            stock_text, stock_color = "Цифровая выдача", ACCENT
        tk.Label(line, text=stock_text, bg=self["bg"], fg=stock_color,
                 font=("Segoe UI", 9, "bold")).pack(side="right")

        if can(self.user, "product_write"):
            actions = tk.Frame(self, bg=self["bg"])
            actions.pack(fill="x", pady=(9, 0))
            ttk.Button(actions, text="Изменить", command=lambda: self.open_editor(self.product["id"])).pack(side="left")
            ttk.Button(actions, text="Удалить", command=self._delete).pack(side="right")

    def _load_image(self, image_path: str | None):
        if not image_path:
            return None
        path = Path(image_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        try:
            with Image.open(path) as source:
                preview = source.convert("RGB")
                preview.thumbnail((280, 132))
                return ImageTk.PhotoImage(preview.copy())
        except (OSError, ValueError):
            return None

    def _delete(self) -> None:
        if not messagebox.askyesno("Удаление товара", f"Удалить товар «{self.product['name']}»?",
                                   parent=self.root):
            return
        try:
            self.repository.delete_product(self.product["id"])
        except ProductInUseError as error:
            messagebox.showwarning("Удаление запрещено", str(error), parent=self.root)
            return
        self.refresh()


class ProductForm(tk.Toplevel):
    def __init__(self, root, repository: Repository, product, on_saved) -> None:
        super().__init__(root)
        self.root = root
        self.repository = repository
        self.product = product
        self.on_saved = on_saved
        self.selected_image: Path | None = None
        self.title("Новый товар" if product is None else "Изменение товара")
        self.configure(bg=BG)
        self.geometry("560x700")
        self.minsize(520, 620)
        self.transient(root)
        self.grab_set()
        self._build()

    def _build(self) -> None:
        outer = tk.Frame(self, bg=BG, padx=24, pady=18)
        outer.pack(fill="both", expand=True)
        heading = "Новый товар" if self.product is None else "Редактирование товара"
        tk.Label(outer, text=heading, bg=BG, fg=INK,
                 font=("Segoe UI", 19, "bold")).pack(anchor="w")
        tk.Label(outer, text="Поля со звёздочкой обязательны. ID назначается базой данных.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(3, 15))
        form = tk.Frame(outer, bg=WHITE, padx=16, pady=14,
                        highlightbackground="#dce4ed", highlightthickness=1)
        form.pack(fill="both", expand=True)
        existing = self.product

        def field(label: str, key: str, default: str = "") -> tk.Entry:
            tk.Label(form, text=label, bg=WHITE, fg=INK).pack(anchor="w", pady=(7, 2))
            entry = ttk.Entry(form)
            entry.pack(fill="x", ipady=3)
            entry.insert(0, str(existing[key] if existing is not None else default))
            return entry

        self.name_entry = field("Название *", "name")
        tk.Label(form, text="Описание", bg=WHITE, fg=INK).pack(anchor="w", pady=(7, 2))
        self.description = tk.Text(form, height=4, wrap="word", font=("Segoe UI", 10),
                                   relief="solid", bd=1, highlightthickness=0)
        self.description.pack(fill="x")
        if existing is not None:
            self.description.insert("1.0", existing["description"])
        tk.Label(form, text="Категория *", bg=WHITE, fg=INK).pack(anchor="w", pady=(7, 2))
        self.category_var = tk.StringVar(value=existing["category_name"] if existing is not None else "")
        ttk.Combobox(form, textvariable=self.category_var,
                     values=[row["name"] for row in self.repository.categories()],
                     state="readonly").pack(fill="x")
        self.price_entry = field("Цена, ₽ *", "price")
        self.stock_entry = field("Остаток, шт. *", "stock", "0")

        flags = tk.Frame(form, bg=WHITE)
        flags.pack(fill="x", pady=(10, 3))
        self.digital_var = tk.BooleanVar(value=bool(existing["is_digital"]) if existing is not None else False)
        self.new_var = tk.BooleanVar(value=bool(existing["is_new"]) if existing is not None else False)
        self.slow_var = tk.BooleanVar(value=bool(existing["is_slow_moving"]) if existing is not None else False)
        ttk.Checkbutton(flags, text="Цифровой товар", variable=self.digital_var).pack(anchor="w")
        ttk.Checkbutton(flags, text="Новинка", variable=self.new_var).pack(anchor="w")
        ttk.Checkbutton(flags, text="Неликвид / уценка", variable=self.slow_var).pack(anchor="w")
        image_line = tk.Frame(form, bg=WHITE)
        image_line.pack(fill="x", pady=(9, 0))
        ttk.Button(image_line, text="Выбрать обложку…", command=self._choose_image).pack(side="left")
        initial_image = existing["image_path"] if existing is not None and existing["image_path"] else "Без обложки"
        self.image_label = tk.Label(image_line, text=initial_image, bg=WHITE, fg=MUTED,
                                    anchor="w", wraplength=290)
        self.image_label.pack(side="left", padx=10, fill="x", expand=True)

        actions = tk.Frame(outer, bg=BG)
        actions.pack(fill="x", pady=(14, 0))
        ttk.Button(actions, text="← Назад", command=self.destroy).pack(side="left")
        ttk.Button(actions, text="Сохранить товар", style="Accent.TButton",
                   command=self._save).pack(side="right")

    def _choose_image(self) -> None:
        path = filedialog.askopenfilename(
            parent=self, title="Выберите обложку",
            filetypes=[("Изображения", "*.png *.jpg *.jpeg *.gif *.webp"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        try:
            image = validate_image(path)
        except ValueError as error:
            messagebox.showerror("Некорректная обложка", str(error), parent=self)
            return
        self.selected_image = image
        self.image_label.configure(text=image.name)

    def _save(self) -> None:
        data = {
            "name": self.name_entry.get(),
            "description": self.description.get("1.0", "end-1c"),
            "category": self.category_var.get(),
            "price": self.price_entry.get(),
            "stock": self.stock_entry.get(),
            "is_digital": self.digital_var.get(),
            "is_new": self.new_var.get(),
            "is_slow_moving": self.slow_var.get(),
            "image_path": self.product["image_path"] if self.product is not None else None,
        }
        try:
            self.repository.normalize_product(data)
        except ValueError as error:
            messagebox.showerror("Проверьте данные", str(error), parent=self)
            return
        copied_path = None
        if self.selected_image is not None:
            try:
                copied_path = copy_uploaded_image(self.selected_image, PROJECT_ROOT)
            except (OSError, ValueError) as error:
                messagebox.showerror("Не удалось скопировать файл", str(error), parent=self)
                return
            data["image_path"] = copied_path
        try:
            product_id = self.product["id"] if self.product is not None else None
            self.repository.save_product(data, product_id)
        except (ValueError, OSError) as error:
            if copied_path:
                (PROJECT_ROOT / copied_path).unlink(missing_ok=True)
            messagebox.showerror("Не удалось сохранить товар", str(error), parent=self)
            return
        self.on_saved()
        self.destroy()


class OrdersPage(ttk.Frame):
    def __init__(self, parent, repository: Repository, root: tk.Tk) -> None:
        super().__init__(parent, style="Page.TFrame")
        self.repository = repository
        self.root = root
        self.orders_by_id = {}
        self._build()
        self.refresh()

    def _build(self) -> None:
        heading = tk.Frame(self, bg=BG)
        heading.pack(fill="x", padx=20, pady=(18, 10))
        tk.Label(heading, text="Заказы", bg=BG, fg=INK,
                 font=("Segoe UI", 21, "bold")).pack(side="left")
        tk.Label(heading, text="Просроченная доставка подсвечена красным.", bg=BG,
                 fg=MUTED, font=("Segoe UI", 9)).pack(side="right")

        columns = ("id", "customer", "phone", "email", "created", "delivery", "status", "total", "items", "comment")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=17, selectmode="browse")
        labels = {
            "id": "№", "customer": "Клиент", "phone": "Телефон", "email": "Email",
            "created": "Создан", "delivery": "Доставка", "status": "Статус",
            "total": "Сумма, ₽", "items": "Состав заказа", "comment": "Комментарий",
        }
        widths = {"id": 45, "customer": 155, "phone": 130, "email": 160, "created": 95,
                  "delivery": 95, "status": 135, "total": 95, "items": 250, "comment": 210}
        for name in columns:
            self.tree.heading(name, text=labels[name])
            self.tree.column(name, width=widths[name], minwidth=55, stretch=name in {"items", "comment"})
        self.tree.tag_configure("overdue", background="#ffe4e5", foreground="#842d34")
        self.tree.tag_configure("delivered", foreground="#758195")
        scrollbar_y = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        self.tree.pack(fill="both", expand=True, padx=20)
        scrollbar_y.place(relx=1.0, rely=0.20, relheight=0.62, anchor="ne")
        scrollbar_x.pack(fill="x", padx=20)
        self.tree.bind("<<TreeviewSelect>>", self._select_order)

        controls = tk.Frame(self, bg=WHITE, padx=14, pady=13,
                            highlightbackground="#dce4ed", highlightthickness=1)
        controls.pack(fill="x", padx=20, pady=14)
        tk.Label(controls, text="Статус", bg=WHITE, fg=INK).pack(side="left", padx=(0, 6))
        self.status_var = tk.StringVar()
        self.status_box = ttk.Combobox(controls, textvariable=self.status_var, state="readonly", width=22,
                                       values=[row["title"] for row in self.repository.statuses()])
        self.status_box.pack(side="left", padx=(0, 16))
        tk.Label(controls, text="Дата доставки (ГГГГ-ММ-ДД)", bg=WHITE, fg=INK).pack(side="left", padx=(0, 6))
        self.delivery_var = tk.StringVar()
        ttk.Entry(controls, textvariable=self.delivery_var, width=16).pack(side="left", padx=(0, 12), ipady=3)
        ttk.Button(controls, text="Сохранить изменения", style="Accent.TButton",
                   command=self._save_order).pack(side="left")
        ttk.Button(controls, text="Обновить", command=self.refresh).pack(side="right")

    def refresh(self) -> None:
        self.orders_by_id = {row["id"]: row for row in self.repository.orders()}
        for item in self.tree.get_children():
            self.tree.delete(item)
        today = date.today().isoformat()
        for order in self.orders_by_id.values():
            values = (
                order["id"], order["customer_name"], order["customer_phone"], order["customer_email"] or "—",
                order["created_at"][:10], order["delivery_date"], order["status"],
                f"{order['total']:,.2f}".replace(",", " "), order["items"] or "—", order["comment"] or "—",
            )
            if order["delivery_date"] < today and order["status_code"] not in {"issued", "cancelled"}:
                tags = ("overdue",)
            elif order["status_code"] == "issued":
                tags = ("delivered",)
            else:
                tags = ()
            self.tree.insert("", "end", iid=str(order["id"]), values=values, tags=tags)

    def _select_order(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        order = self.orders_by_id.get(int(selected[0]))
        if order:
            self.status_var.set(order["status"])
            self.delivery_var.set(order["delivery_date"])

    def _save_order(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Заказ не выбран", "Выберите строку заказа в таблице.", parent=self.root)
            return
        try:
            self.repository.update_order(int(selected[0]), self.status_var.get(), self.delivery_var.get())
        except ValueError as error:
            messagebox.showerror("Проверьте данные заказа", str(error), parent=self.root)
            return
        self.refresh()
        self.tree.selection_set(selected[0])
        messagebox.showinfo("Сохранено", "Статус и дата доставки обновлены в базе данных.", parent=self.root)


def configure_styles(root: tk.Tk) -> None:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("Page.TFrame", background=BG)
    style.configure("TNotebook", background=BG, borderwidth=0)
    style.configure("TNotebook.Tab", padding=(16, 9), background="#e2e9f1", foreground=INK)
    style.map("TNotebook.Tab", background=[("selected", WHITE)], foreground=[("selected", ACCENT)])
    style.configure("TButton", padding=(10, 7), background="#e7edf4", foreground=INK)
    style.map("TButton", background=[("active", "#d8e3ee")])
    style.configure("Accent.TButton", padding=(11, 8), background=ACCENT, foreground=WHITE)
    style.map("Accent.TButton", background=[("active", ACCENT_DARK)])
    style.configure("Treeview", rowheight=29, background=WHITE, fieldbackground=WHITE,
                    foreground=INK, bordercolor="#dce4ed")
    style.configure("Treeview.Heading", padding=(8, 8), background="#e5ebf2", foreground=INK,
                    font=("Segoe UI", 9, "bold"))
    style.map("Treeview", background=[("selected", "#d5ece5")], foreground=[("selected", INK)])
