"""/start, havola orqali qo'shilish va til tanlash."""
import logging

from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import database as db
from keyboards import main_menu, lang_kb
from locales import t
from .lists import build_view

router = Router()
logger = logging.getLogger(__name__)


async def join_list(bot, user, lang, code, answer_fn):
    """Havola kodi bo'yicha ro'yxatga qo'shadi va sahifasini yuboradi."""
    lst = await db.get_list_by_code(code)
    if not lst:
        await answer_fn(t(lang, "join_bad"))
        return
    if await db.is_member(lst["id"], user.id):
        await answer_fn(t(lang, "join_already"))
    else:
        await db.add_member(lst["id"], user.id)
        await answer_fn(t(lang, "join_ok").format(name=lst["name"]))
        if lst["owner_id"] != user.id:
            owner_lang = await db.get_lang(lst["owner_id"])
            try:
                await bot.send_message(
                    lst["owner_id"],
                    t(owner_lang, "join_notify").format(user=user.full_name, name=lst["name"]),
                )
            except Exception:  # noqa: BLE001 — egasi botni bloklagan bo'lishi mumkin
                logger.info("Egasiga xabar yetmadi: %s", lst["owner_id"])
    text, kb = await build_view(lang, lst, user.id)
    await answer_fn(text, reply_markup=kb)


@router.message(CommandStart(deep_link=True), F.chat.type == "private")
async def cmd_start_deeplink(message: Message, command: CommandObject, state: FSMContext):
    """t.me/bot?start=join_KOD — ulashilgan ro'yxatga qo'shilish."""
    await state.clear()
    args = command.args or ""
    if not args.startswith("join_"):
        await cmd_start(message, state)
        return
    code = args[len("join_"):]
    user = message.from_user
    known = await db.user_exists(user.id)  # set_user_name yozuv ochishidan OLDIN
    await db.set_user_name(user.id, user.first_name or "")
    if known:
        lang = await db.get_lang(user.id)
        await message.answer(t(lang, "start"), reply_markup=main_menu(lang))
        await join_list(message.bot, user, lang, code, message.answer)
    else:
        # Avval til tanlansin — kod holatda saqlab turiladi
        await state.update_data(join_code=code)
        await message.answer(t("uz", "choose_lang"), reply_markup=lang_kb())


@router.message(CommandStart(), F.chat.type == "private")
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    known = await db.user_exists(user_id)  # set_user_name yozuv ochishidan OLDIN
    await db.set_user_name(user_id, message.from_user.first_name or "")
    if known:
        lang = await db.get_lang(user_id)
        await message.answer(t(lang, "start"), reply_markup=main_menu(lang))
    else:
        await message.answer(t("uz", "choose_lang"), reply_markup=lang_kb())


@router.callback_query(F.data.startswith("lang:"))
async def choose_lang(call: CallbackQuery, state: FSMContext):
    lang = call.data.split(":")[1]
    await db.set_lang(call.from_user.id, lang)
    data = await state.get_data()
    join_code = data.get("join_code")
    await state.clear()
    await call.message.edit_text(t(lang, "lang_saved"))
    await call.message.answer(t(lang, "start"), reply_markup=main_menu(lang))
    if join_code:
        await join_list(call.bot, call.from_user, lang, join_code, call.message.answer)
    await call.answer()
