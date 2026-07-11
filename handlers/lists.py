"""Ro'yxatlar: yaratish, ko'rish, ulashish, o'chirish."""
import logging

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import database as db
from keyboards import (
    lists_kb, list_view_kb, additems_kb,
    share_kb, delete_confirm_kb, members_kb,
)
from locales import t
from states import NewList, AddItems
from utils.text import MENU_EMOJIS, fmt_amount, truncate

router = Router()
logger = logging.getLogger(__name__)


# ---------- ro'yxat sahifasini yasash ----------

async def build_view(lang, list_row, viewer_id, group=False):
    """Ro'yxat sahifasi: matn (sarlavha, hisob, byudjet) + checkbox klaviatura.

    `group=True` — guruh chatidagi ixcham variant (faqat checkbox + yangilash).
    """
    items = await db.get_items(list_row["id"])
    member_ids = await db.get_members(list_row["id"])
    done = sum(1 for i in items if i["bought"])
    spent = sum(i["price"] for i in items if i["bought"] and i["price"])

    lines = [f"🛒 {list_row['name']}", t(lang, "list_members").format(n=len(member_ids)), ""]
    if items:
        lines.append(t(lang, "list_progress").format(done=done, total=len(items)))
        if list_row["budget"]:
            lines.append(t(lang, "list_budget").format(
                sum=fmt_amount(spent), budget=fmt_amount(list_row["budget"])))
            if spent > list_row["budget"]:
                lines.append(t(lang, "budget_over").format(
                    over=fmt_amount(spent - list_row["budget"])))
        else:
            lines.append(t(lang, "list_spent").format(sum=fmt_amount(spent)))
        if done == len(items):
            lines += ["", t(lang, "list_done_note")]
    else:
        lines.append(t(lang, "list_empty"))

    # Ko'p a'zoli ro'yxatda kim olganini tugmada ko'rsatamiz
    buyers = await db.get_user_names(member_ids) if len(member_ids) > 1 else {}
    kb = list_view_kb(
        lang, list_row, items, list_row["owner_id"] == viewer_id, buyers, group=group,
    )
    return "\n".join(lines), kb


async def edit_to_view(message, lang, list_row, viewer_id):
    """Mavjud xabarni ro'yxat sahifasiga aylantiradi («o'zgarmagan» xatosi jim o'tadi)."""
    group = message.chat.type != "private"
    text, kb = await build_view(lang, list_row, viewer_id, group=group)
    try:
        await message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass  # matn o'zgarmagan bo'lsa ham xato emas


async def _load_list(call, need_member=True):
    """Callbackdagi ro'yxatni yuklaydi, a'zolikni tekshiradi. Topilmasa (lang, None)."""
    lang = await db.get_lang(call.from_user.id)
    list_id = int(call.data.split(":")[1])
    lst = await db.get_list(list_id)
    if not lst:
        await call.answer(t(lang, "list_gone"), show_alert=True)
        return lang, None
    if need_member and not await db.is_member(list_id, call.from_user.id):
        await call.answer(t(lang, "not_member"), show_alert=True)
        return lang, None
    return lang, lst


# ---------- yangi ro'yxat ----------

async def start_new(message, state, lang):
    await state.set_state(NewList.name)
    await message.answer(t(lang, "newlist_prompt"))


@router.message(Command("new"), F.chat.type == "private")
async def cmd_new(message: Message, state: FSMContext):
    await state.clear()
    lang = await db.get_lang(message.from_user.id)
    await start_new(message, state, lang)


@router.message(NewList.name, F.text)
async def newlist_name(message: Message, state: FSMContext):
    lang = await db.get_lang(message.from_user.id)
    name = truncate(message.text, 64)
    if name.startswith(MENU_EMOJIS):
        return
    data = await state.get_data()
    list_id = data.get("list_id")
    if list_id:
        # «◀️ Orqaga» dan qaytib kelingan — nomni almashtiramiz
        await db.update_list_name(list_id, name)
    else:
        list_id = await db.create_list(message.from_user.id, name)
    suggest = await db.frequent_items(message.from_user.id, list_id)
    await state.set_state(AddItems.items)
    await state.set_data({"list_id": list_id, "new": True, "suggest": suggest})
    await message.answer(
        t(lang, "additems_prompt"),
        reply_markup=additems_kb(lang, list_id, new=True, suggestions=suggest),
    )


# ---------- ro'yxatlarim ----------

async def show_lists(message, lang, user_id):
    lists = await db.get_user_lists(user_id)
    if not lists:
        await message.answer(t(lang, "no_lists"))
        return
    await message.answer(t(lang, "your_lists"), reply_markup=lists_kb(lists))


@router.message(Command("lists"), F.chat.type == "private")
async def cmd_lists(message: Message, state: FSMContext):
    await state.clear()
    lang = await db.get_lang(message.from_user.id)
    await show_lists(message, lang, message.from_user.id)


@router.callback_query(F.data.startswith("lview:"))
async def cb_view(call: CallbackQuery):
    lang, lst = await _load_list(call)
    if not lst:
        return
    await edit_to_view(call.message, lang, lst, call.from_user.id)
    await call.answer()


# O'chirish endi tahrirlash rejimi ichida (handlers/edit.py).


# ---------- ulashish ----------

@router.callback_query(F.data.startswith("share:"))
async def cb_share(call: CallbackQuery):
    lang, lst = await _load_list(call)
    if not lst:
        return
    me = await call.bot.me()
    link = f"https://t.me/{me.username}?start=join_{lst['code']}"
    invite = t(lang, "share_invite").format(name=lst["name"])
    await call.message.answer(
        t(lang, "share_msg").format(link=link),
        reply_markup=share_kb(lang, link, invite),
    )
    # Egasiga — a'zolarni boshqarish paneli
    if lst["owner_id"] == call.from_user.id:
        member_ids = await db.get_members(lst["id"])
        others = [uid for uid in member_ids if uid != lst["owner_id"]]
        if others:
            names = await db.get_user_names(member_ids)
            pairs = [(uid, names.get(uid, f"id{uid}")) for uid in others]
            await call.message.answer(
                t(lang, "members_title").format(n=len(member_ids)),
                reply_markup=members_kb(lang, lst["id"], pairs),
            )
    await call.answer()


# ---------- ro'yxatni takrorlash ----------

@router.callback_query(F.data.startswith("rpt:"))
async def cb_repeat(call: CallbackQuery):
    """Ro'yxat nusxasi: o'sha mahsulotlar (narxlari bilan), belgilari toza."""
    lang, lst = await _load_list(call)
    if not lst:
        return
    new_id = await db.duplicate_list(lst["id"], call.from_user.id)
    new_lst = await db.get_list(new_id)
    text, kb = await build_view(lang, new_lst, call.from_user.id)
    await call.message.answer(text, reply_markup=kb)
    await call.answer("🔁")


# ---------- ro'yxatni o'chirish ----------

@router.callback_query(F.data.startswith("ldel:"))
async def cb_delete_ask(call: CallbackQuery):
    lang, lst = await _load_list(call)
    if not lst:
        return
    if lst["owner_id"] != call.from_user.id:
        await call.answer(t(lang, "only_owner"), show_alert=True)
        return
    try:
        await call.message.edit_text(
            t(lang, "del_confirm").format(name=lst["name"]),
            reply_markup=delete_confirm_kb(lang, lst["id"]),
        )
    except TelegramBadRequest:
        pass
    await call.answer()


@router.callback_query(F.data.startswith("delyes:"))
async def cb_delete_yes(call: CallbackQuery):
    lang, lst = await _load_list(call)
    if not lst:
        return
    if lst["owner_id"] != call.from_user.id:
        await call.answer(t(lang, "only_owner"), show_alert=True)
        return
    await db.delete_list(lst["id"])
    try:
        await call.message.edit_text(t(lang, "deleted"))
    except TelegramBadRequest:
        pass
    await call.answer()


@router.callback_query(F.data.startswith("delno:"))
async def cb_delete_no(call: CallbackQuery):
    lang, lst = await _load_list(call)
    if not lst:
        return
    await edit_to_view(call.message, lang, lst, call.from_user.id)
    await call.answer(t(lang, "cancelled"))
