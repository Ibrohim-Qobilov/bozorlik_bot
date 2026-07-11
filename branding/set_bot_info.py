"""Bot nomi, tavsifi va buyruqlarini barcha tillarda o'rnatadi.

Bir marta ishga tushiriladi (matn o'zgarsa — qayta):

    python3 branding/set_bot_info.py

Eslatmalar:
- Rasmlarni API o'rnatolmaydi — @BotFather orqali qo'lda yuklanadi
  (qarang: branding/BOTFATHER.md).
- `uz_cyr` Telegramda alohida til kodiga ega emas (mijozlar o'zbekcha uchun
  `uz` yuboradi), shuning uchun bu skriptda faqat lotincha o'rnatiladi.
- Bot nomini Telegram tez-tez o'zgartirishga ruxsat bermaydi — 429 xato
  chiqsa, skript uni o'tkazib yuborib davom etadi.
"""
import asyncio
import sys
from pathlib import Path

# Loyiha ildizini import yo'liga qo'shamiz (skript branding/ ichida turadi)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import BotCommand

from config import BOT_TOKEN

# Telegram cheklovlari (UTF-16 birliklarida)
MAX_NAME = 64
MAX_SHORT = 120
MAX_DESC = 512

# til kodi (None — standart, ya'ni ro'yxatda yo'q tillar uchun) -> matnlar
BOT_INFO = {
    None: "uz",  # standart til — o'zbekcha (lotin)
    "uz": {
        "name": "Bozorlik — oilaviy xarid ro'yxati 🛒",
        "short": "Oilaviy bozorlik ro'yxati: birga tuzing, ✅ belgilang, "
                 "xarajatni hisoblang. 8 til, guruh va inline rejim.",
        "description": (
            "🛒 Bozorlik — oilaviy xarid ro'yxati boti.\n"
            "\n"
            "• Ro'yxat tuzing — mahsulotni narxi bilan ham yozish mumkin: «Non 5000»\n"
            "• 👥 Havola orqali yaqinlaringiz bilan ulashing — hamma bitta ro'yxatni ko'radi\n"
            "• ✅ Olinganini belgilang — bot sarflangan summani hisoblab boradi\n"
            "• 💰 Byudjet qo'ying — oshib ketsa ogohlantiradi\n"
            "• ⏰ Eslatma (haftalik ham), 📊 oylik hisobot, 💾 zaxira nusxa\n"
            "• Guruhda /list, istalgan chatda inline rejim\n"
            "• 🌐 8 til\n"
            "\n"
            "Boshlash uchun /start bosing 👇"
        ),
        "commands": [
            ("new", "🛒 Yangi ro'yxat"),
            ("lists", "📋 Ro'yxatlarim"),
            ("list", "👥 Guruhda ro'yxatni ochish"),
            ("start", "▶️ Boshlash"),
        ],
    },
    "ru": {
        "name": "Bozorlik — семейный список покупок 🛒",
        "short": "Семейный список покупок: составляйте вместе, отмечайте ✅, "
                 "считайте расходы. 8 языков, группы и inline-режим.",
        "description": (
            "🛒 Bozorlik — бот для семейного списка покупок.\n"
            "\n"
            "• Составьте список — можно сразу с ценой: «Хлеб 5000»\n"
            "• 👥 Поделитесь ссылкой с близкими — все видят один список\n"
            "• ✅ Отмечайте купленное — бот считает потраченную сумму\n"
            "• 💰 Задайте бюджет — предупредит о превышении\n"
            "• ⏰ Напоминания (и еженедельные), 📊 отчёт за месяц, 💾 резервная копия\n"
            "• /list в группе, inline-режим в любом чате\n"
            "• 🌐 8 языков\n"
            "\n"
            "Нажмите /start, чтобы начать 👇"
        ),
        "commands": [
            ("new", "🛒 Новый список"),
            ("lists", "📋 Мои списки"),
            ("list", "👥 Открыть список в группе"),
            ("start", "▶️ Начать"),
        ],
    },
    "en": {
        "name": "Bozorlik — family shopping list 🛒",
        "short": "Family shopping list: build it together, tick items ✅, "
                 "track spending. 8 languages, groups and inline mode.",
        "description": (
            "🛒 Bozorlik — a family shopping list bot.\n"
            "\n"
            "• Build a list — add prices right away: “Bread 5000”\n"
            "• 👥 Share a link with your family — everyone sees one list\n"
            "• ✅ Tick items as you buy — the bot totals the spending\n"
            "• 💰 Set a budget — it warns you when you go over\n"
            "• ⏰ Reminders (weekly too), 📊 monthly report, 💾 backups\n"
            "• /list in groups, inline mode in any chat\n"
            "• 🌐 8 languages\n"
            "\n"
            "Tap /start to begin 👇"
        ),
        "commands": [
            ("new", "🛒 New list"),
            ("lists", "📋 My lists"),
            ("list", "👥 Open the list in a group"),
            ("start", "▶️ Start"),
        ],
    },
    "kk": {
        "name": "Bozorlik — отбасылық сауда тізімі 🛒",
        "short": "Отбасылық сауда тізімі: бірге құрыңыз, ✅ белгілеңіз, "
                 "шығынды есептеңіз. 8 тіл, топтар және inline режим.",
        "description": (
            "🛒 Bozorlik — отбасылық сауда тізімі боты.\n"
            "\n"
            "• Тізім құрыңыз — бірден бағасымен жазуға болады: «Нан 5000»\n"
            "• 👥 Сілтемемен жақындарыңызбен бөлісіңіз — бәрі бір тізімді көреді\n"
            "• ✅ Алынғанды белгілеңіз — бот жұмсалған соманы есептейді\n"
            "• 💰 Бюджет қойыңыз — асып кетсе ескертеді\n"
            "• ⏰ Еске салу (апта сайын да), 📊 айлық есеп, 💾 сақтық көшірме\n"
            "• Топта /list, кез келген чатта inline режим\n"
            "• 🌐 8 тіл\n"
            "\n"
            "Бастау үшін /start басыңыз 👇"
        ),
        "commands": [
            ("new", "🛒 Жаңа тізім"),
            ("lists", "📋 Менің тізімдерім"),
            ("list", "👥 Топта тізімді ашу"),
            ("start", "▶️ Бастау"),
        ],
    },
    "tg": {
        "name": "Bozorlik — рӯйхати хариди оилавӣ 🛒",
        "short": "Рӯйхати хариди оилавӣ: якҷоя месозед, ✅ қайд мекунед, бот "
                 "харҷро ҳисоб мекунад. 8 забон, гурӯҳ ва inline.",
        "description": (
            "🛒 Bozorlik — боти рӯйхати хариди оилавӣ.\n"
            "\n"
            "• Рӯйхат созед — якбора бо нарх навиштан мумкин: «Нон 5000»\n"
            "• 👥 Пайвандро бо наздиконатон мубодила кунед — ҳама як рӯйхатро мебинанд\n"
            "• ✅ Чизи харидашударо қайд кунед — бот харҷи умумиро ҳисоб мекунад\n"
            "• 💰 Буҷет гузоред — аз ҳад гузарад, огоҳ мекунад\n"
            "• ⏰ Ёдрасонӣ (ҳафтаина ҳам), 📊 ҳисоботи моҳона, 💾 нусхаи эҳтиётӣ\n"
            "• Дар гурӯҳ /list, дар ҳар чат inline режим\n"
            "• 🌐 8 забон\n"
            "\n"
            "Барои оғоз /start-ро пахш кунед 👇"
        ),
        "commands": [
            ("new", "🛒 Рӯйхати нав"),
            ("lists", "📋 Рӯйхатҳои ман"),
            ("list", "👥 Кушодани рӯйхат дар гурӯҳ"),
            ("start", "▶️ Оғоз"),
        ],
    },
    "tr": {
        "name": "Bozorlik — aile alışveriş listesi 🛒",
        "short": "Aile alışveriş listesi: birlikte oluşturun, ✅ işaretleyin, "
                 "harcamayı takip edin. 8 dil, grup ve inline mod.",
        "description": (
            "🛒 Bozorlik — aile alışveriş listesi botu.\n"
            "\n"
            "• Liste oluşturun — fiyatıyla birlikte de yazabilirsiniz: «Ekmek 5000»\n"
            "• 👥 Bağlantıyı yakınlarınızla paylaşın — herkes aynı listeyi görür\n"
            "• ✅ Aldıklarınızı işaretleyin — bot toplam harcamayı hesaplar\n"
            "• 💰 Bütçe belirleyin — aşarsanız uyarır\n"
            "• ⏰ Hatırlatıcı (haftalık da), 📊 aylık rapor, 💾 yedekleme\n"
            "• Grupta /list, her sohbette inline mod\n"
            "• 🌐 8 dil\n"
            "\n"
            "Başlamak için /start'a dokunun 👇"
        ),
        "commands": [
            ("new", "🛒 Yeni liste"),
            ("lists", "📋 Listelerim"),
            ("list", "👥 Grupta listeyi aç"),
            ("start", "▶️ Başla"),
        ],
    },
    "ky": {
        "name": "Bozorlik — үй-бүлөлүк базарлык тизмеси 🛒",
        "short": "Үй-бүлөлүк базарлык тизмеси: чогуу түзүңүз, ✅ белгилеңиз, "
                 "чыгымды эсептеңиз. 8 тил, топ жана inline режим.",
        "description": (
            "🛒 Bozorlik — үй-бүлөлүк базарлык тизмеси боту.\n"
            "\n"
            "• Тизме түзүңүз — баасы менен да жазса болот: «Нан 5000»\n"
            "• 👥 Шилтемени жакындарыңыз менен бөлүшүңүз — баары бир тизмени көрөт\n"
            "• ✅ Алынганын белгилеңиз — бот жумшалган сумманы эсептейт\n"
            "• 💰 Бюджет коюңуз — ашып кетсе эскертет\n"
            "• ⏰ Эскертме (жума сайын да), 📊 айлык отчёт, 💾 камдык көчүрмө\n"
            "• Топто /list, каалаган чатта inline режим\n"
            "• 🌐 8 тил\n"
            "\n"
            "Баштоо үчүн /start басыңыз 👇"
        ),
        "commands": [
            ("new", "🛒 Жаңы тизме"),
            ("lists", "📋 Менин тизмелерим"),
            ("list", "👥 Топто тизмени ачуу"),
            ("start", "▶️ Баштоо"),
        ],
    },
}


def _u16len(s):
    """Telegram uzunlikni UTF-16 birliklarida sanaydi (emoji ba'zan 2 birlik)."""
    return len(s.encode("utf-16-le")) // 2


def check_limits():
    """Barcha matnlar Telegram cheklovlariga sig'ishini tekshiradi."""
    errors = []
    for code, info in BOT_INFO.items():
        if not isinstance(info, dict):
            continue
        for field, limit in (("name", MAX_NAME), ("short", MAX_SHORT),
                             ("description", MAX_DESC)):
            n = _u16len(info[field])
            if n > limit:
                errors.append(f"{code}.{field}: {n} > {limit}")
    return errors


async def main():
    errors = check_limits()
    if errors:
        print("❌ Cheklovdan oshgan matnlar:", *errors, sep="\n  ")
        return

    default_lang = BOT_INFO[None]
    bot = Bot(BOT_TOKEN)
    try:
        for code, info in BOT_INFO.items():
            lang = code
            if code is None:  # standart: til kodi yuborilmaydi
                info, lang = BOT_INFO[default_lang], None
            label = lang or f"standart ({default_lang})"

            try:
                await bot.set_my_name(info["name"], language_code=lang)
                print(f"✅ {label}: nom")
            except TelegramRetryAfter as e:
                # Nomni tez-tez o'zgartirib bo'lmaydi — o'tkazib yuboramiz
                print(f"⚠️ {label}: nom o'rnatilmadi (429, {e.retry_after}s "
                      f"kutish kerak) — qolganlari davom etadi")

            await bot.set_my_short_description(info["short"], language_code=lang)
            await bot.set_my_description(info["description"], language_code=lang)
            await bot.set_my_commands(
                [BotCommand(command=c, description=d) for c, d in info["commands"]],
                language_code=lang,
            )
            print(f"✅ {label}: qisqa tavsif, tavsif, buyruqlar")
    finally:
        await bot.session.close()

    print("\n🎉 Tayyor! Rasmlarni @BotFather orqali yuklang: branding/BOTFATHER.md")


if __name__ == "__main__":
    asyncio.run(main())
