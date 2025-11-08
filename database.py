from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, Iterable, Optional

DB_PATH = Path(__file__).resolve().parent / "bot.sqlite3"


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                phone_number TEXT NOT NULL,
                fname TEXT DEFAULT '',
                lname TEXT DEFAULT '',
                username TEXT DEFAULT ''
            )
            """
        )
        _ensure_users_schema(conn)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                telegram_id INTEGER PRIMARY KEY,
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id) ON DELETE CASCADE
            )
            """
        )


def _ensure_users_schema(conn: sqlite3.Connection) -> None:
    columns = {
        row[1]: {"type": row[2], "notnull": row[3], "default": row[4]}
        for row in conn.execute("PRAGMA table_info(users)")
    }

    if "phone_number" not in columns:
        conn.execute("ALTER TABLE users RENAME TO users_old")
        conn.execute(
            """
            CREATE TABLE users (
                telegram_id INTEGER PRIMARY KEY,
                phone_number TEXT NOT NULL,
                fname TEXT DEFAULT '',
                lname TEXT DEFAULT '',
                username TEXT DEFAULT ''
            )
            """
        )
        conn.execute(
            """
            INSERT INTO users (telegram_id, phone_number, fname, lname, username)
            SELECT
                telegram_id,
                substr(COALESCE(phone_last10, ''), -10),
                '',
                '',
                ''
            FROM users_old
            """
        )
        conn.execute("DROP TABLE users_old")
        columns = {
            row[1]: {"type": row[2], "notnull": row[3], "default": row[4]}
            for row in conn.execute("PRAGMA table_info(users)")
        }

    for column_name in ("fname", "lname", "username"):
        if column_name not in columns:
            conn.execute(
                f"""
                ALTER TABLE users
                ADD COLUMN {column_name} TEXT DEFAULT ''
                """
            )


def upsert_user(
    telegram_id: int,
    phone_number: str,
    fname: str,
    lname: str,
    username: str,
) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO users (telegram_id, phone_number, fname, lname, username)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE
            SET
                phone_number = excluded.phone_number,
                fname = excluded.fname,
                lname = excluded.lname,
                username = excluded.username
            """,
            (telegram_id, phone_number, fname or "", lname or "", username or ""),
        )


def get_user(telegram_id: int) -> Optional[Dict[str, str]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT telegram_id, phone_number, fname, lname, username
            FROM users
            WHERE telegram_id = ?
            """,
            (telegram_id,),
        )
        row = cursor.fetchone()
    if row is None:
        return None
    return {
        "telegram_id": row[0],
        "phone_number": row[1],
        "fname": row[2],
        "lname": row[3],
        "username": row[4],
    }


def get_user_by_phone(phone_number: str) -> Optional[Dict[str, str]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT telegram_id, phone_number, fname, lname, username
            FROM users
            WHERE phone_number = ?
            """,
            (phone_number,),
        )
        row = cursor.fetchone()
    if row is None:
        return None
    return {
        "telegram_id": row[0],
        "phone_number": row[1],
        "fname": row[2],
        "lname": row[3],
        "username": row[4],
    }


def user_has_phone(telegram_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT 1 FROM users WHERE telegram_id = ? LIMIT 1", (telegram_id,)
        )
        return cursor.fetchone() is not None


def add_admin(telegram_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO admins (telegram_id)
            VALUES (?)
            ON CONFLICT(telegram_id) DO NOTHING
            """,
            (telegram_id,),
        )
        return cursor.rowcount > 0


def remove_admin(telegram_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "DELETE FROM admins WHERE telegram_id = ?", (telegram_id,)
        )
        return cursor.rowcount > 0


def is_admin(telegram_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT 1 FROM admins WHERE telegram_id = ? LIMIT 1", (telegram_id,)
        )
        return cursor.fetchone() is not None


def list_admins() -> Iterable[Dict[str, str]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT
                admins.telegram_id,
                users.phone_number,
                users.fname,
                users.lname,
                users.username
            FROM admins
            LEFT JOIN users ON users.telegram_id = admins.telegram_id
            ORDER BY admins.telegram_id
            """
        )
        for telegram_id, phone_number, fname, lname, username in cursor.fetchall():
            yield {
                "telegram_id": telegram_id,
                "phone_number": phone_number or "",
                "fname": fname or "",
                "lname": lname or "",
                "username": username or "",
            }


def get_user_stats() -> Dict[str, int]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN phone_number IS NOT NULL AND TRIM(phone_number) <> '' THEN 1 ELSE 0 END) AS with_phone
            FROM users
            """
        )
        total, with_phone = cursor.fetchone()

    with_phone = with_phone or 0
    total = total or 0
    without_phone = total - with_phone

    return {
        "total": total,
        "with_phone": with_phone,
        "without_phone": without_phone,
    }

