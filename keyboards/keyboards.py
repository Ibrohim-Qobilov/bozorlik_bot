"""Barcha klaviaturalar shu yerda yig'ilgan."""
from urllib.parse import quote

from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)

from locales import t, LANGUAGES
from utils.text import fmt_amount, truncate
from utils.timezone import TIMEZONES, utc_str_to_local


def main_menu(lang):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "menu_new"))],
            [KeyboardButton(text=t(lang, "menu_lists"))],
            [KeyboardButton(text=t(lang, "menu_settings"))],
        ],
        resize_keyboard=True,
        is_persistent=True,  # pastki menyu doim ko'rinib turadi
    )


def settings_kb(lang):
    """Sozlamalar menyusi: til, vaqt mintaqasi, hisobot, eslatmalar, zaxira, murojaat."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(lang, "set_lang_btn"), callback_data="set:lang"),
            InlineKeyboardButton(text=t(lang, "set_tz_btn"), callback_data="set:tz"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "set_stats_btn"), callback_data="set:stats"),
            InlineKeyboardButton(text=t(lang, "set_reminders_btn"), callback_data="set:reminders"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "set_export_btn"), callback_data="set:export"),
            InlineKeyboardButton(text=t(lang, "set_import_btn"), callback_data="set:import"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "feedback_btn"), url="https://t.me/Ibrohim_qobilov_aloqabot"),
        ],
    ])


def tz_kb(current):
    """Vaqt mintaqasini tanlash; joriy tanlov ✅ bilan belgilanadi."""
    rows = []
    for minutes, label in TIMEZONES:
        mark = "✅ " if minutes == current else ""
        rows.append([InlineKeyboardButton(text=mark + label, callback_data=f"tz:{minutes}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def export_pick_kb(lists):
    """Zaxira uchun ro'yxat tanlash: jadvaldagi tartib raqamlari — tugmalar."""
    rows, row = [], []
    for n, lst in enumerate(lists, 1):
        row.append(InlineKeyboardButton(text=str(n), callback_data=f"exp:{lst['id']}"))
        if len(row) == 5:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def export_format_kb(lang, list_id):
    """Zaxira formati: Excel yoki PDF."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "export_fmt_xlsx"), callback_data=f"expf:{list_id}:x"),
        InlineKeyboardButton(text=t(lang, "export_fmt_pdf"), callback_data=f"expf:{list_id}:p"),
    ]])


def cancel_kb(lang):
    """Faqat «❌ Bekor qilish» (byudjet/eslatma promptlari uchun)."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "cancel_btn"), callback_data="xcancel"),
    ]])


def remind_kb(lang, list_id):
    """Eslatma vaqti: tez tanlovlar + bekor qilish."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(lang, "remind_today"), callback_data=f"rmq:{list_id}:td"),
            InlineKeyboardButton(text=t(lang, "remind_tomorrow"), callback_data=f"rmq:{list_id}:tm"),
        ],
        [InlineKeyboardButton(text=t(lang, "cancel_btn"), callback_data="xcancel")],
    ])


def members_kb(lang, list_id, members):
    """A'zolarni chiqarish tugmalari. `members` — [(user_id, ism), ...]."""
    rows = [
        [InlineKeyboardButton(text=f"❌ {truncate(name, 40)}", callback_data=f"mdel:{list_id}:{uid}")]
        for uid, name in members
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def lang_kb():
    rows, row = [], []
    for code, title in LANGUAGES:
        row.append(InlineKeyboardButton(text=title, callback_data=f"lang:{code}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _item_label(item, buyer=None):
    """Checkbox tugmasi matni: ⬜/✅ + nom + (×miqdor) + narx + (kim olgani)."""
    mark = "✅" if item["bought"] else "⬜️"
    label = f"{mark} {item['name']}"
    if item.get("qty", 1) > 1:
        label += f" ×{item['qty']}"
    if item["price"]:
        label += f" · {fmt_amount(item['price'])}"
    if buyer:
        label += f" · {buyer}"
    return truncate(label, 60)


def list_view_kb(lang, list_row, items, is_owner, buyers=None, group=False):
    """Ro'yxat sahifasi: har bir mahsulot — checkbox tugma, pastda boshqaruv.

    `buyers` — {user_id: ism}; ko'p a'zoli ro'yxatda kim olganini ko'rsatadi.
    `group=True` — guruh chatidagi ixcham ko'rinish: faqat checkbox + yangilash.
    """
    buyers = buyers or {}
    rows = [
        [InlineKeyboardButton(
            text=_item_label(i, buyers.get(i["bought_by"]) if i["bought"] else None),
            callback_data=f"chk:{i['id']}",
        )]
        for i in items
    ]
    if group:
        rows.append([InlineKeyboardButton(text=t(lang, "btn_refresh"), callback_data=f"lview:{list_row['id']}")])
        return InlineKeyboardMarkup(inline_keyboard=rows)
    rows.append([
        InlineKeyboardButton(text=t(lang, "btn_add"), callback_data=f"iadd:{list_row['id']}"),
        InlineKeyboardButton(text=t(lang, "btn_refresh"), callback_data=f"lview:{list_row['id']}"),
    ])
    rows.append([
        InlineKeyboardButton(text=t(lang, "btn_share"), callback_data=f"share:{list_row['id']}"),
        InlineKeyboardButton(text=t(lang, "btn_remind"), callback_data=f"rem:{list_row['id']}"),
    ])
    controls = []
    if is_owner:
        controls.append(InlineKeyboardButton(text=t(lang, "btn_budget"), callback_data=f"bud:{list_row['id']}"))
    if items:
        controls.append(InlineKeyboardButton(text=t(lang, "btn_edit"), callback_data=f"emode:{list_row['id']}"))
    if controls:
        rows.append(controls)
    bottom = []
    if items:
        bottom.append(InlineKeyboardButton(text=t(lang, "btn_repeat"), callback_data=f"rpt:{list_row['id']}"))
    if is_owner:
        bottom.append(InlineKeyboardButton(text=t(lang, "btn_delete_list"), callback_data=f"ldel:{list_row['id']}"))
    if bottom:
        rows.append(bottom)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def edit_pick_kb(lang, list_id, items):
    """Tahrirlash rejimi: mahsulot tanlanadi."""
    rows = [
        [InlineKeyboardButton(text=truncate(i["name"], 50), callback_data=f"ie:{i['id']}")]
        for i in items
    ]
    rows.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=f"lview:{list_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def edit_item_kb(lang, item):
    """Bitta mahsulot: nomi / narxi / o'chirish / orqaga."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(lang, "edit_name_btn"), callback_data=f"ien:{item['id']}"),
            InlineKeyboardButton(text=t(lang, "edit_price_btn"), callback_data=f"iep:{item['id']}"),
        ],
        [InlineKeyboardButton(text=t(lang, "btn_remove"), callback_data=f"idel:{item['id']}")],
        [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=f"emode:{item['list_id']}")],
    ])


def remind_repeat_kb(lang, reminder_id):
    """Eslatma saqlangach: har hafta takrorlashni yoqish tugmasi."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "remind_repeat_btn"), callback_data=f"rrep:{reminder_id}"),
    ]])


def reminders_kb(lang, reminders, tz_min=0):
    """Faol eslatmalar: bosilsa — o'chadi. Vaqtlar UTC'dan mahalliyga ko'rsatiladi."""
    rows = []
    for r in reminders:
        when = utc_str_to_local(r["at"], tz_min)  # "YYYY-MM-DD HH:MM" (UTC) -> "DD.MM HH:MM"
        label = f"🗑 {when} · {truncate(r['list_name'], 24)}"
        if r["repeat"]:
            label += " 🔂"
        rows.append([InlineKeyboardButton(text=truncate(label, 60), callback_data=f"rdel:{r['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def lists_kb(lists):
    """«Ro'yxatlarim» sahifasi: har bir ro'yxat — tugma."""
    rows = []
    for lst in lists:
        if lst["total"] and lst["done"] == lst["total"]:
            label = f"✅ {lst['name']}"
        else:
            label = f"🛒 {lst['name']} ({lst['done']}/{lst['total']})"
        rows.append([InlineKeyboardButton(text=truncate(label, 60), callback_data=f"lview:{lst['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def additems_kb(lang, list_id, new=False, suggestions=None):
    """Mahsulot kiritish bosqichi: tez qo'shish tugmalari + Bo'ldi + Orqaga/Bekor.

    `suggestions` — tez-tez olinadigan mahsulot nomlari (None o'rinlari o'tkaziladi).
    """
    rows, row = [], []
    for i, name in enumerate(suggestions or []):
        if not name:
            continue
        row.append(InlineKeyboardButton(text=f"➕ {truncate(name, 24)}", callback_data=f"qa:{list_id}:{i}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text=t(lang, "additems_done_btn"), callback_data=f"adddone:{list_id}")])
    controls = []
    if new:
        controls.append(InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=f"addback:{list_id}"))
    controls.append(InlineKeyboardButton(text=t(lang, "cancel_btn"), callback_data=f"addcancel:{list_id}"))
    rows.append(controls)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def price_kb(lang, item_id, last=None):
    """Narx so'ralganda: oxirgi narx (bo'lsa) / narxsiz belgilash / bekor qilish."""
    rows = []
    if last:
        rows.append([InlineKeyboardButton(
            text=t(lang, "price_last_btn").format(sum=fmt_amount(last)),
            callback_data=f"plast:{item_id}:{last}",
        )])
    rows.append([InlineKeyboardButton(text=t(lang, "price_skip_btn"), callback_data=f"pskip:{item_id}")])
    rows.append([InlineKeyboardButton(text=t(lang, "cancel_btn"), callback_data=f"pcancel:{item_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def share_kb(lang, link, invite_text):
    """«Yuborish» — Telegramning ulashish oynasini ochadi."""
    share_url = f"https://t.me/share/url?url={quote(link)}&text={quote(invite_text)}"
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "share_btn"), url=share_url),
    ]])


def delete_confirm_kb(lang, list_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "no"), callback_data=f"delno:{list_id}"),
        InlineKeyboardButton(text=t(lang, "yes"), callback_data=f"delyes:{list_id}"),
    ]])
