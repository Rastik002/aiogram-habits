import asyncio
from aiogram.utils import executor
from create_bot import dp
from handlers import user
from handlers.user import send_notifications

user.register_handlers_user()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(send_notifications())
    executor.start_polling(dp, skip_updates=True)
