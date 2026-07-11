"""Ko'p tilli matnlar.

Har bir til alohida modulda (`uz.py`, `ru.py`, ...) `TEXTS` lug'ati sifatida
saqlanadi. Bu yerda ular yig'iladi va `t()` funksiyasi orqali beriladi.
"""
from . import uz, uz_cyr, ru, en, kk, tg, tr, ky

# kod -> matnlar lug'ati
TEXTS = {
    "uz": uz.TEXTS,
    "uz_cyr": uz_cyr.TEXTS,
    "ru": ru.TEXTS,
    "en": en.TEXTS,
    "kk": kk.TEXTS,
    "tg": tg.TEXTS,
    "tr": tr.TEXTS,
    "ky": ky.TEXTS,
}

# Til tanlash klaviaturasi uchun: (kod, ko'rinadigan nom)
LANGUAGES = [
    ("uz", "🇺🇿 O'zbekcha"),
    ("uz_cyr", "🇺🇿 Ўзбекча"),
    ("ru", "🇷🇺 Русский"),
    ("en", "🇬🇧 English"),
    ("kk", "🇰🇿 Қазақша"),
    ("tg", "🇹🇯 Тоҷикӣ"),
    ("tr", "🇹🇷 Türkçe"),
    ("ky", "🇰🇬 Кыргызча"),
]

DEFAULT_LANG = "uz"
FALLBACK_LANG = "en"


def t(lang, key):
    """`lang` tilida `key` matnini qaytaradi.

    Topilmasa: inglizcha -> o'zbekcha -> kalitning o'zi (zaxira).
    """
    d = TEXTS.get(lang)
    if d and key in d:
        return d[key]
    return TEXTS[FALLBACK_LANG].get(key, TEXTS[DEFAULT_LANG].get(key, key))
