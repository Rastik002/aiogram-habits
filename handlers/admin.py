from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State as _State
from create_bot import dp, bot
from misc.keyboards import *
from misc.config import *
from misc.database import *


class AdminState(StatesGroup):
    mailing = _State()


@dp.message_handler(commands=['adm', 'admin'])
async def admin(message: types.Message):
    if message.chat.id not in admins:
        pass
    else:
        await message.answer("Админ меню", reply_markup=menuAdmin)


@dp.callback_query_handler(lambda c: c.data == 'stats')
async def stats(call: types.CallbackQuery):
    await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                text=f"Всего в базе <code>{len(Users.select())}</code> пользователей.",
                                reply_markup=menuAdmin, parse_mode='html')


@dp.callback_query_handler(lambda c: c.data == 'mailing')
async def mailing(call: types.CallbackQuery):
    await call.message.delete()
    await call.message.answer('Введите текст рассылки:', reply_markup=menu)
    await AdminState.mailing.set()


@dp.message_handler(state=AdminState.mailing, content_types=types.ContentType.ANY)
async def mailing(message: types.Message, state: FSMContext):
    await bot.delete_message(chat_id=message.from_user.id, message_id=message.message_id)
    await message.answer("Рассылка начата.")
    success = 0
    errors = 0
    for user in Users.select():
        try:
            success += 1
            if types.ContentType.TEXT == message.content_type:
                await bot.send_message(user.user_id, message.text)

            elif types.ContentType.VIDEO == message.content_type:
                await bot.send_video(chat_id=user.user_id, video=message.video.file_id,
                                     caption=message.html_text if message.caption else None)

            elif types.ContentType.ANIMATION == message.content_type:
                await bot.send_animation(chat_id=user.user_id, animation=message.animation.file_id,
                                         caption=message.html_text if message.caption else None)

            elif types.ContentType.STICKER == message.content_type:
                await bot.send_sticker(chat_id=user.user_id, sticker=message.sticker.file_id)

            elif types.ContentType.PHOTO == message.content_type:
                await bot.send_photo(chat_id=user.user_id, photo=message.photo[-1].file_id,
                                     caption=message.html_text if message.caption else None)
        except:
            errors += 1
    await message.answer(f"Рассылка окончена.\n\nУспешно: {success}\nОшибок: {errors}", reply_markup=menuAdmin)
    await state.reset_state(with_data=False)


@dp.callback_query_handler(lambda c: c.data == 'cancel', state="*")
async def cancel_promo(call: types.CallbackQuery, state: FSMContext):
    await call.message.delete()
    await state.finish()
    await call.message.answer("Админ меню", reply_markup=menuAdmin)
