"""Запуск приложения Northstar Shop Desk."""

import tkinter as tk

from app.database import Database
from app.repository import Repository
from app.ui import ShopApplication, configure_styles


def main() -> None:
    database = Database()
    database.initialize()
    root = tk.Tk()
    configure_styles(root)
    ShopApplication(root, Repository(database))

    def close() -> None:
        database.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", close)
    root.mainloop()


if __name__ == "__main__":
    main()
