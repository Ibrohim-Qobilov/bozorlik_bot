"""FSM holatlari."""
from aiogram.fsm.state import State, StatesGroup


class NewList(StatesGroup):
    name = State()


class AddItems(StatesGroup):
    items = State()  # data: list_id


class ItemPrice(StatesGroup):
    price = State()  # data: item_id, view_chat_id, view_message_id, prompt_message_id


class Backup(StatesGroup):
    file = State()


class Budget(StatesGroup):
    amount = State()  # data: list_id, view_chat_id, view_message_id, prompt_message_id


class Remind(StatesGroup):
    when = State()  # data: list_id, prompt_message_id


class EditItem(StatesGroup):
    name = State()   # data: item_id, prompt_message_id
    price = State()  # data: item_id, prompt_message_id
