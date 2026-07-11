"""Hech bir handler olmagan xabarlar uchun zaxira javob.

Eng oxirgi router: foydalanuvchi nima yozmasin, pastki menyu qaytib chiqadi
(shaxsiy chatlarda; guruhlarda jim turadi).
"""
from aiogram import Router, F
from aiogram.types import Message

import database as db
from keyboards import main_menu, lang_kb
from locales import t

router = Router()


@router.message(F.text, F.chat.type == "private")
async def any_text(message: Message):
    user_id = message.from_user.id
    if not await db.user_exists(user_id):
        await message.answer(t("uz", "choose_lang"), reply_markup=lang_kb())
        return
    lang = await db.get_lang(user_id)
    await message.answer(t(lang, "menu_hint"), reply_markup=main_menu(lang))
