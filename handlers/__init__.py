"""Barcha routerlar. Dispatcherga shu tartibda ulanadi.

`interrupt` eng birinchi turadi: menyu tugmalari istalgan FSM holati ichida ham
ishlashi va oqimni bekor qilishi uchun. `fallback` eng oxirida: qolgan har
qanday xabarga pastki menyuni qaytaradi.
"""
from . import (
    interrupt, start, group, lists, items, edit, extras,
    settings, backup, inline, fallback,
)

routers = (
    interrupt.router,
    start.router,
    group.router,
    lists.router,
    items.router,
    edit.router,
    extras.router,
    settings.router,
    backup.router,
    inline.router,
    fallback.router,
)
