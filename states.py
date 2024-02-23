from telebot.handler_backends import State, StatesGroup


class UserState(StatesGroup):
    # user states
    base = State()
    choice = State()
    inqueue = State()
    changename = State()



class AdminState(StatesGroup):
    # admin states
    enterpassword = State()
    admin = State()

    # redact bot
    createq = State()
    deleteq = State()
    addu = State()
    deleteu = State()