# Bozorlik Bot 🛒

Bozorlik (xarid) ro'yxatini oila bo'lib yuritish uchun Telegram bot.

## Imkoniyatlar

- 🛒 Bozorlik ro'yxatini tuzish — mahsulotni narxi bilan (`Non 5000`) yoki narxsiz qo'shish
- 👥 Ro'yxatni havola orqali yaqinlar bilan ulashish — hamma bitta ro'yxatni ko'radi va belgilaydi
- ✅ Olingan narsani checkbox tugma bilan belgilab ketish
- 💵 Belgilashda narx kiritish — bot sarflangan summani yig'ib boradi
- 🎉 Hammasi olinganda barcha a'zolarga «Bozorlik tugadi!» xabari va jami summa
- 👥 Tugagach kim nima olgani ko'rinadi — har bir a'zoning xaridi soni va summasi bilan
- ⏰ Eslatmalar — «bozorlik vaqti» xabari belgilangan vaqtda; har kim **o'z vaqt mintaqasida** (Sozlamalar → 🕔 Vaqt mintaqasi, standart tilga qarab)
- 🌐 8 til: O'zbek (lotin/kirill), Rus, Ingliz, Qozoq, Tojik, Turk, Qirg'iz

## O'rnatish

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# .env ichiga @BotFather bergan tokenni yozing

python main.py
```

## Foydalanish

1. **🛒 Yangi ro'yxat** — nom kiritasiz, keyin mahsulotlarni yuborasiz (har qatorda bittadan, xohlasangiz narxi bilan: `Non 5000`).
2. **👥 Ulashish** — havolani oila a'zolariga yuborasiz, ular ham ro'yxatga qo'shiladi.
3. Bozorda yurganda olingan narsani **⬜ tugmasini bosib** belgilaysiz — narxini so'raydi (kiritish ixtiyoriy).
4. Hammasi olinganda bot barcha a'zolarga **«🎉 Bozorlik tugadi!»** deb jami summani yuboradi.

## Tuzilishi

```
bozorlik_bot/
├── main.py          # ishga tushirish
├── config.py        # .env sozlamalari
├── states.py        # FSM holatlari
├── database/        # SQLite (aiosqlite)
├── handlers/        # start, ro'yxatlar, mahsulotlar, interrupt
├── keyboards/       # reply va inline klaviaturalar
├── locales/         # 8 til
├── utils/           # narx ajratish, formatlash
└── tests/           # unittest
```

## Testlar

```bash
python3 -m unittest discover tests
```
