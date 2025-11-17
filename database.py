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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS webinars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                cover_photo_file_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _ensure_webinars_schema(conn)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS webinar_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                webinar_id INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                file_type TEXT NOT NULL,
                content_order INTEGER DEFAULT 0,
                FOREIGN KEY (webinar_id) REFERENCES webinars (id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS drop_learning (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                cover_photo_file_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS drop_learning_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drop_learning_id INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                file_type TEXT NOT NULL,
                content_order INTEGER DEFAULT 0,
                FOREIGN KEY (drop_learning_id) REFERENCES drop_learning (id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS case_studies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                cover_photo_file_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS case_studies_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_study_id INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                file_type TEXT NOT NULL,
                content_order INTEGER DEFAULT 0,
                FOREIGN KEY (case_study_id) REFERENCES case_studies (id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS webinar_views (
                user_id INTEGER NOT NULL,
                webinar_id INTEGER NOT NULL,
                viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, webinar_id),
                FOREIGN KEY (webinar_id) REFERENCES webinars (id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS drop_learning_views (
                user_id INTEGER NOT NULL,
                drop_learning_id INTEGER NOT NULL,
                viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, drop_learning_id),
                FOREIGN KEY (drop_learning_id) REFERENCES drop_learning (id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS case_studies_views (
                user_id INTEGER NOT NULL,
                case_study_id INTEGER NOT NULL,
                viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, case_study_id),
                FOREIGN KEY (case_study_id) REFERENCES case_studies (id) ON DELETE CASCADE
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


def _ensure_webinars_schema(conn: sqlite3.Connection) -> None:
    columns = {
        row[1]: {"type": row[2], "notnull": row[3], "default": row[4]}
        for row in conn.execute("PRAGMA table_info(webinars)")
    }
    if "title" not in columns:
        conn.execute(
            """
            ALTER TABLE webinars
            ADD COLUMN title TEXT DEFAULT ''
            """
        )
        conn.execute(
            """
            UPDATE webinars
            SET title = CASE
                WHEN TRIM(title) = '' OR title IS NULL THEN
                    CASE
                        WHEN LENGTH(description) <= 40 THEN description
                        ELSE SUBSTR(description, 1, 40)
                    END
                ELSE title
            END
            """
        )
    if "cover_photo_file_id" not in columns:
        conn.execute(
            """
            ALTER TABLE webinars
            ADD COLUMN cover_photo_file_id TEXT
            """
        )
    # Remove registration_link if it exists (migration)
    if "registration_link" in columns:
        # SQLite doesn't support DROP COLUMN directly, so we'll recreate the table
        # First, check if cover_photo_file_id exists, if not add it
        if "cover_photo_file_id" not in columns:
            conn.execute("""
                ALTER TABLE webinars
                ADD COLUMN cover_photo_file_id TEXT
            """)
        # Now recreate table without registration_link
        conn.execute("""
            CREATE TABLE IF NOT EXISTS webinars_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                cover_photo_file_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            INSERT INTO webinars_new (id, title, description, cover_photo_file_id, created_at)
            SELECT id, title, description, 
                   COALESCE(cover_photo_file_id, '') as cover_photo_file_id,
                   created_at
            FROM webinars
        """)
        conn.execute("DROP TABLE webinars")
        conn.execute("ALTER TABLE webinars_new RENAME TO webinars")


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


def ensure_user_record(
    telegram_id: int,
    fname: str,
    lname: str,
    username: str,
) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO users (telegram_id, phone_number, fname, lname, username)
            VALUES (?, '', ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                fname = excluded.fname,
                lname = excluded.lname,
                username = excluded.username
            """,
            (telegram_id, fname or "", lname or "", username or ""),
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
            """
            SELECT 1
            FROM users
            WHERE telegram_id = ?
              AND phone_number IS NOT NULL
              AND TRIM(phone_number) <> ''
            LIMIT 1
            """,
            (telegram_id,),
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

        # Get unique viewers for each section
        webinar_viewers = conn.execute(
            "SELECT COUNT(DISTINCT user_id) FROM webinar_views"
        ).fetchone()[0] or 0
        
        drop_learning_viewers = conn.execute(
            "SELECT COUNT(DISTINCT user_id) FROM drop_learning_views"
        ).fetchone()[0] or 0
        
        case_studies_viewers = conn.execute(
            "SELECT COUNT(DISTINCT user_id) FROM case_studies_views"
        ).fetchone()[0] or 0

        return {
            "total": total,
            "with_phone": with_phone,
            "without_phone": without_phone,
            "webinar_viewers": webinar_viewers,
            "drop_learning_viewers": drop_learning_viewers,
            "case_studies_viewers": case_studies_viewers,
        }


def iter_users(has_phone: Optional[bool] = None) -> Iterable[Dict[str, str]]:
    query = """
        SELECT telegram_id, phone_number, fname, lname, username
        FROM users
    """
    params = ()

    if has_phone is True:
        query += """
        WHERE phone_number IS NOT NULL AND TRIM(phone_number) <> ''
        """
    elif has_phone is False:
        query += """
        WHERE phone_number IS NULL OR TRIM(phone_number) = ''
        """

    query += " ORDER BY telegram_id"

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(query, params)
        for telegram_id, phone_number, fname, lname, username in cursor.fetchall():
            yield {
                "telegram_id": telegram_id,
                "phone_number": phone_number or "",
                "fname": fname or "",
                "lname": lname or "",
                "username": username or "",
            }


def list_webinars() -> Iterable[Dict[str, str]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT id, title, description, cover_photo_file_id, created_at
            FROM webinars
            ORDER BY created_at DESC, id DESC
            """
        )
        for (
            webinar_id,
            title,
            description,
            cover_photo_file_id,
            created_at,
        ) in cursor.fetchall():
            yield {
                "id": webinar_id,
                "title": title,
                "description": description,
                "cover_photo_file_id": cover_photo_file_id or "",
                "created_at": created_at,
            }


def get_webinar(webinar_id: int) -> Optional[Dict[str, str]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT id, title, description, cover_photo_file_id, created_at
            FROM webinars
            WHERE id = ?
            """,
            (webinar_id,),
        )
        row = cursor.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "title": row[1],
        "description": row[2],
        "cover_photo_file_id": row[3] or "",
        "created_at": row[4],
    }


def create_webinar(
    title: str,
    description: str,
    cover_photo_file_id: Optional[str] = None,
) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO webinars (title, description, cover_photo_file_id)
            VALUES (?, ?, ?)
            """,
            (title, description, cover_photo_file_id),
        )
        return cursor.lastrowid


def update_webinar(
    webinar_id: int,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    cover_photo_file_id: Optional[str] = None,
) -> bool:
    fields = []
    params = []
    if title is not None:
        fields.append("title = ?")
        params.append(title)
    if description is not None:
        fields.append("description = ?")
        params.append(description)
    if cover_photo_file_id is not None:
        fields.append("cover_photo_file_id = ?")
        params.append(cover_photo_file_id)
    if not fields:
        return False
    params.append(webinar_id)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            f"""
            UPDATE webinars
            SET {", ".join(fields)}
            WHERE id = ?
            """,
            tuple(params),
        )
        return cursor.rowcount > 0


def delete_webinar(webinar_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "DELETE FROM webinars WHERE id = ?",
            (webinar_id,),
        )
        return cursor.rowcount > 0


def add_webinar_content(webinar_id: int, file_id: str, file_type: str, content_order: int = 0) -> int:
    """Add content (video, voice, etc.) to a webinar."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO webinar_content (webinar_id, file_id, file_type, content_order)
            VALUES (?, ?, ?, ?)
            """,
            (webinar_id, file_id, file_type, content_order),
        )
        return cursor.lastrowid


def get_webinar_content(webinar_id: int) -> Iterable[Dict[str, str]]:
    """Get all content for a webinar, ordered by content_order."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT id, file_id, file_type, content_order
            FROM webinar_content
            WHERE webinar_id = ?
            ORDER BY content_order ASC, id ASC
            """,
            (webinar_id,),
        )
        for content_id, file_id, file_type, content_order in cursor.fetchall():
            yield {
                "id": content_id,
                "file_id": file_id,
                "file_type": file_type,
                "content_order": content_order,
            }


def delete_webinar_content(content_id: int) -> bool:
    """Delete a specific content item from a webinar."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "DELETE FROM webinar_content WHERE id = ?",
            (content_id,),
        )
        return cursor.rowcount > 0


def clear_webinar_content(webinar_id: int) -> None:
    """Delete all content for a webinar."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "DELETE FROM webinar_content WHERE webinar_id = ?",
            (webinar_id,),
        )


# Drop Learning functions
def list_drop_learning() -> Iterable[Dict[str, str]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT id, title, description, cover_photo_file_id, created_at
            FROM drop_learning
            ORDER BY created_at DESC, id DESC
            """
        )
        for (
            item_id,
            title,
            description,
            cover_photo_file_id,
            created_at,
        ) in cursor.fetchall():
            yield {
                "id": item_id,
                "title": title,
                "description": description,
                "cover_photo_file_id": cover_photo_file_id or "",
                "created_at": created_at,
            }


def get_drop_learning(item_id: int) -> Optional[Dict[str, str]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT id, title, description, cover_photo_file_id, created_at
            FROM drop_learning
            WHERE id = ?
            """,
            (item_id,),
        )
        row = cursor.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "title": row[1],
        "description": row[2],
        "cover_photo_file_id": row[3] or "",
        "created_at": row[4],
    }


def create_drop_learning(
    title: str,
    description: str,
    cover_photo_file_id: Optional[str] = None,
) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO drop_learning (title, description, cover_photo_file_id)
            VALUES (?, ?, ?)
            """,
            (title, description, cover_photo_file_id),
        )
        return cursor.lastrowid


def update_drop_learning(
    item_id: int,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    cover_photo_file_id: Optional[str] = None,
) -> bool:
    fields = []
    params = []
    if title is not None:
        fields.append("title = ?")
        params.append(title)
    if description is not None:
        fields.append("description = ?")
        params.append(description)
    if cover_photo_file_id is not None:
        fields.append("cover_photo_file_id = ?")
        params.append(cover_photo_file_id)
    if not fields:
        return False
    params.append(item_id)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            f"""
            UPDATE drop_learning
            SET {", ".join(fields)}
            WHERE id = ?
            """,
            tuple(params),
        )
        return cursor.rowcount > 0


def delete_drop_learning(item_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "DELETE FROM drop_learning WHERE id = ?",
            (item_id,),
        )
        return cursor.rowcount > 0


def add_drop_learning_content(item_id: int, file_id: str, file_type: str, content_order: int = 0) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO drop_learning_content (drop_learning_id, file_id, file_type, content_order)
            VALUES (?, ?, ?, ?)
            """,
            (item_id, file_id, file_type, content_order),
        )
        return cursor.lastrowid


def get_drop_learning_content(item_id: int) -> Iterable[Dict[str, str]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT id, file_id, file_type, content_order
            FROM drop_learning_content
            WHERE drop_learning_id = ?
            ORDER BY content_order ASC, id ASC
            """,
            (item_id,),
        )
        for content_id, file_id, file_type, content_order in cursor.fetchall():
            yield {
                "id": content_id,
                "file_id": file_id,
                "file_type": file_type,
                "content_order": content_order,
            }


# Case Studies functions
def list_case_studies() -> Iterable[Dict[str, str]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT id, title, description, cover_photo_file_id, created_at
            FROM case_studies
            ORDER BY created_at DESC, id DESC
            """
        )
        for (
            item_id,
            title,
            description,
            cover_photo_file_id,
            created_at,
        ) in cursor.fetchall():
            yield {
                "id": item_id,
                "title": title,
                "description": description,
                "cover_photo_file_id": cover_photo_file_id or "",
                "created_at": created_at,
            }


def get_case_study(item_id: int) -> Optional[Dict[str, str]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT id, title, description, cover_photo_file_id, created_at
            FROM case_studies
            WHERE id = ?
            """,
            (item_id,),
        )
        row = cursor.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "title": row[1],
        "description": row[2],
        "cover_photo_file_id": row[3] or "",
        "created_at": row[4],
    }


def create_case_study(
    title: str,
    description: str,
    cover_photo_file_id: Optional[str] = None,
) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO case_studies (title, description, cover_photo_file_id)
            VALUES (?, ?, ?)
            """,
            (title, description, cover_photo_file_id),
        )
        return cursor.lastrowid


def update_case_study(
    item_id: int,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    cover_photo_file_id: Optional[str] = None,
) -> bool:
    fields = []
    params = []
    if title is not None:
        fields.append("title = ?")
        params.append(title)
    if description is not None:
        fields.append("description = ?")
        params.append(description)
    if cover_photo_file_id is not None:
        fields.append("cover_photo_file_id = ?")
        params.append(cover_photo_file_id)
    if not fields:
        return False
    params.append(item_id)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            f"""
            UPDATE case_studies
            SET {", ".join(fields)}
            WHERE id = ?
            """,
            tuple(params),
        )
        return cursor.rowcount > 0


def delete_case_study(item_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "DELETE FROM case_studies WHERE id = ?",
            (item_id,),
        )
        return cursor.rowcount > 0


def record_webinar_view(user_id: int, webinar_id: int) -> None:
    """Record that a user viewed a webinar."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO webinar_views (user_id, webinar_id)
            VALUES (?, ?)
            """,
            (user_id, webinar_id),
        )


def record_drop_learning_view(user_id: int, drop_learning_id: int) -> None:
    """Record that a user viewed a drop learning item."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO drop_learning_views (user_id, drop_learning_id)
            VALUES (?, ?)
            """,
            (user_id, drop_learning_id),
        )


def record_case_study_view(user_id: int, case_study_id: int) -> None:
    """Record that a user viewed a case study."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO case_studies_views (user_id, case_study_id)
            VALUES (?, ?)
            """,
            (user_id, case_study_id),
        )


def add_case_study_content(item_id: int, file_id: str, file_type: str, content_order: int = 0) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO case_studies_content (case_study_id, file_id, file_type, content_order)
            VALUES (?, ?, ?, ?)
            """,
            (item_id, file_id, file_type, content_order),
        )
        return cursor.lastrowid


def get_case_study_content(item_id: int) -> Iterable[Dict[str, str]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT id, file_id, file_type, content_order
            FROM case_studies_content
            WHERE case_study_id = ?
            ORDER BY content_order ASC, id ASC
            """,
            (item_id,),
        )
        for content_id, file_id, file_type, content_order in cursor.fetchall():
            yield {
                "id": content_id,
                "file_id": file_id,
                "file_type": file_type,
                "content_order": content_order,
            }

