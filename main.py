from states import UserState, AdminState
from config import BOT_TOKEN, DEFAULT_COMMANDS, usernames, ADMIN_PASSWORD, ADMIN_COMMANDS
from models import User, MyQueue, create_models, UserPlace, tree_queue, all_tree_queue, logging_decorator, get_userqueue

import datetime
from peewee import IntegrityError, fn
from telebot import StateMemoryStorage, TeleBot
from telebot.custom_filters import StateFilter
from telebot.types import BotCommand, Message, InlineKeyboardMarkup, InlineKeyboardButton
import time


user_states = dict()

state_storage = StateMemoryStorage()

bot = TeleBot(BOT_TOKEN, state_storage=state_storage)
enable_logging = True

@bot.message_handler(state="*", commands=["start"], func=lambda message: time.time() - message.date < 60)
@logging_decorator(enable_logging)
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



@bot.message_handler(state="*", commands=["help"], func=lambda message: time.time() - message.date < 60)
@logging_decorator(enable_logging)
def handle_help(message):
    """Команда для справки"""
    bot.reply_to(message, "Через меня вы сможете создавать очереди, следить за ними.\n"
                          "Управляйте мной этими командами:\n\n"
                          "/select - выбрать очередь\n"
                          "/show - показать все очереди\n")


@bot.message_handler(state="*", commands=["show"], func=lambda message: time.time() - message.date < 60)
@logging_decorator(enable_logging)
def handle_show_queues(message):
    """Показывает все очереди после команды от пользователя /show"""
    user_id = message.from_user.id
    user = User.get_or_none(User.user_id == user_id)
    if user is None:
        bot.reply_to(message, "Вы не зарегистрированы. Напишите /start")
        return

    res = all_tree_queue()
    bot.send_message(message.from_user.id, "Список очередей:\n{}".format(res))


@bot.message_handler(state="*", commands=["select"], func=lambda message: time.time() - message.date < 60)
@logging_decorator(enable_logging)
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


@bot.message_handler(state="*", commands=["admin"], func=lambda message: time.time() - message.date < 60)
@logging_decorator(enable_logging)
def handle_password_request(message):
    """Запрос пароля для входа в режим админа"""
    bot.send_message(message.from_user.id, "Введите пароль")
    bot.set_state(message.from_user.id, AdminState.enterpassword)


@bot.message_handler(state=AdminState.enterpassword, func=lambda message: time.time() - message.date < 60)
@logging_decorator(enable_logging)
def handle_login_admin(message):
    """Вход в режим админа"""
    if message.text == ADMIN_PASSWORD:
        bot.send_message(message.from_user.id, "Создатель, добро пожаловать!\n/qcreate - Создать новую очередь\n"
                                               "/qdelete - Удалить старую очередь\n/uadd - добавить пользователя в "
                                               "очередь\n/udelete - Удалить пользователя из "
                                               "очереди\n/notification - Оповощение всем пользователям"
                                               "\n/user - Вернуться в режим пользователя")
        bot.set_my_commands([BotCommand(*cmd) for cmd in ADMIN_COMMANDS])
        bot.set_state(message.from_user.id, AdminState.admin)
    else:
        bot.send_message(message.from_user.id, "Ошибка входа!")


@bot.message_handler(state=AdminState.admin, commands=["user"], func=lambda message: time.time() - message.date < 60)
@logging_decorator(enable_logging)
def back_user(message):
    bot.send_message(message.from_user.id, "Возвращение в режим пользователя")
    bot.set_state(message.from_user.id, UserState.base)



@bot.message_handler(state=AdminState.admin, commands=["qcreate"], func=lambda message: time.time() - message.date < 60)
@logging_decorator(enable_logging)
def handle_create_queue_name_request(message):
    """Запрос нового названия"""
    bot.send_message(message.from_user.id, "Введите название новой очереди")
    bot.set_state(message.from_user.id, AdminState.createq)


@bot.message_handler(state=AdminState.createq, func=lambda message: time.time() - message.date < 60)
@logging_decorator(enable_logging)
def handle_create_queue(message):
    """Создание новой очереди"""
    max_num_queue = MyQueue.select(MyQueue.num_queue).order_by(MyQueue.num_queue.desc()).get().num_queue
    MyQueue.create(title=message.text, num_queue=max_num_queue+1)
    resp_str = "Новая очередь {} успешно создана!\n{}".format(message.text, all_tree_queue())
    bot.send_message(message.from_user.id, resp_str)
    bot.set_state(message.from_user.id, AdminState.admin)


@bot.message_handler(state=AdminState.admin, commands=["qdelete"], func=lambda message: time.time() - message.date < 60)
@logging_decorator(enable_logging)
def handle_delete_queue_name_request(message):
    """Запрос ID очереди"""
    resp_str = "Введите ID очереди для удаления:\n{}".format(all_tree_queue())
    bot.send_message(message.from_user.id, resp_str)
    bot.set_state(message.from_user.id, AdminState.deleteq)


@bot.message_handler(state=AdminState.deleteq, func=lambda message: time.time() - message.date < 60)
@logging_decorator(enable_logging)
def handle_delete_queue(message):
    """Удаление очереди"""
    queue_nums = [my_queue.num_queue for my_queue in MyQueue.select()]
    try:
        delete_num = int(message.text)
    except ValueError:
        bot.send_message(message.from_user.id, "Ошибка ввода, переход в меню admin.")
        bot.set_state(message.from_user.id, AdminState.admin)
        return

    if delete_num in queue_nums:
        queue_delete = MyQueue.select().where(MyQueue.num_queue == delete_num).get()
        num_queue = queue_delete.num_queue
        name_queue = queue_delete.title
        queue_delete.delete_instance()
        bot.send_message(message.from_user.id, "Очередь {} успешно удалена!".format(name_queue))

        queue_places = MyQueue.select().where(MyQueue.num_queue >= num_queue)
        for i_place in queue_places:
            i_place.num_queue -= 1
            i_place.save()

        bot.set_state(message.from_user.id, AdminState.admin)
    else:
        bot.send_message(message.from_user.id, "Очереди с таким ID не существует.")
        bot.set_state(message.from_user.id, AdminState.admin)


@bot.message_handler(state=AdminState.admin, commands=["uadd"], func=lambda message: time.time() - message.date < 60)
@logging_decorator(enable_logging)
def handle_add_user_in_queue_request(message):
    """Запрос ID очереди и ID пользователя"""
    bot.send_message(message.from_user.id, "Введите ID очереди, с которой работаем, затем через пробел ник пользователя"
                                           " без '@', которого надо добавить")
    bot.set_state(message.from_user.id, AdminState.addu)


@bot.message_handler(state=AdminState.addu, func=lambda message: time.time() - message.date < 60)
@logging_decorator(enable_logging)
def handle_add_user_in_queue(message):
    """Добавление пользователя в определённую очередь"""
    my_queue, my_user, id_queue, username = get_userqueue(bot, message)

    max_place = UserPlace.select(fn.Max(UserPlace.placeInQueue)).where(UserPlace.myQueue == id_queue).scalar()
    if not max_place:
        max_place = 0

    UserPlace.create(
        myQueue=id_queue,
        user=my_user.user_id,
        placeInQueue=max_place + 1,
        place_time=datetime.datetime.now().replace(microsecond=0)
    )
    res = tree_queue(my_queue)

    bot.send_message(message.from_user.id, "Пользователь @{} был успешно добавлен в очередь {}\n{}".format(
        username, my_queue.title, res
    ))
    bot.set_state(message.from_user.id, AdminState.admin)



@bot.message_handler(state=AdminState.admin, commands=["udelete"], func=lambda message: time.time() - message.date < 60)
@logging_decorator(enable_logging)
def handle_delete_user_in_queue_request(message):
    """Запрос ID очереди и ID пользователя"""
    bot.send_message(message.from_user.id, "Введите ID очереди, с которой работаем, затем через пробел ник пользователя"
                                           " без '@', которого надо удалить")
    bot.set_state(message.from_user.id, AdminState.deleteu)


@bot.message_handler(state=AdminState.deleteu, func=lambda message: time.time() - message.date < 60)
@logging_decorator(enable_logging)
def handle_delete_user_in_queue(message):
    """Удаление пользователя из очереди"""
    my_queue, my_user, id_queue, username = get_userqueue(bot, message)
    try:
        user_place = UserPlace.get((UserPlace.user == my_user.user_id) & (UserPlace.myQueue == id_queue))  # replace nd
        user_place.delete_instance()
    except:
        bot.send_message(message.from_user.id, "Пользователя нет в этой очереди!")
        return
    bnum_queue = True
    try:
        num_queue_user = UserPlace.get(UserPlace.user == my_user.user_id)
    except:
        bnum_queue = False
    if bnum_queue:
        user_places = UserPlace.select().where(
            (UserPlace.myQueue == id_queue) & (UserPlace.placeInQueue >= num_queue_user.placeInQueue))
        for i_place in user_places:
            i_place.placeInQueue -= 1
            i_place.save()


    res = tree_queue(my_queue)
    bot.send_message(message.from_user.id, "Пользователь {} был успешно удалён из очереди {}\n{}".format(username, my_queue, res))
    bot.set_state(message.from_user.id, AdminState.admin)


@bot.message_handler(state=AdminState.admin, commands=["notification"], func=lambda message: time.time() - message.date < 60)
@logging_decorator(enable_logging)
def handle_notification_for_all_users(message):
    all_users = User.select()
    for i_user in all_users:
        bot.send_message(i_user.user_id, "Запись открыта!")



def gen_markup(myQueue):
    """Кнопки под сообщением"""
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton("Да", callback_data="cb_yes_{}".format(myQueue)),
               InlineKeyboardButton("Выйти из очереди", callback_data="cb_no_{}".format(myQueue)),
               InlineKeyboardButton("Отмена", callback_data="cb_cancellation_{}".format(myQueue)),)
    return markup


@bot.callback_query_handler(func=lambda call: call.data.startswith('cb_'))
@logging_decorator(enable_logging)
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
                bot.send_message(call.from_user.id, "В очередь по вебу можно встать только в среду с 8:50 до 12:20")
                bot.set_state(call.from_user.id, UserState.base)
                return
            elif not (datetime.time(8, 50) <= datetime.datetime.now().time() <= datetime.time(12, 20)):
                bot.send_message(call.from_user.id, "Забронировать место можно только с 8:50 до 12:20")
                bot.set_state(call.from_user.id, UserState.base)
                return

            try:
                last_user_place = UserPlace.select().where((UserPlace.myQueue == 1) & (UserPlace.user == user.user_id)).\
                    order_by(UserPlace.pair_id.desc()).get()  # replace nd
                last_time_user = last_user_place.place_time
                if now - last_time_user < datetime.timedelta(days=1):
                    bot.send_message(call.from_user.id, "Похоже, что сегодня вы уже бронировали очередь, попробуйте через неделю)"
                                                        " Последний раз вы занимали очередь {} назад".format(now - last_time_user))
                    bot.set_state(call.from_user.id, UserState.base)
                    return
            except BaseException as exc:
                print("EXC:", exc)
        elif str(myQueue) == "1networksQueue":
            now = datetime.datetime.now()
            day_of_week = now.weekday()
            if day_of_week != 2 and day_of_week != 3:
                bot.send_message(call.from_user.id, "В очередь по сетям можно встать только в среду с 14:20 до 16:00 и "
                                                    "четверг с 10:30 до 13:50 ")
                bot.set_state(call.from_user.id, UserState.base)
                return
            elif not (((datetime.time(14, 20) <= now.time() <= datetime.time(16, 00)) and day_of_week == 2) or
                      ((datetime.time(10, 30) <= now.time() <= datetime.time(13, 50)) and day_of_week == 3)):
                if day_of_week == 2:
                    bot.send_message(call.from_user.id, "В очередь по сетям можно встать сегодня с 14:20 до 16:00")
                elif day_of_week == 3:
                    bot.send_message(call.from_user.id, "В очередь по сетям можно встать сегодня с 10:30 до 13:50")
                bot.set_state(call.from_user.id, UserState.base)
                return
            try:
                user_last_number = UserPlace.select().where((UserPlace.myQueue == 2) & (UserPlace.user == user.user_id)).order_by(UserPlace.pair_id.desc()).get()
                # replace nd
                user_last_number_place = user_last_number.placeInQueue
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
            place_time=datetime.datetime.now().replace(microsecond=0)
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


@bot.message_handler(state=UserState.choice, func=lambda message: time.time() - message.date < 60)
@logging_decorator(enable_logging)
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


@bot.message_handler(state=UserState.inqueue, func=lambda message: time.time() - message.date < 60)
@logging_decorator(enable_logging)
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
               InlineKeyboardButton("Пропустить очередь", callback_data="cbSkip_no_{}_{}".format(myQueue, num_next)),
               InlineKeyboardButton("Выйти из очереди", callback_data="cbSkip_exit_{}_{}".format(myQueue, num_next)),)
    return markup


@bot.callback_query_handler(func=lambda call: call.data.startswith('cbSkip'))
@logging_decorator(enable_logging)
def callback_query_skip(call):
    """
    Если выбран ответ 'да', то пользователь становится в статусе 'inqueue'
    Если 'нет' ....эм, нужно доработать
    """
    call_data = call.data.split('_')
    myQueue = MyQueue.select().where(MyQueue.title == call_data[2]).get()

    if call_data[1] == "yes":
        bot.answer_callback_query(call.id, "Answer is Yes")
        bot.send_message(call.from_user.id, "Как закончите отвечать, напишите, пожалуйста 'выйти' \nили воспользуйтесь"
                                            " кнопкой 'выйти' в предыдущем сообщении.")
        user_states[call.from_user.id] = myQueue
        bot.set_state(call.from_user.id, UserState.inqueue)
    elif call_data[1] == "no":
        bot.answer_callback_query(call.id, "Answer is Skip")
        # num_next = int(call_data[3])
        # num_next += 1
        # print("next - ", num_next)
        # notif_next(myQueue, num_next)
    else:
        bot.answer_callback_query(call.id, "Answer is Exit")
        exit_queue(bot, call, myQueue)
        bot.set_state(call.from_user.id, UserState.base)



def notif_next(myQueue, num_next):
    """
    Если предыдущий(1) пользователь вышел из очереди появляется это сообщение.
    P.s. Нужно доработать, чтобы при нажатии на кнопку 'пропустить очередь', шёл следующий пользователь и так
    до конца очереди.
    """
    try:
        user_place = UserPlace.get((UserPlace.placeInQueue == 1) & (UserPlace.myQueue == myQueue.queue_id))  # replace nd
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
        user_place = UserPlace.get((UserPlace.user == call.from_user.id) & (UserPlace.myQueue == myQueue.queue_id))
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


@bot.message_handler(state="*", func=lambda message: time.time() - message.date < 60)
@logging_decorator(enable_logging)
def help_response(message):
    """Ответ пользователю, если была введена неизвестная команда"""
    bot.send_message(message.from_user.id, "Я не знаю этой команды. Введите /help, если ничего не понимаете")


if __name__ == "__main__":
    print("Bot started")
    create_models()
    bot.add_custom_filter(StateFilter(bot))

    bot.set_my_commands([BotCommand(*cmd) for cmd in DEFAULT_COMMANDS])

    bot.polling()