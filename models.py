from peewee import (
    AutoField,
    CharField,
    ForeignKeyField,
    IntegerField,
    Model,
    SqliteDatabase,
    DateTimeField
)
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


from config import DB_PATH

db = SqliteDatabase(DB_PATH)


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    user_id = IntegerField(primary_key=True)
    username = CharField()
    first_name = CharField()
    last_name = CharField(null=True)


class MyQueue(BaseModel):
    queue_id = AutoField(primary_key=True)
    title = CharField()

    def __str__(self):
        return str(self.title)


class UserPlace(BaseModel):
    pair_id = AutoField(primary_key=True)
    myQueue = IntegerField()
    user = IntegerField()
    placeInQueue = IntegerField()
    place_time = DateTimeField(null=True)


def tree_queue(myQueue):
    qu = MyQueue.select().where(MyQueue.queue_id == myQueue.queue_id).get()
    res = ''

    query = UserPlace.select().where(UserPlace.myQueue == qu.queue_id)
    for user_place in query:
        user = User.get_or_none(User.user_id == user_place.user)
        res += "  {}) {} @{} - {}\n".format(user_place.placeInQueue, user.first_name, user.username, user_place.place_time)
    return res


def all_tree_queue():
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
    db.create_tables(BaseModel.__subclasses__())
    queues = MyQueue.select()
    if not queues:
        MyQueue.create(title="webQueue")
        MyQueue.create(title="networksQueue")
