"""Qo'shimcha imkoniyatlar: byudjet, eslatma va a'zolarni boshqarish."""
import logging
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import database as db
from keyboards import cancel_kb, remind_kb, remind_repeat_kb, reminders_kb, members_kb
from locales import t
from states import Budget, Remind
from utils.text import MENU_EMOJIS, fmt_amount, parse_price, parse_when
from utils.timezone import local_now, to_utc, utc_str_to_local
from .lists import _load_list
from .items import _show_updated_view

router = Router()
logger = logging.getLogger(__name__)


async def _cleanup(message, prompt_message_id):
    """Prompt va foydalanuvchi javobini o'chirib, chatni toza tutadi."""
    if prompt_message_id:
        try:
            await message.bot.delete_message(message.chat.id, prompt_message_id)
        except TelegramBadRequest:
            pass
    try:
        await message.delete()
    except TelegramBadRequest:
        pass


# ---------- byudjet ----------

@router.callback_query(F.data.startswith("bud:"))
async def cb_budget(call: CallbackQuery, state: FSMContext):
    lang, lst = await _load_list(call)
    if not lst:
        return
    if lst["owner_id"] != call.from_user.id:
        await call.answer(t(lang, "only_owner"), show_alert=True)
        return
    await state.set_state(Budget.amount)
    prompt = await call.message.answer(t(lang, "budget_prompt"), reply_markup=cancel_kb(lang))
    await state.set_data({
        "list_id": lst["id"],
        "view_chat_id": call.message.chat.id,
        "view_message_id": call.message.message_id,
        "prompt_message_id": prompt.message_id,
    })
    await call.answer()


@router.message(Budget.amount, F.text)
async def budget_entered(message: Message, state: FSMContext):
    lang = await db.get_lang(message.from_user.id)
    text = message.text.strip()
    if text.startswith(MENU_EMOJIS):
        return
    if text == "0":
        amount = None
    else:
        amount = parse_price(text)
        if amount is None:
            await message.answer(t(lang, "price_bad"))
            return
    data = await state.get_data()
    await state.clear()
    list_id = data.get("list_id")
    lst = await db.get_list(list_id) if list_id else None
    if not lst:
        await message.answer(t(lang, "list_gone"))
        return
    await db.set_budget(list_id, amount)
    await _cleanup(message, data.get("prompt_message_id"))
    if amount is None:
        await message.answer(t(lang, "budget_removed"))
    else:
        await message.answer(t(lang, "budget_saved").format(sum=fmt_amount(amount)))
    await _show_updated_view(
        message.bot, lang, list_id, message.from_user.id,
        data.get("view_chat_id"), data.get("view_message_id"), message.answer,
    )


# ---------- eslatma ----------

def _fmt_when(when):
    return when.strftime("%d.%m %H:%M")


@router.callback_query(F.data.startswith("rem:"))
async def cb_remind(call: CallbackQuery, state: FSMContext):
    lang, lst = await _load_list(call)
    if not lst:
        return
    await state.set_state(Remind.when)
    prompt = await call.message.answer(
        t(lang, "remind_prompt"), reply_markup=remind_kb(lang, lst["id"])
    )
    await state.set_data({"list_id": lst["id"], "prompt_message_id": prompt.message_id})
    await call.answer()


@router.callback_query(F.data.startswith("rmq:"))
async def cb_remind_quick(call: CallbackQuery, state: FSMContext):
    """Tez tanlov: bugun 18:00 / ertaga 09:00."""
    lang = await db.get_lang(call.from_user.id)
    _, list_id, kind = call.data.split(":")
    list_id = int(list_id)
    lst = await db.get_list(list_id)
    if not lst or not await db.is_member(list_id, call.from_user.id):
        await call.answer(t(lang, "list_gone"), show_alert=True)
        return
    tz = await db.get_tz(call.from_user.id)
    now = local_now(tz)  # foydalanuvchi mahalliy vaqti
    if kind == "td":
        when = now.replace(hour=18, minute=0, second=0, microsecond=0)
        if when <= now:
            when += timedelta(days=1)
    else:
        when = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    data = await state.get_data()
    if await state.get_state() == Remind.when.state and data.get("list_id") == list_id:
        await state.clear()
    utc_when = to_utc(when, tz)  # bazaga UTC'da yoziladi
    rem_id = await db.add_reminder(list_id, call.from_user.id, utc_when.strftime("%Y-%m-%d %H:%M"))
    try:
        await call.message.edit_text(
            t(lang, "remind_saved").format(time=_fmt_when(when)),
            reply_markup=remind_repeat_kb(lang, rem_id),
        )
    except TelegramBadRequest:
        pass
    await call.answer("⏰")


@router.message(Remind.when, F.text)
async def remind_entered(message: Message, state: FSMContext):
    lang = await db.get_lang(message.from_user.id)
    if message.text.startswith(MENU_EMOJIS):
        return
    tz = await db.get_tz(message.from_user.id)
    when = parse_when(message.text, local_now(tz))  # mahalliy vaqtga nisbatan
    if when is None:
        await message.answer(t(lang, "remind_bad"))
        return
    data = await state.get_data()
    await state.clear()
    list_id = data.get("list_id")
    lst = await db.get_list(list_id) if list_id else None
    if not lst:
        await message.answer(t(lang, "list_gone"))
        return
    utc_when = to_utc(when, tz)  # bazaga UTC'da yoziladi
    rem_id = await db.add_reminder(list_id, message.from_user.id, utc_when.strftime("%Y-%m-%d %H:%M"))
    await _cleanup(message, data.get("prompt_message_id"))
    await message.answer(
        t(lang, "remind_saved").format(time=_fmt_when(when)),
        reply_markup=remind_repeat_kb(lang, rem_id),
    )


@router.callback_query(F.data.startswith("rrep:"))
async def cb_remind_repeat(call: CallbackQuery):
    """«Har hafta takrorlash» — eslatmani haftalik qiladi."""
    lang = await db.get_lang(call.from_user.id)
    rem_id = int(call.data.split(":")[1])
    rem = await db.get_reminder(rem_id)
    if not rem or rem["user_id"] != call.from_user.id:
        await call.answer(t(lang, "list_gone"), show_alert=True)
        return
    await db.set_reminder_repeat(rem_id, call.from_user.id, "weekly")
    tz = await db.get_tz(call.from_user.id)
    when = utc_str_to_local(rem["at"], tz)  # UTC -> mahalliy "DD.MM HH:MM"
    try:
        await call.message.edit_text(t(lang, "remind_weekly_on").format(time=when))
    except TelegramBadRequest:
        pass
    await call.answer("🔂")


# ---------- eslatmalarni boshqarish (sozlamalar) ----------

async def _reminders_view(lang, user_id):
    reminders = await db.user_reminders(user_id)
    if not reminders:
        return t(lang, "reminders_empty"), None
    tz = await db.get_tz(user_id)  # vaqtlar UTC'da saqlangan — mahalliyga ko'rsatamiz
    return t(lang, "reminders_title"), reminders_kb(lang, reminders, tz)


@router.callback_query(F.data == "set:reminders")
async def cb_reminders(call: CallbackQuery):
    lang = await db.get_lang(call.from_user.id)
    text, kb = await _reminders_view(lang, call.from_user.id)
    await call.message.answer(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("rdel:"))
async def cb_reminder_delete(call: CallbackQuery):
    lang = await db.get_lang(call.from_user.id)
    rem_id = int(call.data.split(":")[1])
    await db.delete_reminder(rem_id, call.from_user.id)
    text, kb = await _reminders_view(lang, call.from_user.id)
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
    await call.answer(t(lang, "reminder_deleted"))


# ---------- umumiy bekor qilish (byudjet/eslatma promptlari) ----------

@router.callback_query(F.data == "xcancel")
async def cb_xcancel(call: CallbackQuery, state: FSMContext):
    lang = await db.get_lang(call.from_user.id)
    await state.clear()
    try:
        await call.message.delete()
    except TelegramBadRequest:
        pass
    await call.answer(t(lang, "cancelled"))


# ---------- a'zolarni boshqarish ----------

@router.callback_query(F.data.startswith("mdel:"))
async def cb_member_remove(call: CallbackQuery):
    lang = await db.get_lang(call.from_user.id)
    _, list_id, uid = call.data.split(":")
    list_id, uid = int(list_id), int(uid)
    lst = await db.get_list(list_id)
    if not lst:
        await call.answer(t(lang, "list_gone"), show_alert=True)
        return
    if lst["owner_id"] != call.from_user.id:
        await call.answer(t(lang, "only_owner"), show_alert=True)
        return
    names = await db.get_user_names([uid])
    removed_name = names.get(uid, f"id{uid}")
    await db.remove_member(list_id, uid)

    member_ids = await db.get_members(list_id)
    others = [u for u in member_ids if u != lst["owner_id"]]
    title = t(lang, "members_title").format(n=len(member_ids))
    try:
        if others:
            names = await db.get_user_names(member_ids)
            pairs = [(u, names.get(u, f"id{u}")) for u in others]
            await call.message.edit_text(title, reply_markup=members_kb(lang, list_id, pairs))
        else:
            await call.message.edit_text(title)
    except TelegramBadRequest:
        pass
    await call.answer(t(lang, "member_removed").format(user=removed_name))