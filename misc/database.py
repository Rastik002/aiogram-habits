from peewee import *
from playhouse.sqliteq import SqliteQueueDatabase

db = SqliteQueueDatabase('misc/by002.db')


class Users(Model):
    user_id = BigIntegerField(default=0)
    notices = BooleanField(default=False)
    time_notices = TextField(default='06:00')

    class Meta:
        db_table = "Users"
        database = db


class Habits(Model):
    user_id = BigIntegerField(default=0)
    name = TextField(default='')
    target = TextField(default='')
    days = TextField(default='')
    history = TextField(default='')

    class Meta:
        db_table = "Habits"
        database = db


def connect():
    db.connect()
    db.create_tables([Users, Habits])
