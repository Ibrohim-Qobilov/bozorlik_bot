"""Mahsulotni tahrirlash: nomi, narxi va o'chirish.

Ro'yxatdagi «✏️ Tahrirlash» → mahsulot tanlanadi → nom/narx/o'chirish menyusi.
"""
import logging

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import database as db
from keyboards import edit_pick_kb, edit_item_kb, cancel_kb
from locales import t
from states import EditItem
from utils.text import MENU_EMOJIS, parse_price, truncate
from .lists import _load_list, build_view, edit_to_view
from .items import maybe_announce_done

router = Router()
logger = logging.getLogger(__name__)


async def _show_picker(message, lang, lst, viewer_id):
    """Mahsulot tanlash sahifasi (bo'sh bo'lsa — oddiy ko'rinishga qaytadi)."""
    items = await db.get_items(lst["id"])
    if not items:
        await edit_to_view(message, lang, lst, viewer_id)
        return
    try:
        await message.edit_text(
            t(lang, "edit_pick"), reply_markup=edit_pick_kb(lang, lst["id"], items)
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("emode:"))
async def cb_edit_mode(call: CallbackQuery):
    lang, lst = await _load_list(call)
    if not lst:
        return
    await _show_picker(call.message, lang, lst, call.from_user.id)
    await call.answer()


@router.callback_query(F.data.startswith("ie:"))
async def cb_edit_item(call: CallbackQuery):
    """Tanlangan mahsulot menyusi: nomi / narxi / o'chirish."""
    lang = await db.get_lang(call.from_user.id)
    item_id = int(call.data.split(":")[1])
    item = await db.get_item(item_id)
    if not item:
        await call.answer(t(lang, "list_gone"), show_alert=True)
        return
    lst = await db.get_list(item["list_id"])
    if not lst or not await db.is_member(lst["id"], call.from_user.id):
        await call.answer(t(lang, "not_member"), show_alert=True)
        return
    try:
        await call.message.edit_text(
            t(lang, "edit_item_menu").format(name=item["name"]),
            reply_markup=edit_item_kb(lang, item),
        )
    except TelegramBadRequest:
        pass
    await call.answer()


async def _start_edit(call, state, target_state, prompt_key):
    """Nom/narx so'rash bosqichini ochadi (umumiy qism)."""
    lang = await db.get_lang(call.from_user.id)
    item_id = int(call.data.split(":")[1])
    item = await db.get_item(item_id)
    if not item:
        await call.answer(t(lang, "list_gone"), show_alert=True)
        return
    lst = await db.get_list(item["list_id"])
    if not lst or not await db.is_member(lst["id"], call.from_user.id):
        await call.answer(t(lang, "not_member"), show_alert=True)
        return
    await state.set_state(target_state)
    prompt = await call.message.answer(
        t(lang, prompt_key).format(name=item["name"]), reply_markup=cancel_kb(lang)
    )
    await state.set_data({"item_id": item_id, "prompt_message_id": prompt.message_id})
    await call.answer()


@router.callback_query(F.data.startswith("ien:"))
async def cb_edit_name(call: CallbackQuery, state: FSMContext):
    await _start_edit(call, state, EditItem.name, "edit_name_prompt")


@router.callback_query(F.data.startswith("iep:"))
async def cb_edit_price(call: CallbackQuery, state: FSMContext):
    await _start_edit(call, state, EditItem.price, "edit_price_prompt")


async def _cleanup(message, prompt_message_id):
    if prompt_message_id:
        try:
            await message.bot.delete_message(message.chat.id, prompt_message_id)
        except TelegramBadRequest:
            pass
    try:
        await message.delete()
    except TelegramBadRequest:
        pass


async def _finish_edit(message, state, lang):
    """Tahrir yakuni: promptlarni tozalab, yangilangan ro'yxatni yuboradi."""
    data = await state.get_data()
    await state.clear()
    item = await db.get_item(data.get("item_id", 0))
    await _cleanup(message, data.get("prompt_message_id"))
    return data, item


@router.message(EditItem.name, F.text)
async def edit_name_entered(message: Message, state: FSMContext):
    lang = await db.get_lang(message.from_user.id)
    if message.text.startswith(MENU_EMOJIS):
        return
    name = truncate(message.text, 64)
    data, item = await _finish_edit(message, state, lang)
    if not item:
        await message.answer(t(lang, "list_gone"))
        return
    await db.update_item_name(item["id"], name)
    lst = await db.get_list(item["list_id"])
    await message.answer(t(lang, "edited"))
    text, kb = await build_view(lang, lst, message.from_user.id)
    await message.answer(text, reply_markup=kb)


@router.message(EditItem.price, F.text)
async def edit_price_entered(message: Message, state: FSMContext):
    lang = await db.get_lang(message.from_user.id)
    if message.text.startswith(MENU_EMOJIS):
        return
    raw = message.text.strip()
    if raw == "0":
        price = None
    else:
        price = parse_price(raw)
        if price is None:
            await message.answer(t(lang, "price_bad"))
            return
    data, item = await _finish_edit(message, state, lang)
    if not item:
        await message.answer(t(lang, "list_gone"))
        return
    await db.update_item_price(item["id"], price)
    lst = await db.get_list(item["list_id"])
    await message.answer(t(lang, "edited"))
    text, kb = await build_view(lang, lst, message.from_user.id)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("idel:"))
async def cb_item_delete(call: CallbackQuery):
    """Tahrirlash menyusidagi o'chirish — so'ng tanlash sahifasiga qaytadi."""
    lang = await db.get_lang(call.from_user.id)
    item_id = int(call.data.split(":")[1])
    item = await db.get_item(item_id)
    if not item:
        await call.answer(t(lang, "list_gone"), show_alert=True)
        return
    lst = await db.get_list(item["list_id"])
    if not lst or not await db.is_member(lst["id"], call.from_user.id):
        await call.answer(t(lang, "not_member"), show_alert=True)
        return
    await db.delete_item(item_id)
    await _show_picker(call.message, lang, lst, call.from_user.id)
    await call.answer("🗑")
    # qolganlari hammasi olingan bo'lib qolishi mumkin
    await maybe_announce_done(call.bot, lst["id"])
