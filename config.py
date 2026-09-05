"""Sozlamalar — barcha maxfiy qiymatlar `.env` faylidan o'qiladi."""
import os

from dotenv import load_dotenv

load_dotenv()


def _required(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"«{name}» muhit o'zgaruvchisi topilmadi. "
            f".env faylini to'ldiring (.env.example ga qarang)."
        )
    return value


BOT_TOKEN = _required("BOT_TOKEN")
DB_PATH = os.getenv("DB_PATH", "bozorlik.db")
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL", "")

# Bitta ro'yxatdagi mahsulotlar soni chegarasi
# (Telegram inline klaviaturasi ~100 tugma ko'taradi — zaxira bilan 50)
MAX_ITEMS = 50
