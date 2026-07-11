"""Guruh rejimi: oilaviy guruhda /list — umumiy checkbox ro'yxat.

Ro'yxatni guruhga chiqargan odamning eng so'nggi tugallanmagan ro'yxati
ko'rsatiladi. Guruhdagi istalgan odam checkbox bosishi mumkin — birinchi
bosishda avtomatik a'zo bo'ladi. Guruhda narx so'ralmaydi (shaxsiy chatda
tahrirlash orqali kiritsa bo'ladi).
"""
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

import database as db
from locales import t
from .lists import build_view

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("list", "royxat"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_group_list(message: Message):
    lang = await db.get_lang(message.from_user.id)
    await db.set_user_name(message.from_user.id, message.from_user.first_name or "")
    lists = await db.get_user_lists(message.from_user.id)
    if not lists:
        await message.reply(t(lang, "no_lists"))
        return
    # Eng so'nggi tugallanmagan ro'yxat; hammasi tugagan bo'lsa — eng so'nggisi
    target = next(
        (l for l in lists if l["total"] == 0 or l["done"] < l["total"]), lists[0]
    )
    lst = await db.get_list(target["id"])
    text, kb = await build_view(lang, lst, message.from_user.id, group=True)
    await message.answer(text, reply_markup=kb)
