"""SQLite bilan ishlash: foydalanuvchilar, ro'yxatlar, a'zolar, mahsulotlar."""
import secrets

import aiosqlite

from config import DB_PATH
from utils.timezone import default_tz, sqlite_modifier


async def _ensure_column(db, table, column, coltype):
    """Eski bazaga yetishmayotgan ustunni qo'shadi (migratsiya)."""
    async with db.execute(f"PRAGMA table_info({table})") as cur:
        columns = [row[1] for row in await cur.fetchall()]
    if column not in columns:
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                lang    TEXT DEFAULT 'uz',
                name    TEXT,
                tz      INTEGER
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS lists (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id      INTEGER,
                name          TEXT,
                code          TEXT UNIQUE,
                done_notified INTEGER DEFAULT 0,
                budget        INTEGER,
                created_at    TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS members (
                list_id INTEGER,
                user_id INTEGER,
                PRIMARY KEY (list_id, user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                list_id   INTEGER,
                name      TEXT,
                price     INTEGER,
                qty       INTEGER DEFAULT 1,
                bought    INTEGER DEFAULT 0,
                bought_by INTEGER,
                bought_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                list_id INTEGER,
                user_id INTEGER,
                at      TEXT,
                repeat  TEXT,
                sent    INTEGER DEFAULT 0
            )
        """)
        # eski bazalar uchun migratsiya
        await _ensure_column(db, "users", "name", "TEXT")
        await _ensure_column(db, "users", "tz", "INTEGER")
        await _ensure_column(db, "lists", "budget", "INTEGER")
        await _ensure_column(db, "items", "bought_at", "TEXT")
        await _ensure_column(db, "items", "qty", "INTEGER DEFAULT 1")
        await _ensure_column(db, "reminders", "repeat", "TEXT")
        await db.commit()


# ---------- til ----------

async def user_exists(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)) as cur:
            return await cur.fetchone() is not None


async def set_lang(user_id, lang):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO users (user_id, lang) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET lang = ?",
            (user_id, lang, lang),
        )
        await db.commit()


async def get_lang(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else "uz"


# ---------- vaqt mintaqasi ----------

async def get_tz(user_id):
    """Foydalanuvchi UTC siljishi (daqiqa).

    O'zi tanlamagan bo'lsa — tili bo'yicha standart (uz -> +5, tr -> +3 ...).
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT lang, tz FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
    if not row:
        return default_tz("uz")
    lang, tz = row
    return tz if tz is not None else default_tz(lang or "uz")


async def set_tz(user_id, tz_min):
    """Foydalanuvchi vaqt mintaqasini o'rnatadi (daqiqada UTC siljish)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO users (user_id, tz) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET tz = ?",
            (user_id, tz_min, tz_min),
        )
        await db.commit()


async def set_user_name(user_id, name):
    """Foydalanuvchi ismini yangilaydi («kim oldi» ko'rinishi uchun)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO users (user_id, name) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET name = ?",
            (user_id, name, name),
        )
        await db.commit()


async def get_user_names(user_ids):
    """{user_id: name} — faqat ismi ma'lum bo'lganlar."""
    if not user_ids:
        return {}
    marks = ",".join("?" * len(user_ids))
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            f"SELECT user_id, name FROM users WHERE user_id IN ({marks})", tuple(user_ids)
        ) as cur:
            rows = await cur.fetchall()
    return {r[0]: r[1] for r in rows if r[1]}


# ---------- ro'yxatlar ----------

def _list_row(row):
    return {
        "id": row[0], "owner_id": row[1], "name": row[2],
        "code": row[3], "done_notified": row[4], "budget": row[5],
    }


async def create_list(owner_id, name):
    """Yangi ro'yxat ochadi, egasini a'zo qilib qo'shadi. `id` qaytaradi."""
    async with aiosqlite.connect(DB_PATH) as db:
        while True:
            code = secrets.token_urlsafe(6)
            async with db.execute("SELECT 1 FROM lists WHERE code = ?", (code,)) as cur:
                if await cur.fetchone() is None:
                    break
        cur = await db.execute(
            "INSERT INTO lists (owner_id, name, code) VALUES (?, ?, ?)",
            (owner_id, name, code),
        )
        list_id = cur.lastrowid
        await db.execute(
            "INSERT OR IGNORE INTO members (list_id, user_id) VALUES (?, ?)",
            (list_id, owner_id),
        )
        await db.commit()
        return list_id


_LIST_COLS = "id, owner_id, name, code, done_notified, budget"


async def get_list(list_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            f"SELECT {_LIST_COLS} FROM lists WHERE id = ?", (list_id,)
        ) as cur:
            row = await cur.fetchone()
            return _list_row(row) if row else None


async def get_list_by_code(code):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            f"SELECT {_LIST_COLS} FROM lists WHERE code = ?", (code,)
        ) as cur:
            row = await cur.fetchone()
            return _list_row(row) if row else None


async def get_user_lists(user_id):
    """Foydalanuvchi a'zo bo'lgan ro'yxatlar + olingan/jami sanoq va summa."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT l.id, l.name,
                   COUNT(i.id)                AS total,
                   COALESCE(SUM(i.bought), 0) AS done,
                   COALESCE(SUM(i.price), 0)  AS sum
            FROM lists l
            JOIN members m ON m.list_id = l.id AND m.user_id = ?
            LEFT JOIN items i ON i.list_id = l.id
            GROUP BY l.id
            ORDER BY l.id DESC
            """,
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
    return [
        {"id": r[0], "name": r[1], "total": r[2], "done": r[3], "sum": r[4]}
        for r in rows
    ]


async def update_list_name(list_id, name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE lists SET name = ? WHERE id = ?", (name, list_id))
        await db.commit()


async def delete_list(list_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM items WHERE list_id = ?", (list_id,))
        await db.execute("DELETE FROM members WHERE list_id = ?", (list_id,))
        await db.execute("DELETE FROM lists WHERE id = ?", (list_id,))
        await db.commit()


async def set_done_notified(list_id, flag):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE lists SET done_notified = ? WHERE id = ?", (1 if flag else 0, list_id)
        )
        await db.commit()


async def set_budget(list_id, amount):
    """Ro'yxat byudjetini o'rnatadi (None — o'chiradi)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE lists SET budget = ? WHERE id = ?", (amount, list_id))
        await db.commit()


# ---------- a'zolar ----------

async def add_member(list_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO members (list_id, user_id) VALUES (?, ?)",
            (list_id, user_id),
        )
        await db.commit()


async def is_member(list_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM members WHERE list_id = ? AND user_id = ?", (list_id, user_id)
        ) as cur:
            return await cur.fetchone() is not None


async def get_members(list_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM members WHERE list_id = ?", (list_id,)
        ) as cur:
            rows = await cur.fetchall()
    return [r[0] for r in rows]


async def count_members(list_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM members WHERE list_id = ?", (list_id,)
        ) as cur:
            (n,) = await cur.fetchone()
            return n


async def remove_member(list_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM members WHERE list_id = ? AND user_id = ?", (list_id, user_id)
        )
        await db.commit()


# ---------- mahsulotlar ----------

def _item_row(row):
    return {
        "id": row[0], "list_id": row[1], "name": row[2],
        "price": row[3], "qty": row[4] or 1,
        "bought": bool(row[5]), "bought_by": row[6],
    }


_ITEM_COLS = "id, list_id, name, price, qty, bought, bought_by"


async def add_item(list_id, name, price=None, qty=1):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO items (list_id, name, price, qty) VALUES (?, ?, ?, ?)",
            (list_id, name, price, qty),
        )
        await db.commit()
        return cur.lastrowid


async def update_item_name(item_id, name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE items SET name = ? WHERE id = ?", (name, item_id))
        await db.commit()


async def update_item_price(item_id, price):
    """Narxni yangilaydi (None — narxni olib tashlaydi)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE items SET price = ? WHERE id = ?", (price, item_id))
        await db.commit()


async def last_price(user_id, name):
    """Foydalanuvchi ro'yxatlaridagi shu nomdagi mahsulotning oxirgi narxi."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT i.price FROM items i
            JOIN members m ON m.list_id = i.list_id AND m.user_id = ?
            WHERE LOWER(i.name) = LOWER(?) AND i.price IS NOT NULL
            ORDER BY i.id DESC LIMIT 1
            """,
            (user_id, name),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def duplicate_list(list_id, owner_id):
    """Ro'yxat nusxasini ochadi: mahsulotlar (belgisiz) va a'zolar ko'chadi."""
    src = await get_list(list_id)
    if not src:
        return None
    new_id = await create_list(owner_id, src["name"])
    for uid in await get_members(list_id):
        await add_member(new_id, uid)
    for item in await get_items(list_id):
        await add_item(new_id, item["name"], item["price"], item["qty"])
    return new_id


async def count_items(list_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM items WHERE list_id = ?", (list_id,)
        ) as cur:
            (n,) = await cur.fetchone()
            return n


async def get_items(list_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            f"SELECT {_ITEM_COLS} FROM items WHERE list_id = ? ORDER BY id", (list_id,)
        ) as cur:
            rows = await cur.fetchall()
    return [_item_row(r) for r in rows]


async def get_item(item_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            f"SELECT {_ITEM_COLS} FROM items WHERE id = ?", (item_id,)
        ) as cur:
            row = await cur.fetchone()
            return _item_row(row) if row else None


async def set_bought(item_id, user_id, price=None):
    """Mahsulotni «olindi» qiladi; narx berilsa, uni ham yozadi."""
    async with aiosqlite.connect(DB_PATH) as db:
        if price is None:
            await db.execute(
                "UPDATE items SET bought = 1, bought_by = ?, bought_at = datetime('now') "
                "WHERE id = ?",
                (user_id, item_id),
            )
        else:
            await db.execute(
                "UPDATE items SET bought = 1, bought_by = ?, bought_at = datetime('now'), "
                "price = ? WHERE id = ?",
                (user_id, price, item_id),
            )
        await db.commit()


async def set_unbought(item_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE items SET bought = 0, bought_by = NULL, bought_at = NULL WHERE id = ?",
            (item_id,),
        )
        await db.commit()


async def delete_item(item_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM items WHERE id = ?", (item_id,))
        await db.commit()


async def member_spending(list_id):
    """Har bir a'zo nechta mahsulot olgani va qancha sarflagani.

    [(user_id, soni, summasi)] — eng ko'p sarflagan birinchi.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT bought_by, COUNT(*), COALESCE(SUM(price), 0)
            FROM items
            WHERE list_id = ? AND bought = 1 AND bought_by IS NOT NULL
            GROUP BY bought_by
            ORDER BY 3 DESC, 2 DESC
            """,
            (list_id,),
        ) as cur:
            rows = await cur.fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


async def frequent_items(user_id, exclude_list_id, limit=8):
    """Foydalanuvchi ro'yxatlaridagi eng ko'p uchraydigan mahsulot nomlari.

    Joriy ro'yxatda allaqachon bor nomlar chiqarilmaydi.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT i.name, COUNT(*) AS c
            FROM items i
            JOIN members m ON m.list_id = i.list_id AND m.user_id = ?
            WHERE LOWER(i.name) NOT IN (
                SELECT LOWER(name) FROM items WHERE list_id = ?
            )
            GROUP BY LOWER(i.name)
            ORDER BY c DESC, MAX(i.id) DESC
            LIMIT ?
            """,
            (user_id, exclude_list_id, limit),
        ) as cur:
            rows = await cur.fetchall()
    return [r[0] for r in rows]


# ---------- statistika ----------

async def month_stats(user_id, month, tz_min=0):
    """`month` ("YYYY-MM", mahalliy) uchun statistika.

    Oy chegarasi foydalanuvchi vaqt mintaqasida hisoblanadi (`tz_min` — UTC
    siljish). Foydalanuvchi a'zo bo'lgan ro'yxatlardagi barcha xaridlar kiradi.
    """
    mod = sqlite_modifier(tz_min)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT COUNT(*), COALESCE(SUM(i.price), 0)
            FROM items i
            JOIN members m ON m.list_id = i.list_id AND m.user_id = ?
            WHERE i.bought = 1 AND strftime('%Y-%m', datetime(i.bought_at, ?)) = ?
            """,
            (user_id, mod, month),
        ) as cur:
            items_count, total = await cur.fetchone()
        async with db.execute(
            """
            SELECT COALESCE(SUM(i.price), 0)
            FROM items i
            JOIN members m ON m.list_id = i.list_id AND m.user_id = ?
            WHERE i.bought = 1 AND i.bought_by = ?
              AND strftime('%Y-%m', datetime(i.bought_at, ?)) = ?
            """,
            (user_id, user_id, mod, month),
        ) as cur:
            (own,) = await cur.fetchone()
        async with db.execute(
            "SELECT COUNT(*) FROM lists WHERE owner_id = ? "
            "AND strftime('%Y-%m', datetime(created_at, ?)) = ?",
            (user_id, mod, month),
        ) as cur:
            (lists_count,) = await cur.fetchone()
        async with db.execute(
            """
            SELECT i.name, i.price
            FROM items i
            JOIN members m ON m.list_id = i.list_id AND m.user_id = ?
            WHERE i.bought = 1 AND i.price IS NOT NULL
              AND strftime('%Y-%m', datetime(i.bought_at, ?)) = ?
            ORDER BY i.price DESC
            LIMIT 5
            """,
            (user_id, mod, month),
        ) as cur:
            top = [{"name": r[0], "price": r[1]} for r in await cur.fetchall()]
    return {
        "items": items_count, "total": total, "own": own,
        "lists": lists_count, "top": top,
    }


async def monthly_totals(user_id, months=6, tz_min=0):
    """Oxirgi oylar bo'yicha xarajat: [("YYYY-MM", summa), ...] (yangi birinchi).

    Oy chegarasi foydalanuvchi vaqt mintaqasida (`tz_min` — UTC siljish).
    """
    mod = sqlite_modifier(tz_min)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT strftime('%Y-%m', datetime(i.bought_at, ?)) AS ym,
                   COALESCE(SUM(i.price), 0)
            FROM items i
            JOIN members m ON m.list_id = i.list_id AND m.user_id = ?
            WHERE i.bought = 1 AND i.bought_at IS NOT NULL AND i.price IS NOT NULL
            GROUP BY ym
            ORDER BY ym DESC
            LIMIT ?
            """,
            (mod, user_id, months),
        ) as cur:
            rows = await cur.fetchall()
    return [(r[0], r[1]) for r in rows]


# ---------- eslatmalar ----------

async def add_reminder(list_id, user_id, at):
    """`at` — "YYYY-MM-DD HH:MM" (mahalliy vaqt). Eslatma `id` sini qaytaradi."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO reminders (list_id, user_id, at) VALUES (?, ?, ?)",
            (list_id, user_id, at),
        )
        await db.commit()
        return cur.lastrowid


async def set_reminder_repeat(reminder_id, user_id, repeat):
    """Takrorni yoqadi/o'chiradi ('weekly' yoki None). Faqat egasi uchun."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE reminders SET repeat = ? WHERE id = ? AND user_id = ?",
            (repeat, reminder_id, user_id),
        )
        await db.commit()


async def get_reminder(reminder_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, list_id, user_id, at, repeat, sent FROM reminders WHERE id = ?",
            (reminder_id,),
        ) as cur:
            r = await cur.fetchone()
    if not r:
        return None
    return {"id": r[0], "list_id": r[1], "user_id": r[2], "at": r[3], "repeat": r[4], "sent": r[5]}


async def user_reminders(user_id):
    """Foydalanuvchining faol eslatmalari (ro'yxat nomi bilan)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT r.id, r.at, r.repeat, l.name
            FROM reminders r JOIN lists l ON l.id = r.list_id
            WHERE r.user_id = ? AND r.sent = 0
            ORDER BY r.at
            """,
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
    return [{"id": r[0], "at": r[1], "repeat": r[2], "list_name": r[3]} for r in rows]


async def delete_reminder(reminder_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM reminders WHERE id = ? AND user_id = ?", (reminder_id, user_id)
        )
        await db.commit()


async def due_reminders(now):
    """Vaqti kelgan, hali yuborilmagan eslatmalar."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, list_id, user_id, at, repeat FROM reminders "
            "WHERE sent = 0 AND at <= ?",
            (now,),
        ) as cur:
            rows = await cur.fetchall()
    return [
        {"id": r[0], "list_id": r[1], "user_id": r[2], "at": r[3], "repeat": r[4]}
        for r in rows
    ]


async def bump_reminder(reminder_id, new_at):
    """Takroriy eslatmani keyingi vaqtga suradi (sent=0 qoladi)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE reminders SET at = ? WHERE id = ?", (new_at, reminder_id)
        )
        await db.commit()


async def mark_reminder_sent(reminder_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))
        await db.commit()
