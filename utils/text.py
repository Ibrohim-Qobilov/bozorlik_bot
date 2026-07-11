"""Matn bilan ishlash: narxni ajratish va formatlash."""
import re

# Menyu tugmalari boshidagi emojilar (FSM ichida menyu bosilganini aniqlash uchun)
# 🌐 — eski menyudagi «Til» tugmasi uchun ham qoladi
MENU_EMOJIS = ("🛒", "📋", "⚙️", "🌐")

# Ming/million qisqartmalari — narxdan keyin kelishi mumkin
_MULTIPLIERS = {
    "ming": 1_000, "минг": 1_000, "мың": 1_000, "миң": 1_000,
    "тыс": 1_000, "ҳазор": 1_000, "hazor": 1_000, "bin": 1_000,
    "k": 1_000, "к": 1_000,
    "mln": 1_000_000, "млн": 1_000_000,
}
_NUM = r"\d[\d\s.,]*"
_MULT = r"ming|минг|мың|миң|тыс|ҳазор|hazor|bin|mln|млн|k|к"
_CUR = r"so'?m|som|sum|soum|сум|сўм|сом"

# Faqat narxning o'zi: "12 000", "85 ming", "12k so'm"
_PRICE_ONLY = re.compile(
    rf"^\s*(?P<num>{_NUM})\s*(?P<mult>{_MULT})?\.?\s*(?P<cur>{_CUR})?\s*$",
    re.IGNORECASE,
)
# Qator oxiridagi narx: "Non 5000", "Go'sht - 85 ming", "Sut: 12.000 so'm"
_PRICE_TAIL = re.compile(
    rf"^(?P<name>.+?)[\s\-—:]+(?P<num>{_NUM})\s*(?P<mult>{_MULT})?\.?\s*(?P<cur>{_CUR})?\s*$",
    re.IGNORECASE,
)

MAX_PRICE = 1_000_000_000_000  # aql bovar qilmas narxlardan himoya


def fmt_amount(n):
    """12345678 -> «12 345 678» (mingliklar bo'shliq bilan)."""
    return f"{n:,}".replace(",", " ")


def _to_price(num, mult):
    """Regex bo'laklaridan butun narx yasaydi. Yaroqsiz bo'lsa None."""
    num = (num or "").strip()
    if not num:
        return None
    if mult:
        # «1,5 ming» — vergul/nuqta o'nlik ayirgich
        cleaned = num.replace(" ", "").replace(",", ".")
        if cleaned.count(".") > 1:  # «1.200.300» — minglik ayirgichlar
            cleaned = cleaned.replace(".", "")
        try:
            value = float(cleaned) * _MULTIPLIERS[mult.lower()]
        except ValueError:
            return None
    else:
        digits = re.sub(r"\D", "", num)
        if not digits:
            return None
        value = int(digits)
    price = int(round(value))
    if price <= 0 or price > MAX_PRICE:
        return None
    return price


def parse_price(text):
    """Narx matnini butun songa aylantiradi. Yaroqsiz bo'lsa None.

    "12 000", "12.000 so'm", "85 ming", "12k" -> 12000, 12000, 85000, 12000
    """
    m = _PRICE_ONLY.match(text or "")
    if not m:
        return None
    return _to_price(m.group("num"), m.group("mult"))


# Miqdor belgisi: "Non x2", "Non ×2", "2x Non" emas — nom oxirida
_QTY_TAIL = re.compile(
    r"^(?P<name>.+?)\s*(?:[x×](?P<q1>\d{1,3})|(?P<q2>\d{1,3})\s*(?:ta|dona|шт|adet|та))\s*$",
    re.IGNORECASE,
)


def _split_qty(name):
    """Nom oxiridagi miqdorni ajratadi: "Non x2" -> ("Non", 2)."""
    m = _QTY_TAIL.match(name)
    if not m:
        return name, 1
    qty = int(m.group("q1") or m.group("q2"))
    if qty < 1 or qty > 999:
        return name, 1
    clean = m.group("name").strip()
    return (clean, qty) if clean else (name, 1)


def parse_item_line(line):
    """Bitta qatordan (nom, narx, miqdor) ni ajratadi.

    Qator oxiridagi son narx deb olinadi: "Non 5000" -> ("Non", 5000, 1).
    "ming/so'm" kabi so'z bilan kelsa — aniq narx: "Go'sht 85 ming" -> 85000.
    Yolg'iz kichik son (100 dan kam) — miqdor emas, nomda qoladi: "Olma 3".
    Miqdor "x" bilan yoziladi: "Non x2 5000" -> ("Non", 5000, 2).
    """
    line = line.strip()
    if not line:
        return None
    m = _PRICE_TAIL.match(line)
    if m:
        price = _to_price(m.group("num"), m.group("mult"))
        explicit = bool(m.group("mult") or m.group("cur"))
        if price is not None and (explicit or price >= 100):
            name, qty = _split_qty(m.group("name").strip())
            return name, price, qty
    name, qty = _split_qty(line)
    return name, None, qty


def parse_items(text):
    """Xabar matnidan mahsulotlar ro'yxatini yig'adi (har qator — bitta)."""
    items = []
    for line in (text or "").splitlines():
        parsed = parse_item_line(line)
        if parsed:
            name, price, qty = parsed
            items.append((truncate(name, 64), price, qty))
    return items


def truncate(s, limit):
    """Uzun matnni «…» bilan qisqartiradi (tugma/nom uchun)."""
    s = s.strip()
    return s if len(s) <= limit else s[: limit - 1] + "…"


# Eslatma vaqti: "18:30" yoki "12.07 09:00"
_WHEN_TIME = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*$")
_WHEN_DATE = re.compile(r"^\s*(\d{1,2})\.(\d{1,2})\.?\s+(\d{1,2}):(\d{2})\s*$")


def parse_when(text, now):
    """Eslatma vaqtini datetime ga aylantiradi (mahalliy vaqt).

    "18:30" — bugun (o'tgan bo'lsa ertaga); "12.07 09:00" — shu yil
    (o'tgan bo'lsa kelasi yil). Tushunarsiz bo'lsa None.
    """
    from datetime import datetime, timedelta

    m = _WHEN_TIME.match(text or "")
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        if hour > 23 or minute > 59:
            return None
        when = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if when <= now:
            when += timedelta(days=1)
        return when

    m = _WHEN_DATE.match(text or "")
    if m:
        day, month = int(m.group(1)), int(m.group(2))
        hour, minute = int(m.group(3)), int(m.group(4))
        try:
            when = datetime(now.year, month, day, hour, minute)
        except ValueError:
            return None
        if when <= now:
            try:
                when = when.replace(year=now.year + 1)
            except ValueError:  # 29-fevral
                return None
        return when

    return None
