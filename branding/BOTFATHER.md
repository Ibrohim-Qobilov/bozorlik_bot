# Bot brendingi 🎨

Botning rasmi, tavsifi va buyruqlarini o'rnatish uchun tayyor materiallar.

## Fayllar

| Fayl | Nima uchun |
|---|---|
| `logo_1024.png` | Bot profil rasmi (@BotFather → `/setuserpic`) |
| `description_pic_640x360.png` | Tavsif rasmi — bo'sh chatda ko'rinadi (@BotFather → Bot Settings → Edit Description Picture) |
| `description_pic_1280x720.png` | Xuddi shu banner 2× sifatda — kanal/post uchun |
| `logo.svg`, `description_pic.svg` | Manba fayllar — rang/matnni o'zgartirib qayta render qilsa bo'ladi |
| `set_bot_info.py` | Nom, tavsif va buyruqlarni 7 tilda avtomatik o'rnatadi |

SVG'ni qayta render qilish (macOS, Chrome bilan):

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless=new --disable-gpu --hide-scrollbars \
  --window-size=1024,1124 --screenshot=logo_1024.png "file://$PWD/logo.svg"
# pastki oq hoshiyani kesish: PIL bilan (0,0,1024,1024) crop
```

## Tez yo'l — skript ⚡

Rasmdan tashqari hammasini (nom, qisqa tavsif, tavsif, buyruqlar — 7 tilda)
bitta buyruq o'rnatadi:

```bash
python3 branding/set_bot_info.py
```

Rasmlarni esa Bot API qo'llamaydi — faqat @BotFather orqali:

1. `/setuserpic` → botni tanlang → `logo_1024.png` yuboring
2. `/mybots` → bot → **Bot Settings** → **Edit Description Picture** → `description_pic_640x360.png`

> ⚠️ Bot **nomini** Telegram tez-tez o'zgartirishga ruxsat bermaydi — skript
> 429 xatoda nomni o'tkazib yuborib, qolganini o'rnatadi.

## Qo'lda o'rnatish (asosiy — o'zbekcha)

Skript ishlatmasangiz, @BotFather'da:

**`/setname`** (64 belgigacha):

```
Bozorlik — oilaviy xarid ro'yxati 🛒
```

**`/setabouttext`** — profil sahifasidagi «About» (120 belgigacha):

```
Oilaviy bozorlik ro'yxati: birga tuzing, ✅ belgilang, xarajatni hisoblang. 8 til, guruh va inline rejim.
```

**`/setdescription`** — bo'sh chatdagi «Bu bot nima qila oladi?» (512 belgigacha):

```
🛒 Bozorlik — oilaviy xarid ro'yxati boti.

• Ro'yxat tuzing — mahsulotni narxi bilan ham yozish mumkin: «Non 5000»
• 👥 Havola orqali yaqinlaringiz bilan ulashing — hamma bitta ro'yxatni ko'radi
• ✅ Olinganini belgilang — bot sarflangan summani hisoblab boradi
• 💰 Byudjet qo'ying — oshib ketsa ogohlantiradi
• ⏰ Eslatma (haftalik ham), 📊 oylik hisobot, 💾 zaxira nusxa
• Guruhda /list, istalgan chatda inline rejim
• 🌐 8 til

Boshlash uchun /start bosing 👇
```

**`/setcommands`**:

```
new - 🛒 Yangi ro'yxat
lists - 📋 Ro'yxatlarim
list - 👥 Guruhda ro'yxatni ochish
start - ▶️ Boshlash
```

Boshqa tillardagi (ru, en, kk, tg, tr, ky) matnlar `set_bot_info.py` ichida —
BotFather til bo'yicha o'rnatishni qo'llamaydi, ular faqat skript orqali kiradi.

## Inline rejim 🔍

`handlers/inline.py` ishlashi uchun inline yoqilgan bo'lsin:

1. `/setinline` → botni tanlang
2. Placeholder: `Ro'yxat nomini yozing…`

## Kirill alifbosi haqida

Telegram mijozlari o'zbekcha uchun faqat `uz` kodini yuboradi — `uz_cyr`ga
alohida til kodi yo'q, shuning uchun bot tavsifi lotinchada qoladi (bot ichidagi
til tanlash esa ishlayveradi). Kerak bo'lsa, kirillcha variant:

**Qisqa tavsif:**

```
Оилавий бозорлик рўйхати: бирга тузинг, ✅ белгиланг, харажатни ҳисобланг. 8 тил, гуруҳ ва inline режим.
```

**Tavsif:**

```
🛒 Bozorlik — оилавий харид рўйхати боти.

• Рўйхат тузинг — маҳсулотни нархи билан ҳам ёзиш мумкин: «Нон 5000»
• 👥 Ҳавола орқали яқинларингиз билан улашинг — ҳамма битта рўйхатни кўради
• ✅ Олинганини белгиланг — бот сарфланган суммани ҳисоблаб боради
• 💰 Бюджет қўйинг — ошиб кетса огоҳлантиради
• ⏰ Эслатма (ҳафталик ҳам), 📊 ойлик ҳисобот, 💾 захира нусха
• Гуруҳда /list, исталган чатда inline режим
• 🌐 8 тил

Бошлаш учун /start босинг 👇
```

## Dizayn ranglari

| Element | Rang |
|---|---|
| Fon gradienti | `#3ddc97` → `#0b8f60` |
| Savat, matn | `#ffffff` |
| Ro'yxat qatorlari | `#0b8f60` |
| «Bajarildi» belgisi | `#fcd34d` → `#f59e0b` |
