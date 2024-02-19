from states import UserState
from config import BOT_TOKEN, DEFAULT_COMMANDS, usernames
from models import User, MyQueue, create_models, UserPlace, tree_queue, all_tree_queue

import datetime
from peewee import IntegrityError, fn
from telebot import StateMemoryStorage, TeleBot
from telebot.custom_filters import StateFilter
from telebot.types import BotCommand, Message, InlineKeyboardMarkup, InlineKeyboardButton
user_states = dict()

state_storage = StateMemoryStorage()

bot = TeleBot(BOT_TOKEN, state_storage=state_storage)


@bot.message_handler(state="*", commands=["start"])
def handle_start(message: Message) -> None:
    """Регистрация пользователя в БД, если его там ещё нет."""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    if not username in usernames:
        bot.reply_to(message, "Это бот создан специально для Московского Политеха группы 221-324, если вы не от туда,"
                              "то закройте бота, пожалуйста")
        return
    try:
        User.create(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        bot.reply_to(message, "Добро пожаловать в менеджер очередей Московского Политеха для группы 221-324!")
    except IntegrityError:
        bot.reply_to(message, f"Рад вас снова видеть, {first_name}!")\



@bot.message_handler(state="*", commands=["help"])
def handle_help(message):
    """Команда для справки"""
    bot.reply_to(message, "Через меня вы сможете создавать очереди, следить за ними.\n"
                          "Управляйте мной этими командами:\n\n"
                          "/select - выбрать очередь\n"
                          "/show - показать все очереди\n")


@bot.message_handler(state="*", commands=["show"])
def handle_show_queues(message):
    """Показывает все очереди после команды от пользователя /show"""
    user_id = message.from_user.id
    user = User.get_or_none(User.user_id == user_id)
    if user is None:
        bot.reply_to(message, "Вы не зарегистрированы. Напишите /start")
        return

    res = all_tree_queue()
    bot.send_message(message.from_user.id, "Список очередей:\n{}".format(res))


@bot.message_handler(state="*", commands=["select"])
def handle_select(message):
    """Выводит список очередей, переносит статус пользователя в статус выбора очереди."""
    user_id = message.from_user.id
    user = User.get_or_none(User.user_id == user_id)
    if user is None:
        bot.reply_to(message, "Вы не зарегистрированы. Напишите /start")
        return

    res = all_tree_queue()
    bot.send_message(message.from_user.id, "Выберете номер очереди:\n{}".format(res))
    bot.set_state(message.from_user.id, UserState.choice)


def gen_markup(myQueue):
    """Кнопки под сообщением"""
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton("Да", callback_data="cb_yes_{}".format(myQueue)),
               InlineKeyboardButton("Выйти из очереди", callback_data="cb_no_{}".format(myQueue)),
               InlineKeyboardButton("Отмена", callback_data="cb_cancellation_{}".format(myQueue)),)
    return markup


@bot.callback_query_handler(func=lambda call: call.data.startswith('cb_'))
def callback_query(call):
    """
    После нажатия на кнопку проверяется какая была нажата.
    Если "да", то добавление пользователя в конец очереди и переход в состояние "inQueue", если он имеет на это право.
    Если "Выйти из очереди", то удаляет данного пользователя, находящегося ближе к началу очереди, если пользователь
    в ней находится. При удалении смещает остальных пользователей на позицию. Переход в статус 'base'.
    Если "Отмена", то возвращение в базовое состояние.
    """
    call_data = call.data.split('_')

    if call_data[1] == "yes":
        bot.answer_callback_query(call.id, "Answer is Yes")

        myQueue = MyQueue.select().where(MyQueue.title == call_data[2]).get()
        user = User.select().where(User.user_id == call.from_user.id).get()

        max_place = UserPlace.select(fn.Max(UserPlace.placeInQueue)).where(UserPlace.myQueue == myQueue).scalar()
        if not max_place:
            max_place = 0

        if str(myQueue) == "1webQueue":
            now = datetime.datetime.now()
            day_of_week = now.weekday()

            if day_of_week != 2:
                bot.send_message(call.from_user.id, "В очередь во вебу можно встать только в среду с 8:50 до 12:20")
                bot.set_state(call.from_user.id, UserState.base)
                return
            elif not (datetime.time(8, 50) <= datetime.datetime.now().time() <= datetime.time(12, 20)):
                bot.send_message(call.from_user.id, "Забронировать место можно только с 8:50 до 12:20")
                bot.set_state(call.from_user.id, UserState.base)
                return

            try:
                last_user_place = UserPlace.select().where(UserPlace.myQueue == 1 and UserPlace.user == user.user_id).\
                    order_by(UserPlace.pair_id.desc()).get()
                last_time_user = last_user_place.place_time
                if now - last_time_user < datetime.timedelta(days=1):
                    bot.send_message(call.from_user.id, "Похоже, что сегодня вы уже бронировали очередь, попробуйте через неделю)"
                                                        " Последний раз вы занимали очередь {} назад".format(now - last_time_user))
                    bot.set_state(call.from_user.id, UserState.base)
                    return
            except BaseException as exc:
                print(exc)
        elif str(myQueue) == "1networksQueue":
            now = datetime.datetime.now()
            day_of_week = now.weekday()
            if day_of_week != 2 and day_of_week != 3:
                bot.send_message(call.from_user.id, "В очередь по сетям можно встать только в среду и четверг с "
                                                    "14:20 до 16:00 и 10:30 до 13:50 соответственно")
                bot.set_state(call.from_user.id, UserState.base)
                return
            try:
                user_last_number = UserPlace.select().where(UserPlace.myQueue == 2 and UserPlace.user == user.user_id).order_by(UserPlace.pair_id.desc()).get()
                user_last_number_place = user_last_number.placeInQueue
                print(user_last_number_place, max_place)
                if user_last_number_place - max_place < 5:
                    bot.send_message(call.from_user.id, "Куда вы торопитесь? Между вами не прошло даже 5 человек")
                    bot.set_state(call.from_user.id, UserState.base)
                    return
            except:
                pass

        new_user_place = UserPlace.create(
            myQueue=myQueue,
            user=user,
            placeInQueue=max_place+1,
            place_time=datetime.datetime.now()
        )

        res = tree_queue(myQueue)
        user_states[call.from_user.id] = myQueue
        bot.send_message(call.from_user.id, "Вы встали в очередь {}\n{}\nЧтобы выйти из очереди - напишите 'выйти'".format(myQueue, res))
        bot.set_state(call.from_user.id, UserState.inqueue)
    elif call_data[1] == "no":
        myQueue = MyQueue.select().where(MyQueue.title == call_data[2]).get()

        bot.answer_callback_query(call.id, "Answer is Exit")
        exit_queue(bot, call, myQueue)
        try:
            user_states.pop(call.from_user.id)
        except KeyError:
            pass
        bot.set_state(call.from_user.id, UserState.base)
    else:
        bot.answer_callback_query(call.id, "Answer is No")
        bot.set_state(call.from_user.id, UserState.base)


@bot.message_handler(state=UserState.choice)
def choice_queue(message):
    """Ожидает ввод существующего ID очереди. Подтверждение становления в очередь через кнопки."""
    try:
        queue_id = int(message.text)
    except:
        bot.send_message(message.from_user.id, "Номер очереди введён не корректно.")
        return

    myQueue = MyQueue.get_or_none(MyQueue.queue_id == queue_id)
    if myQueue is None:
        bot.send_message(message.from_user.id, "Очереди с таким ID не существует.")
        return

    res = tree_queue(myQueue)

    bot.send_message(message.from_user.id, "Желаете встать в очередь {}?\n{}".format(myQueue, res),
                     reply_markup=gen_markup(myQueue))


@bot.message_handler(state=UserState.inqueue)
def handle_inqueue(message):
    """Если было получено сообщение 'выйти', то удаляет пользователя из очереди. Смещает очередь."""
    myQueue = user_states.get(message.from_user.id, "DATA_ERROR")

    myQueue = MyQueue.select().where(MyQueue.queue_id == myQueue.queue_id).get()
    if message.text.upper() == 'выйти'.upper():
        exit_queue(bot, message, myQueue)

        user_states.pop(message.from_user.id)
        bot.set_state(message.from_user.id, UserState.base)
    else:
        bot.send_message(message.from_user.id, "Ёмаё, слово 'выйти' можешь нормально написать? Или же можешь вернуться"
                                               "в меню /start")



def gen_markup_skip(myQueue, num_next):
    """Кнопки под сообщением"""
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton("Иду-иду", callback_data="cbSkip_yes_{}_{}".format(myQueue, num_next)),
               InlineKeyboardButton("Пропустить очередь", callback_data="cbSkip_no_{}_{}".format(myQueue, num_next)),)
    return markup


@bot.callback_query_handler(func=lambda call: call.data.startswith('cbSkip'))
def callback_query_skip(call):
    """
    Если выбран ответ 'да', то пользователь становится в статусе 'inqueue'
    Если 'нет' ....эм, нужно доработать
    """
    call_data = call.data.split('_')
    myQueue = MyQueue.select().where(MyQueue.title == call_data[2]).get()

    if call_data[1] == "yes":
        bot.answer_callback_query(call.id, "Answer is Yes")
        bot.send_message(call.from_user.id, "Как закончите отвечать, напишите, пожалуйста 'выйти'")
        user_states[call.from_user.id] = myQueue
        bot.set_state(call.from_user.id, UserState.inqueue)
    elif call_data[1] == "no":
        bot.answer_callback_query(call.id, "Answer is Skip")
        # num_next = int(call_data[3])
        # num_next += 1
        # print("next - ", num_next)
        # notif_next(myQueue, num_next)


def notif_next(myQueue, num_next):
    """
    Если предыдущий(1) пользователь вышел из очереди появляется это сообщение.
    P.s. Нужно доработать, чтобы при нажатии на кнопку 'пропустить очередь', шёл следующий пользователь и так
    до конца очереди.
    """
    try:
        user_place = UserPlace.get(UserPlace.placeInQueue == 1 and UserPlace.myQueue == myQueue.queue_id)
    except:
        return
    bot.send_message(user_place.user, "Очередь {} дошла до вас!".format(myQueue.title),
                     reply_markup=gen_markup_skip(myQueue, num_next))


def exit_queue(bot, call, myQueue):
    """
    Функция выхода из очереди. Удаляет пользователя из очереди, запускает напоминание следующему по счёту
    пользователю, что его черёд (если предыдущий вышел первым).
    """
    notification_for_next = False
    try:
        user_place = UserPlace.get(UserPlace.user == call.from_user.id and UserPlace.myQueue == myQueue.queue_id)
        if user_place.placeInQueue == 1:
            notification_for_next = True
        user_place.delete_instance()
    except:
        bot.send_message(call.from_user.id, "Вас нет в этой очереди!")
        return

    if notification_for_next:
        notif_next(myQueue, 1)

    user = User.get(User.user_id == call.from_user.id)
    bnum_queue = True
    try:
        num_queue_user = UserPlace.get(UserPlace.user == user.user_id)
    except:
        bnum_queue = False
    if bnum_queue:
        user_places = UserPlace.select().where(
            (UserPlace.myQueue == myQueue.queue_id) & (UserPlace.placeInQueue >= num_queue_user.placeInQueue))
        for i_place in user_places:
            i_place.placeInQueue -= 1
            i_place.save()

    res = tree_queue(myQueue)
    bot.send_message(call.from_user.id, "Вы успешно вышли из очереди {}\n{}".format(myQueue, res))


@bot.message_handler(state="*")
def help_response(message):
    """Ответ пользователю, если была введена неизвестная команда"""
    bot.send_message(message.from_user.id, "Я не знаю этой команды. Введите /help, если ничего не понимаете")


if __name__ == "__main__":
    print("Bot started")
    create_models()
    bot.add_custom_filter(StateFilter(bot))
    bot.set_my_commands([BotCommand(*cmd) for cmd in DEFAULT_COMMANDS])

    bot.polling()