"""Inline rejim: istalgan chatda `@bot` deb yozib, ro'yxatni yuborish.

Yuborilgan xabar — ro'yxatning matnli surati + «Qo'shilish» havolasi.
Ishlashi uchun BotFather'da Inline Mode yoqilgan bo'lishi kerak.
"""
import logging

from aiogram import Router
from aiogram.types import (
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent,
    InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultsButton,
)

import database as db
from locales import t
from utils.text import fmt_amount

router = Router()
logger = logging.getLogger(__name__)

MAX_RESULTS = 20      # Telegram cheklovi — 50, bizga 20 yetadi
MAX_SNAPSHOT = 40     # suratdagi mahsulotlar soni


def _snapshot(lang, name, items, done, total, spent):
    """Ro'yxatning matnli surati (boshqa chatga yuborish uchun)."""
    lines = [f"🛒 {name}", ""]
    for i in items[:MAX_SNAPSHOT]:
        mark = "✅" if i["bought"] else "⬜️"
        line = f"{mark} {i['name']}"
        if i.get("qty", 1) > 1:
            line += f" ×{i['qty']}"
        if i["price"]:
            line += f" · {fmt_amount(i['price'])}"
        lines.append(line)
    if len(items) > MAX_SNAPSHOT:
        lines.append("…")
    lines += [
        "",
        t(lang, "list_progress").format(done=done, total=total),
        t(lang, "list_spent").format(sum=fmt_amount(spent)),
    ]
    return "\n".join(lines)


@router.inline_query()
async def inline_lists(query: InlineQuery):
    lang = await db.get_lang(query.from_user.id)
    lists = await db.get_user_lists(query.from_user.id)
    me = await query.bot.me()

    results = []
    for l in lists[:MAX_RESULTS]:
        lst = await db.get_list(l["id"])
        if not lst:
            continue
        items = await db.get_items(l["id"])
        spent = sum(i["price"] for i in items if i["bought"] and i["price"])
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=t(lang, "inline_join_btn"),
                url=f"https://t.me/{me.username}?start=join_{lst['code']}",
            ),
        ]])
        results.append(InlineQueryResultArticle(
            id=str(lst["id"]),
            title=lst["name"],
            description=f"{l['done']}/{l['total']} · 💰 {fmt_amount(spent)}",
            input_message_content=InputTextMessageContent(
                message_text=_snapshot(lang, lst["name"], items, l["done"], l["total"], spent),
            ),
            reply_markup=kb,
        ))

    await query.answer(
        results,
        is_personal=True,   # har kimga o'z ro'yxatlari
        cache_time=1,       # ro'yxat tez o'zgaradi — keshlamaymiz
        button=InlineQueryResultsButton(
            text=t(lang, "inline_open_btn"), start_parameter="menu",
        ),
    )
