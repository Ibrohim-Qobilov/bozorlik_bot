"""Sozlamalar menyusi: til, vaqt mintaqasi, hisobot va zaxira nusxa bo'limlari."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

import database as db
from keyboards import lang_kb, settings_kb, tz_kb
from locales import t
from utils.text import fmt_amount
from utils.timezone import VALID_OFFSETS, local_now, utc_label

router = Router()


async def show_settings(message: Message, lang):
    await message.answer(t(lang, "settings_menu"), reply_markup=settings_kb(lang))


@router.callback_query(F.data == "set:lang")
async def open_lang(call: CallbackQuery):
    lang = await db.get_lang(call.from_user.id)
    await call.message.edit_text(t(lang, "choose_lang"), reply_markup=lang_kb())
    await call.answer()


@router.callback_query(F.data == "set:tz")
async def open_tz(call: CallbackQuery):
    """Vaqt mintaqasini tanlash — eslatmalar shu vaqt bo'yicha ishlaydi."""
    lang = await db.get_lang(call.from_user.id)
    current = await db.get_tz(call.from_user.id)
    await call.message.edit_text(t(lang, "tz_prompt"), reply_markup=tz_kb(current))
    await call.answer()


@router.callback_query(F.data.startswith("tz:"))
async def choose_tz(call: CallbackQuery):
    lang = await db.get_lang(call.from_user.id)
    minutes = int(call.data.split(":")[1])
    if minutes not in VALID_OFFSETS:  # eskirgan/soxta tugma
        await call.answer()
        return
    await db.set_tz(call.from_user.id, minutes)
    await call.message.edit_text(t(lang, "tz_saved").format(tz=utc_label(minutes)))
    await call.answer("🕔")


@router.callback_query(F.data == "set:stats")
async def open_stats(call: CallbackQuery):
    """Joriy oy bo'yicha hisobot (foydalanuvchi vaqt mintaqasida)."""
    lang = await db.get_lang(call.from_user.id)
    tz = await db.get_tz(call.from_user.id)
    now = local_now(tz)
    s = await db.month_stats(call.from_user.id, now.strftime("%Y-%m"), tz)
    if not s["items"] and not s["lists"]:
        await call.message.answer(t(lang, "stats_empty"))
        await call.answer()
        return
    text = t(lang, "stats_body").format(
        month=now.strftime("%m.%Y"),
        lists=s["lists"],
        items=s["items"],
        sum=fmt_amount(s["total"]),
        own=fmt_amount(s["own"]),
    )
    if s["top"]:
        top_lines = "\n".join(
            f"• {i['name']} — {fmt_amount(i['price'])}" for i in s["top"]
        )
        text += "\n\n" + t(lang, "stats_top_title") + "\n" + top_lines
    months = await db.monthly_totals(call.from_user.id, tz_min=tz)
    if len(months) > 1:
        text += "\n\n" + t(lang, "stats_months_title") + "\n" + _months_chart(months)
    await call.message.answer(text)
    await call.answer()


def _months_chart(months):
    """Oylar bo'yicha matnli grafik: «07.2026 ▓▓▓▓ 450 000»."""
    peak = max(total for _, total in months) or 1
    lines = []
    for ym, total in months:
        label = f"{ym[5:7]}.{ym[:4]}"
        bar = "▓" * max(1, round(total / peak * 8))
        lines.append(f"{label}  {bar} {fmt_amount(total)}")
    return "\n".join(lines)
