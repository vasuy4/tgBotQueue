from telebot.handler_backends import State, StatesGroup


class UserState(StatesGroup):
    base = State()
    choice = State()
    inqueue = State()