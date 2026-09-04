"""Botni ishga tushirish."""
import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, ErrorEvent

import database as db
import handlers
from config import BOT_TOKEN
from handlers.lists import build_view
from locales import t

logger = logging.getLogger(__name__)

REMINDER_INTERVAL = 30  # soniya — eslatmalarni tekshirish oralig'i


async def reminder_loop(bot):
    """Fon vazifasi: vaqti kelgan eslatmalarni egasiga yuboradi.

    Eslatmalar bazada UTC'da saqlanadi (kiritishda foydalanuvchi mahalliy vaqti
    UTC'ga aylantiriladi), shuning uchun bu yerda ham UTC bilan solishtiramiz —
    server vaqt mintaqasiga bog'liq emas. Haftalik (`repeat='weekly'`) eslatmalar
    yuborilgach 7 kunga suriladi (mintaqalar yozgi vaqtga o'tmaydi — vaqt saqlanadi).
    """
    while True:
        try:
            now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            for r in await db.due_reminders(now):
                if r["repeat"] == "weekly":
                    # avval suramiz — xato bo'lsa ham qayta-qayta yuborilmasin
                    old = datetime.strptime(r["at"], "%Y-%m-%d %H:%M")
                    new_at = old + timedelta(days=7)
                    while new_at.strftime("%Y-%m-%d %H:%M") <= now:
                        new_at += timedelta(days=7)
                    await db.bump_reminder(r["id"], new_at.strftime("%Y-%m-%d %H:%M"))
                else:
                    await db.mark_reminder_sent(r["id"])
                lst = await db.get_list(r["list_id"])
                if not lst or not await db.is_member(lst["id"], r["user_id"]):
                    continue
                lang = await db.get_lang(r["user_id"])
                try:
                    await bot.send_message(
                        r["user_id"], t(lang, "remind_fire").format(name=lst["name"])
                    )
                    text, kb = await build_view(lang, lst, r["user_id"])
                    await bot.send_message(r["user_id"], text, reply_markup=kb)
                except Exception:  # noqa: BLE001 — foydalanuvchi botni bloklagan bo'lishi mumkin
                    logger.info("Eslatma yetmadi: %s", r["user_id"])
        except Exception:  # noqa: BLE001 — sikl hech qachon to'xtamasin
            logger.exception("Eslatma siklida xatolik")
        await asyncio.sleep(REMINDER_INTERVAL)


async def on_error(event: ErrorEvent):
    """Har qanday handler'dagi ushlanmagan xatoni jurnalga yozadi va
    foydalanuvchiga xushmuomala xabar qaytaradi (bot yiqilmaydi)."""
    logger.exception("Update ishlovida xatolik: %s", event.exception)
    upd = event.update
    user = chat_msg = None
    if upd.message:
        user, chat_msg = upd.message.from_user, upd.message
    elif upd.callback_query:
        user, chat_msg = upd.callback_query.from_user, upd.callback_query.message
        try:
            await upd.callback_query.answer()
        except Exception:  # noqa: BLE001 — bildirishnoma muhim emas
            pass
    if user is not None and chat_msg is not None:
        try:
            lang = await db.get_lang(user.id)
            await chat_msg.answer(t(lang, "error"))
        except Exception:  # noqa: BLE001 — foydalanuvchiga yozib bo'lmasa, jim o'tamiz
            pass
    return True


import os
from aiohttp import web

async def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Tez Bozorlik Bot is live! 🛒"))
    app.router.add_get("/health", lambda r: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Health server listening on port %d", port)
    return runner


async def set_commands(bot):
    await bot.set_my_commands([
        BotCommand(command="new", description="Yangi ro'yxat / New list"),
        BotCommand(command="lists", description="Ro'yxatlarim / My lists"),
        BotCommand(command="list", description="Guruhda ro'yxat / List in group"),
        BotCommand(command="start", description="Boshlash / Start"),
    ])


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    await db.init_db()

    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.include_routers(*handlers.routers)
    dp.errors.register(on_error)

    await set_commands(bot)

    web_runner = None
    if os.environ.get("PORT"):
        web_runner = await start_health_server()

    reminder_task = asyncio.create_task(reminder_loop(bot))

    logger.info("Bot ishga tushdi ✅")
    try:
        await dp.start_polling(bot)
    finally:
        reminder_task.cancel()
        if web_runner:
            await web_runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
