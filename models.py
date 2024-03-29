from peewee import (
    AutoField,
    CharField,
    IntegerField,
    Model,
    SqliteDatabase,
    DateTimeField
)
from datetime import datetime
import traceback
import requests

from config import DB_PATH, AI_API_KEY, TRANSLATOR_API_KEY, TRANSLATOR_API_URL

db = SqliteDatabase(DB_PATH)


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    """Класс пользователя"""
    user_id = IntegerField(primary_key=True)
    username = CharField()
    first_name = CharField()
    last_name = CharField(null=True)
    #true_name = CharField(null=True)


class MyQueue(BaseModel):
    """Класс очереди."""
    queue_id = AutoField(primary_key=True)
    title = CharField()
    num_queue = IntegerField()

    def __str__(self):
        return str(self.title)


class UserPlace(BaseModel):
    """Класс, который связывает пользователя и очередь."""
    pair_id = AutoField(primary_key=True)
    myQueue = IntegerField()
    user = IntegerField()
    placeInQueue = IntegerField()
    place_time = DateTimeField(null=True)


def tree_queue(myQueue):
    """Функция, которая возвращает строку очереди с её содержимым."""
    qu = MyQueue.select().where(MyQueue.queue_id == myQueue.queue_id).get()
    res = ''

    query = UserPlace.select().where(UserPlace.myQueue == qu.queue_id)
    for user_place in query:
        user = User.get_or_none(User.user_id == user_place.user)
        res += "  {}) {} @{} - {}\n".format(user_place.placeInQueue, user.first_name, user.username, user_place.place_time)
    return res


def all_tree_queue():
    """Функция, которая возвращает строку всех очередей с их содержимым."""
    queues = MyQueue.select()
    res = ''
    for qu in queues:
        res += "========================\n"
        res += "{} - {}\n".format(str(qu.num_queue), str(qu.title))
        query = UserPlace.select().where(UserPlace.myQueue == qu.queue_id)
        for user_place in query:
            user = User.get_or_none(User.user_id == user_place.user)
            res += "  {}) {} @{} - {}\n".format(user_place.placeInQueue, user.first_name, user.username, user_place.place_time)
    res += "========================"
    return res


def create_models():
    """Функция, которая создаёт модели"""
    db.create_tables(BaseModel.__subclasses__())
    queues = MyQueue.select()
    if not queues:
        MyQueue.create(title="webQueue", num_queue=1)
        MyQueue.create(title="networksQueue", num_queue=2)


def logging_decorator(enable_logging):
    """Декоратор, который логирует данные, отправленные пользователем."""
    def log_dec(func):
        def wrapped(message):
            if enable_logging:
                try:
                    data = message.text
                except:
                    data = message.data
                name_log_file = 'log/chat_{}.log'.format(datetime.now().date())
                with open(name_log_file, 'a') as f:
                    new_log = "{} - user: @{} send message: {}\n".format(str(datetime.now().time()), str(message.from_user.username), str(data))
                    try:
                        f.write(new_log)
                    except UnicodeError:
                        pass
                try:
                    res = func(message)
                except BaseException as exc:
                    name_log_error = "log/errors_{}.log".format(datetime.now().date())
                    print(traceback.print_exc())
                    with open(name_log_error, 'a') as f:
                        new_log = "{} - user: {}, send message: {}, error: {}\n".format(str(datetime.now().time()),
                                                                                        str(message.from_user.username),
                                                                                        str(data),
                                                                                        exc)
                        f.write(new_log)
                    return None
            return res
        return wrapped
    return log_dec


def get_userqueue(bot, message):
    try:
        id_queue, username = message.text.split()
        id_queue = int(id_queue)
        username = str(username)
    except ValueError:
        bot.send_message(message.from_user.id, "Данные введены некорректно, попробуйте ещё раз.")
        return
    try:
        my_queue = MyQueue.get(MyQueue.queue_id == id_queue)
        my_user = User.get(User.username == username)
    except:
        bot.send_message(message.from_user.id, "Пользователь/очередь с заданными параметрами не найдены.")
        return
    return my_queue, my_user, id_queue, username


def translator_api_request(endpoint: str, params={}) -> requests.Response:
    params['key'] = TRANSLATOR_API_KEY
    return requests.get(
        f'{TRANSLATOR_API_URL}/{endpoint}',
        params=params
    )

def lookup(lang, msg):
    response = translator_api_request('lookup', params={
        'lang':lang,
        'text':msg.text,
        'ui':'ru'
    })
    print(response)
    print(response.json())
    print(response.json().get('def', {}))
    return response.json().get('def', {})



def math_ai(message):
    url = "https://robomatic-ai.p.rapidapi.com/api"

    payload = {
        "in": message.text,
        "op": "in",
        "cbot": "1",
        "SessionID": "RapidAPI1",
        "cbid": "1",
        "key": "RHMN5hnQ4wTYZBGCF3dfxzypt68rVP",
        "ChatSource": "RapidAPI",
        "duration": "1"
    }
    headers = {
        "content-type": "application/x-www-form-urlencoded",
        "X-RapidAPI-Key": AI_API_KEY,
        "X-RapidAPI-Host": "robomatic-ai.p.rapidapi.com"
    }

    response = requests.post(url, data=payload, headers=headers)
    print(response.json()['out'])
    return response