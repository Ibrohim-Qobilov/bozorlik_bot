"""Menyu tugmasi oqim o'rtasida bosilsa — oqimni bekor qilib, o'sha bo'limga o'tadi.

Bu router eng birinchi ulanadi, shuning uchun FSM holati ichida ham
(ro'yxat nomi, mahsulot, narx kutilayotganda) menyu tugmalari ishlab ketadi va
tugma matni "noto'g'ri kiritma" sifatida qabul qilinmaydi.
"""
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import database as db
from keyboards import lang_kb
from locales import t
from .lists import start_new, show_lists
from .settings import show_settings

router = Router()


@router.message(F.text.startswith("🛒"), F.chat.type == "private")
async def i_new(message: Message, state: FSMContext):
    await state.clear()
    lang = await db.get_lang(message.from_user.id)
    await start_new(message, state, lang)


@router.message(F.text.startswith("📋"), F.chat.type == "private")
async def i_lists(message: Message, state: FSMContext):
    await state.clear()
    lang = await db.get_lang(message.from_user.id)
    await show_lists(message, lang, message.from_user.id)


@router.message(F.text.startswith("⚙️"), F.chat.type == "private")
async def i_settings(message: Message, state: FSMContext):
    await state.clear()
    lang = await db.get_lang(message.from_user.id)
    await show_settings(message, lang)


@router.message(F.text.startswith("🌐"), F.chat.type == "private")
async def i_lang(message: Message, state: FSMContext):
    """Eski menyudagi «🌐 Til» tugmasi uchun ham ishlab qoladi."""
    await state.clear()
    lang = await db.get_lang(message.from_user.id)
    await message.answer(t(lang, "choose_lang"), reply_markup=lang_kb())
