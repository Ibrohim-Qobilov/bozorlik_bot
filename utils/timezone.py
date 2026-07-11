"""Vaqt mintaqasi: har foydalanuvchiga UTC'dan siljish (offset, daqiqada).

Eslatmalar bazada har doim UTC'da saqlanadi; kiritishda mahalliy vaqt UTC'ga,
ko'rsatishda UTC mahalliy vaqtga aylantiriladi. Shu sabab bot ishlayotgan
serverning vaqt mintaqasiga umuman bog'liq bo'lmaydi.

Markaziy Osiyo va Turkiya/Rossiya yozgi vaqtga o'tmaydi — shuning uchun oddiy,
qat'iy siljish (butun soat) yetarli, DST hisobi kerak emas.
"""
from datetime import datetime, timedelta

_FMT = "%Y-%m-%d %H:%M"

# Standart siljish — noma'lum til uchun (Toshkent).
DEFAULT_TZ = 300  # daqiqa (UTC+5)

# Til -> standart vaqt mintaqasi (foydalanuvchi o'zi tanlamaguncha).
LANG_TZ = {
    "uz": 300,      # 🇺🇿 Toshkent
    "uz_cyr": 300,
    "ru": 180,      # 🇷🇺 Moskva
    "en": 300,      # mintaqaviy bot — standart Toshkent
    "kk": 300,      # 🇰🇿 Almati
    "tg": 300,      # 🇹🇯 Dushanbe
    "tr": 180,      # 🇹🇷 Anqara
    "ky": 360,      # 🇰🇬 Bishkek
}

# Tanlash klaviaturasi uchun: (siljish_daqiqa, ko'rinadigan yorliq).
TIMEZONES = [
    (180, "🇹🇷 Anqara · 🇷🇺 Moskva (UTC+3)"),
    (240, "🇦🇿 Boku (UTC+4)"),
    (300, "🇺🇿 Toshkent · 🇰🇿 Almati · 🇹🇯 Dushanbe (UTC+5)"),
    (360, "🇰🇬 Bishkek (UTC+6)"),
]

# Yaroqli siljishlar to'plami (tashqi kiritmani tekshirish uchun).
VALID_OFFSETS = {minutes for minutes, _ in TIMEZONES}


def default_tz(lang):
    """Til bo'yicha standart siljishni qaytaradi."""
    return LANG_TZ.get(lang, DEFAULT_TZ)


def local_now(tz_min):
    """Foydalanuvchi mahalliy vaqtidagi hozirgi payt (naiv datetime)."""
    return datetime.utcnow() + timedelta(minutes=tz_min)


def to_utc(local_dt, tz_min):
    """Mahalliy vaqtni UTC'ga aylantiradi (saqlashdan oldin)."""
    return local_dt - timedelta(minutes=tz_min)


def to_local(utc_dt, tz_min):
    """UTC vaqtni mahalliy vaqtga aylantiradi (ko'rsatishdan oldin)."""
    return utc_dt + timedelta(minutes=tz_min)


def utc_str_to_local(s, tz_min, out="%d.%m %H:%M"):
    """Saqlangan UTC satrini ("YYYY-MM-DD HH:MM") mahalliy yorliqqa aylantiradi.

    Buzuq satr bo'lsa — o'zini qaytaradi (hech qachon yiqilmaydi).
    """
    try:
        dt = datetime.strptime(s, _FMT) + timedelta(minutes=tz_min)
    except (ValueError, TypeError):
        return s
    return dt.strftime(out)


def sqlite_modifier(tz_min):
    """SQLite `datetime(...)` uchun siljish modifikatori: "+300 minutes"."""
    sign = "+" if tz_min >= 0 else "-"
    return f"{sign}{abs(tz_min)} minutes"


def utc_label(tz_min):
    """Qisqa yorliq: 300 -> "UTC+5", -90 -> "UTC-1:30"."""
    hours, minutes = divmod(abs(tz_min), 60)
    sign = "+" if tz_min >= 0 else "-"
    tail = f":{minutes:02d}" if minutes else ""
    return f"UTC{sign}{hours}{tail}"
