from aiogram import Bot
from aiogram.dispatcher import Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from misc.config import *
from misc.database import *

storage = MemoryStorage()
bot = Bot(token)
dp = Dispatcher(bot, storage=storage)
connect()