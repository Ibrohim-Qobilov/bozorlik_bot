"""Mahsulotlar: qo'shish, checkbox belgilash, narx kiritish, o'chirish."""
import logging

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import database as db
from config import MAX_ITEMS
from keyboards import additems_kb, price_kb, main_menu
from locales import t
from states import AddItems, ItemPrice, NewList
from utils.text import MENU_EMOJIS, parse_items, parse_price, fmt_amount
from .lists import build_view, edit_to_view, _load_list

router = Router()
logger = logging.getLogger(__name__)


# ---------- «tugadi» e'loni ----------

async def maybe_announce_done(bot, list_id):
    """Hamma narsa olingan bo'lsa, barcha a'zolarga jami summa bilan xabar beradi.

    `done_notified` bayrog'i takror e'lonning oldini oladi (mahsulot qaytadan
    ochilsa yoki yangisi qo'shilsa, bayroq qayta 0 bo'ladi).
    """
    lst = await db.get_list(list_id)
    if not lst or lst["done_notified"]:
        return
    items = await db.get_items(list_id)
    if not items or not all(i["bought"] for i in items):
        return
    await db.set_done_notified(list_id, True)
    spent = sum(i["price"] for i in items if i["price"])
    key = "done_all" if spent else "done_all_noprice"
    members = await db.get_members(list_id)
    # Ko'p a'zoli ro'yxatda kim nima olganini ham qo'shamiz
    split = await db.member_spending(list_id) if len(members) > 1 else []
    names = await db.get_user_names([uid for uid, _, _ in split])
    for uid in members:
        lang_u = await db.get_lang(uid)
        text = t(lang_u, key).format(name=lst["name"], sum=fmt_amount(spent))
        if split:
            block = [t(lang_u, "done_by_title")]
            for buyer, n, total in split:
                line = "done_by_line" if total else "done_by_line_nosum"
                block.append(t(lang_u, line).format(
                    user=names.get(buyer, f"id{buyer}"), n=n, sum=fmt_amount(total)))
            text += "\n\n" + "\n".join(block)
        try:
            await bot.send_message(uid, text)
        except Exception:  # noqa: BLE001 — a'zo botni bloklagan bo'lishi mumkin
            logger.info("A'zoga yozib bo'lmadi: %s", uid)


async def _reopen_if_needed(list_id):
    """Ro'yxat «tugagan» bo'lsa, uni yana ochiq holatga qaytaradi."""
    lst = await db.get_list(list_id)
    if lst and lst["done_notified"]:
        await db.set_done_notified(list_id, False)


async def _budget_warn(send_fn, lang, list_id, added_price):
    """Shu xarid byudjetdan oshirgan bo'lsa, ogohlantirish yuboradi."""
    if not added_price:
        return
    lst = await db.get_list(list_id)
    if not lst or not lst["budget"]:
        return
    items = await db.get_items(list_id)
    spent = sum(i["price"] for i in items if i["bought"] and i["price"])
    if spent > lst["budget"] >= spent - added_price:
        await send_fn(t(lang, "budget_over").format(over=fmt_amount(spent - lst["budget"])))


# ---------- mahsulot qo'shish ----------

@router.callback_query(F.data.startswith("iadd:"))
async def cb_add_items(call: CallbackQuery, state: FSMContext):
    """Ro'yxat sahifasidagi «➕ Qo'shish» — kiritish bosqichini ochadi."""
    lang, lst = await _load_list(call)
    if not lst:
        return
    suggest = await db.frequent_items(call.from_user.id, lst["id"])
    await state.set_state(AddItems.items)
    await state.set_data({"list_id": lst["id"], "new": False, "suggest": suggest})
    await call.message.answer(
        t(lang, "additems_prompt_add"),
        reply_markup=additems_kb(lang, lst["id"], suggestions=suggest),
    )
    await call.answer()


@router.callback_query(F.data.startswith("qa:"))
async def cb_quick_add(call: CallbackQuery, state: FSMContext):
    """Tez qo'shish tugmasi — tez-tez olinadigan mahsulotni bir bosishda qo'shadi."""
    lang = await db.get_lang(call.from_user.id)
    _, list_id, idx = call.data.split(":")
    list_id, idx = int(list_id), int(idx)
    data = await state.get_data()
    if await state.get_state() != AddItems.items.state or data.get("list_id") != list_id:
        await call.answer(t(lang, "list_gone"), show_alert=True)  # eskirgan tugma
        return
    suggest = data.get("suggest") or []
    name = suggest[idx] if 0 <= idx < len(suggest) else None
    if not name:
        await call.answer()
        return
    if await db.count_items(list_id) >= MAX_ITEMS:
        await call.answer(t(lang, "too_many_items").format(max=MAX_ITEMS), show_alert=True)
        return
    await db.add_item(list_id, name)
    await _reopen_if_needed(list_id)
    suggest[idx] = None  # indekslar siljimasligi uchun o'chirmay bo'shatamiz
    await state.update_data(suggest=suggest)
    try:
        await call.message.edit_reply_markup(
            reply_markup=additems_kb(lang, list_id, data.get("new", False), suggest)
        )
    except TelegramBadRequest:
        pass
    await call.answer(f"➕ {name}")


@router.message(AddItems.items, F.text)
async def add_items_msg(message: Message, state: FSMContext):
    lang = await db.get_lang(message.from_user.id)
    if message.text.startswith(MENU_EMOJIS):
        return
    data = await state.get_data()
    list_id = data.get("list_id")
    lst = await db.get_list(list_id) if list_id else None
    if not lst:
        await state.clear()
        await message.answer(t(lang, "list_gone"))
        return

    items = parse_items(message.text)
    if not items:
        await message.answer(t(lang, "additems_empty"))
        return

    space = MAX_ITEMS - await db.count_items(list_id)
    for name, price, qty in items[:space]:
        await db.add_item(list_id, name, price, qty)
    added = len(items[:space])

    if added:
        await _reopen_if_needed(list_id)
    if added < len(items):
        await message.answer(t(lang, "too_many_items").format(max=MAX_ITEMS))
    if added:
        suggest = await db.frequent_items(message.from_user.id, list_id)
        await state.update_data(suggest=suggest)
        await message.answer(
            t(lang, "additems_added").format(n=added),
            reply_markup=additems_kb(lang, list_id, data.get("new", False), suggest),
        )


@router.message(AddItems.items)
async def add_items_other(message: Message):
    lang = await db.get_lang(message.from_user.id)
    await message.answer(t(lang, "additems_empty"))


@router.callback_query(F.data.startswith("adddone:"))
async def cb_add_done(call: CallbackQuery, state: FSMContext):
    lang = await db.get_lang(call.from_user.id)
    list_id = int(call.data.split(":")[1])
    data = await state.get_data()
    is_new = bool(data.get("new")) and data.get("list_id") == list_id
    await state.clear()
    lst = await db.get_list(list_id)
    if not lst:
        await call.answer(t(lang, "list_gone"), show_alert=True)
        return
    if is_new:
        await call.message.answer(t(lang, "list_ready"), reply_markup=main_menu(lang))
    text, kb = await build_view(lang, lst, call.from_user.id)
    await call.message.answer(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("addback:"))
async def cb_add_back(call: CallbackQuery, state: FSMContext):
    """«◀️ Orqaga» — ro'yxat nomini qayta kiritish bosqichiga qaytadi."""
    lang = await db.get_lang(call.from_user.id)
    list_id = int(call.data.split(":")[1])
    await state.set_state(NewList.name)
    await state.set_data({"list_id": list_id})
    await call.message.answer(t(lang, "newlist_prompt"))
    await call.answer()


@router.callback_query(F.data.startswith("addcancel:"))
async def cb_add_cancel(call: CallbackQuery, state: FSMContext):
    """«❌ Bekor qilish» — yangi ro'yxat oqimida ro'yxat butunlay o'chadi."""
    lang = await db.get_lang(call.from_user.id)
    list_id = int(call.data.split(":")[1])
    data = await state.get_data()
    is_new = bool(data.get("new")) and data.get("list_id") == list_id
    await state.clear()
    if is_new:
        lst = await db.get_list(list_id)
        if lst and lst["owner_id"] == call.from_user.id:
            await db.delete_list(list_id)
    await call.message.answer(t(lang, "cancelled"), reply_markup=main_menu(lang))
    await call.answer()


# ---------- checkbox: olindi / olinmadi ----------

@router.callback_query(F.data.startswith("chk:"))
async def cb_check(call: CallbackQuery, state: FSMContext):
    lang = await db.get_lang(call.from_user.id)
    item_id = int(call.data.split(":")[1])
    item = await db.get_item(item_id)
    if not item:
        await call.answer(t(lang, "list_gone"), show_alert=True)
        return
    lst = await db.get_list(item["list_id"])
    if not lst:
        await call.answer(t(lang, "list_gone"), show_alert=True)
        return
    in_group = call.message.chat.type != "private"
    if not await db.is_member(lst["id"], call.from_user.id):
        if in_group:
            # Guruhdagi ro'yxatni bosgan odam avtomatik a'zo bo'ladi
            await db.add_member(lst["id"], call.from_user.id)
            await db.set_user_name(call.from_user.id, call.from_user.first_name or "")
        else:
            await call.answer(t(lang, "not_member"), show_alert=True)
            return

    # Belgilangan narsani qayta bosish — bekor qilish
    if item["bought"]:
        await db.set_unbought(item_id)
        await _reopen_if_needed(lst["id"])
        await edit_to_view(call.message, lang, lst, call.from_user.id)
        await call.answer()
        return

    # Narxi oldindan yozilgan (yoki guruhda) — darhol belgilaymiz
    if item["price"] or in_group:
        await db.set_bought(item_id, call.from_user.id)
        await edit_to_view(call.message, lang, lst, call.from_user.id)
        await call.answer("✅")
        if item["price"]:
            await _budget_warn(call.message.answer, lang, lst["id"], item["price"])
        await maybe_announce_done(call.bot, lst["id"])
        return

    # Narxi yo'q — so'raymiz (oxirgi narx tugmasi bilan)
    last = await db.last_price(call.from_user.id, item["name"])
    await state.set_state(ItemPrice.price)
    prompt = await call.message.answer(
        t(lang, "price_prompt").format(name=item["name"]),
        reply_markup=price_kb(lang, item_id, last),
    )
    await state.set_data({
        "item_id": item_id,
        "view_chat_id": call.message.chat.id,
        "view_message_id": call.message.message_id,
        "prompt_message_id": prompt.message_id,
    })
    await call.answer()


@router.callback_query(F.data.startswith("plast:"))
async def cb_price_last(call: CallbackQuery, state: FSMContext):
    """«Oxirgi narx» tugmasi — o'sha narx bilan belgilaydi."""
    lang = await db.get_lang(call.from_user.id)
    _, item_id, price = call.data.split(":")
    item_id, price = int(item_id), int(price)
    item = await db.get_item(item_id)

    data = await state.get_data()
    if await state.get_state() == ItemPrice.price.state and data.get("item_id") == item_id:
        await state.clear()
    else:
        data = {}

    if not item:
        await call.answer(t(lang, "list_gone"), show_alert=True)
        return
    lst = await db.get_list(item["list_id"])
    if not lst or not await db.is_member(lst["id"], call.from_user.id):
        await call.answer(t(lang, "not_member"), show_alert=True)
        return
    if item["bought"]:
        try:
            await call.message.delete()
        except TelegramBadRequest:
            pass
        await call.answer("✅")
        return

    await db.set_bought(item_id, call.from_user.id, price)
    try:
        await call.message.delete()
    except TelegramBadRequest:
        pass
    await _show_updated_view(
        call.bot, lang, lst["id"], call.from_user.id,
        data.get("view_chat_id"), data.get("view_message_id"), call.message.answer,
    )
    await call.answer("✅")
    await _budget_warn(call.message.answer, lang, lst["id"], price)
    await maybe_announce_done(call.bot, lst["id"])


async def _show_updated_view(bot, lang, list_id, viewer_id, chat_id, message_id, send_fn):
    """Saqlangan xabar (chat_id, message_id)ni yangilaydi; bo'lmasa yangisini yuboradi."""
    lst = await db.get_list(list_id)
    if not lst:
        return
    text, kb = await build_view(lang, lst, viewer_id)
    if chat_id and message_id:
        try:
            await bot.edit_message_text(
                text, chat_id=chat_id, message_id=message_id, reply_markup=kb
            )
            return
        except TelegramBadRequest:
            pass
    await send_fn(text, reply_markup=kb)


@router.message(ItemPrice.price, F.text)
async def price_entered(message: Message, state: FSMContext):
    lang = await db.get_lang(message.from_user.id)
    price = parse_price(message.text)
    if price is None:
        await message.answer(t(lang, "price_bad"))
        return
    data = await state.get_data()
    await state.clear()
    item = await db.get_item(data.get("item_id", 0))
    if not item:
        await message.answer(t(lang, "list_gone"))
        return
    await db.set_bought(item["id"], message.from_user.id, price)
    # narx so'ragan xabar (tugmalari bilan) endi kerak emas
    if data.get("prompt_message_id"):
        try:
            await message.bot.delete_message(message.chat.id, data["prompt_message_id"])
        except TelegramBadRequest:
            pass
    # foydalanuvchi yozgan narx xabarini ham tozalaymiz
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
    await _show_updated_view(
        message.bot, lang, item["list_id"], message.from_user.id,
        data.get("view_chat_id"), data.get("view_message_id"), message.answer,
    )
    await _budget_warn(message.answer, lang, item["list_id"], price)
    await maybe_announce_done(message.bot, item["list_id"])


@router.callback_query(F.data.startswith("pskip:"))
async def cb_price_skip(call: CallbackQuery, state: FSMContext):
    lang = await db.get_lang(call.from_user.id)
    item_id = int(call.data.split(":")[1])
    item = await db.get_item(item_id)

    # Holatni faqat shu mahsulot kutilayotgan bo'lsa tozalaymiz
    data = await state.get_data()
    if await state.get_state() == ItemPrice.price.state and data.get("item_id") == item_id:
        await state.clear()
    else:
        data = {}

    if not item:
        await call.answer(t(lang, "list_gone"), show_alert=True)
        return
    lst = await db.get_list(item["list_id"])
    if not lst or not await db.is_member(lst["id"], call.from_user.id):
        await call.answer(t(lang, "not_member"), show_alert=True)
        return

    if item["bought"]:  # eskirgan tugma — allaqachon belgilangan
        try:
            await call.message.delete()
        except TelegramBadRequest:
            pass
        await call.answer("✅")
        return

    await db.set_bought(item_id, call.from_user.id)
    try:
        await call.message.delete()  # narx so'ragan xabar endi kerak emas
    except TelegramBadRequest:
        pass
    await _show_updated_view(
        call.bot, lang, lst["id"], call.from_user.id,
        data.get("view_chat_id"), data.get("view_message_id"), call.message.answer,
    )
    await call.answer("✅")
    await maybe_announce_done(call.bot, lst["id"])


@router.callback_query(F.data.startswith("pcancel:"))
async def cb_price_cancel(call: CallbackQuery, state: FSMContext):
    """Narx so'rovini bekor qilish — mahsulot belgilanmagan holicha qoladi."""
    lang = await db.get_lang(call.from_user.id)
    item_id = int(call.data.split(":")[1])
    data = await state.get_data()
    if await state.get_state() == ItemPrice.price.state and data.get("item_id") == item_id:
        await state.clear()
    try:
        await call.message.delete()
    except TelegramBadRequest:
        pass
    await call.answer(t(lang, "cancelled"))


# Mahsulotni o'chirish endi tahrirlash rejimida (handlers/edit.py, `idel:`).
