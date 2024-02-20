from peewee import (
    AutoField,
    CharField,
    IntegerField,
    Model,
    SqliteDatabase,
    DateTimeField
)
from datetime import datetime

from config import DB_PATH

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


class MyQueue(BaseModel):
    """Класс очереди."""
    queue_id = AutoField(primary_key=True)
    title = CharField()

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
        res += str(qu.queue_id) + " - " + str(qu.title) + "\n"
        query = UserPlace.select().where(UserPlace.myQueue == qu.queue_id)
        for user_place in query:
            user = User.get_or_none(User.user_id == user_place.user)
            res += "  {}) {} @{} - {}\n".format(user_place.placeInQueue, user.first_name, user.username, user_place.place_time)
    return res


def create_models():
    """Функция, которая создаёт модели"""
    db.create_tables(BaseModel.__subclasses__())
    queues = MyQueue.select()
    if not queues:
        MyQueue.create(title="webQueue")
        MyQueue.create(title="networksQueue")


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
            res = func(message)
            return res
        return wrapped
    return log_dec
