"""Хранилище данных о питании, воде и профиле в SQLite."""
import sqlite3
from datetime import datetime

class Storage:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        return db

    def _init_db(self):
        with self._connect() as db:
            # Таблица еды
            db.execute("""
                CREATE TABLE IF NOT EXISTS food_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user TEXT NOT NULL,
                    date TEXT NOT NULL,
                    meal TEXT NOT NULL,
                    name TEXT NOT NULL,
                    kcal INTEGER NOT NULL,
                    p REAL NOT NULL,
                    f REAL NOT NULL,
                    c REAL NOT NULL
                )
            """)
            # Таблица воды (уникальная запись на пользователя и дату)
            db.execute("""
                CREATE TABLE IF NOT EXISTS water_log (
                    user TEXT NOT NULL,
                    date TEXT NOT NULL,
                    cups INTEGER DEFAULT 0,
                    PRIMARY KEY (user, date)
                )
            """)
            # Профиль (цель по калориям)
            db.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    user TEXT PRIMARY KEY,
                    kcal_goal INTEGER DEFAULT 2000
                )
            """)
            db.commit()

    def _today(self):
        return datetime.now().strftime("%Y-%m-%d")

    def get_kcal_goal(self, user: str) -> int:
        with self._connect() as db:
            row = db.execute("SELECT kcal_goal FROM profiles WHERE user = ?", (user,)).fetchone()
            return row["kcal_goal"] if row else 2000

    def get_day_food(self, user: str, date: str = None) -> list:
        if not date: date = self._today()
        with self._connect() as db:
            rows = db.execute("SELECT * FROM food_log WHERE user = ? AND date = ?", (user, date)).fetchall()
            return [dict(r) for r in rows]

    def add_food(self, user: str, meal: str, food: tuple):
        name, _amount, kcal, p, f, c = food
        with self._connect() as db:
            db.execute(
                "INSERT INTO food_log (user, date, meal, name, kcal, p, f, c) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (user, self._today(), meal, name, kcal, p, f, c)
            )
            db.commit()

    def get_water(self, user: str) -> int:
        with self._connect() as db:
            row = db.execute("SELECT cups FROM water_log WHERE user = ? AND date = ?", (user, self._today())).fetchone()
            return row["cups"] if row else 0

    def set_water(self, user: str, cups: int):
        cups = max(0, min(cups, 8)) # Ограничиваем от 0 до 8
        with self._connect() as db:
            db.execute(
                "INSERT INTO water_log (user, date, cups) VALUES (?, ?, ?) "
                "ON CONFLICT(user, date) DO UPDATE SET cups = excluded.cups",
                (user, self._today(), cups)
            )
            db.commit()