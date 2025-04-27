import asyncio
import locale
import logging
import os
from datetime import datetime

import arrow
import matplotlib.pyplot as plt
import pandas as pd
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State as _State
from babel.dates import format_datetime, format_date

from create_bot import dp, bot
from misc.database import *
from misc.keyboards import *

class UserState(StatesGroup):
    waiting_for_time = _State()
    add_habit = _State()
    add_habit_second = _State()
    add_habit_third = _State()
    add_habit_fourth = _State()
    upd_habit = _State()
    upd_habit_second = _State()
    upd_habit_third = _State()
    upd_habit_fourth = _State()

logging.basicConfig(level=logging.INFO)

day_mapping = {
    'понедельник': 1,
    'вторник': 2,
    'среда': 3,
    'четверг': 4,
    'пятница': 5,
    'суббота': 6,
    'воскресенье': 7
}

async def send_notifications():
    while True:
        try:
            current_time = arrow.now('Europe/Moscow').format('H:mm')
            logging.info(f'Текущее время: {current_time}')
            users_with_notifications = Users.select().where(Users.notices == True)
            for user in users_with_notifications:
                if current_time == user.time_notices:
                    habits = Habits.select().where(Habits.user_id == user.user_id)
                    today_day = arrow.now('Europe/Moscow').isoweekday()
                    habit_list = []
                    for habit in habits:
                        days_list = habit.days.split(',')
                        days_as_numbers = []
                        for day in days_list:
                            day = day.strip().lower()
                            if day in day_mapping:
                                days_as_numbers.append(day_mapping[day])
                            else:
                                logging.warning(f'Неизвестный день: {day}')
                        if today_day in days_as_numbers:
                            habit_list.append(habit.name)
                    if habit_list:
                        await bot.send_message(user.user_id, f"Ваши привычки на сегодня:\n\n" + "\n".join(habit_list))
                        logging.info(f'Уведомление отправлено пользователю {user.user_id}: {habit_list}')
        except Exception as e:
            logging.error(f'Произошла ошибка: {e}')
        await asyncio.sleep(60)

async def start(message: types.Message):
    if not Users.select().where(Users.user_id == message.chat.id).exists():
        Users.create(user_id=message.chat.id)
    await message.answer("🔝 Главное меню", reply_markup=menuUser)

async def handler(message: types.Message):
    if not Users.select().where(Users.user_id == message.chat.id).exists():
        return await message.answer("Напиши /start.")
    if message.text == '❓ Помощь':
        await message.answer('Действующая администрация:', reply_markup=support)
    elif message.text == '➕ Добавить привычку':
        await message.answer('Введите название привычки', reply_markup=menuUserCancel)
        await UserState.add_habit.set()
    elif message.text == '📋 Мои привычки':
        if not Habits.select().where(Habits.user_id == message.chat.id).exists():
            return await message.answer('У вас нет привычек, добавьте их через главное меню.', reply_markup=menuUser)
        habits = InlineKeyboardMarkup()
        for habit in Habits.select().where(Habits.user_id == message.chat.id):
            habits.add(
                InlineKeyboardButton(text=f'{habit.name}', callback_data=f'habits_{habit.id}')
            )
        habits.add(
            InlineKeyboardButton(text="Назад", callback_data='cancel_user')
        )
        await message.answer('Ваши привычки:', reply_markup=habits)
    elif message.text == '✅ Отметить выполнение':
        if not Habits.select().where(Habits.user_id == message.chat.id).exists():
            return await message.answer('У вас нет привычек, добавьте их через главное меню.', reply_markup=menuUser)
        now = arrow.now()
        day_of_week = format_datetime(now.datetime, 'EEEE', locale='ru_RU')
        formatted_date = format_date(now.date(), format='dd MMMM yyyy', locale='ru_RU')
        habits = InlineKeyboardMarkup()
        has_habits_today = False
        for habit in Habits.select().where(Habits.user_id == message.chat.id):
            if day_of_week in habit.days:
                if formatted_date not in habit.history:
                    habits.add(
                        InlineKeyboardButton(text=f'{habit.name}', callback_data=f'habits_executed|{habit.id}')
                    )
                    has_habits_today = True
        if not has_habits_today:
            return await message.answer('У вас нет запланированных привычек на сегодня', reply_markup=menuUser)
        habits.add(
            InlineKeyboardButton(text="Назад", callback_data='cancel_user')
        )
        await message.answer('Выберите привычку:', reply_markup=habits)
    elif message.text == '⚙️ Настройки':
        await message.answer('Настройки:', reply_markup=settings)
    elif message.text == '📊 Статистика':
        if not Habits.select().where(Habits.user_id == message.chat.id).exists():
            return await message.answer('У вас нет привычек, добавьте их через главное меню.', reply_markup=menuUser)
        habits = InlineKeyboardMarkup()
        for habit in Habits.select().where(Habits.user_id == message.chat.id):
            habits.add(
                InlineKeyboardButton(text=f'{habit.name}', callback_data=f'habits_history|{habit.id}')
            )
        habits.add(
            InlineKeyboardButton(text="Назад", callback_data='cancel_user')
        )
        await message.answer('Выберите привычку:', reply_markup=habits)

def parse_date(date_str):
    months = {
        'января': 1,
        'февраля': 2,
        'марта': 3,
        'апреля': 4,
        'мая': 5,
        'июня': 6,
        'июля': 7,
        'августа': 8,
        'сентября': 9,
        'октября': 10,
        'ноября': 11,
        'декабря': 12
    }
    parts = date_str.strip().split()
    day = int(parts[0])
    month_name = parts[1]
    year = int(parts[2])
    month = months.get(month_name)
    if month is None:
        raise ValueError(f"Некорректное название месяца: {month_name}")
    return datetime(year, month, day)

@dp.callback_query_handler(lambda c: 'habits_history|' in c.data)
async def habits_history(call: types.CallbackQuery):
    await call.message.delete()
    habits_id = call.data.split('|')[1]
    habitInfo = Habits.select().where(Habits.id == habits_id)[0]
    menuUserCancelHistory = InlineKeyboardMarkup()
    menuUserCancelHistory.add(
        InlineKeyboardButton(text='Назад', callback_data='cancel_user_history')
    )
    if not habitInfo.history:
        await call.message.answer(f'История привычки {habitInfo.name} пуста!', reply_markup=menuUserCancelHistory, parse_mode='html')
        return
    history_cleaned = habitInfo.history.strip(", ")
    dates_str = history_cleaned.split(", ")
    dates = []
    for date_str in dates_str:
        try:
            date = parse_date(date_str)
            dates.append(date)
        except ValueError as e:
            print(f"Ошибка разбора даты: {date_str} - {e}")
    if not dates:
        await call.message.answer(f'Все даты в истории привычки {habitInfo.name} некорректны!', reply_markup=menuUserCancelHistory, parse_mode='html')
        return
    try:
        locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
    except locale.Error as e:
        print(f"Ошибка установки локали: {e}")
    dates_text = "\n".join([d.strftime("%d %B %Y") for d in dates])
    df = pd.DataFrame(dates, columns=['date'])
    df['count'] = 1
    daily_counts = df.groupby(df['date']).count().reset_index()
    daily_counts = daily_counts.sort_values('date')
    user_id = call.from_user.id
    photo_dir = f"photo/{user_id}"
    if not os.path.exists(photo_dir):
        os.makedirs(photo_dir)
    filename = f"habit_statistics_{user_id}.png"
    filepath = os.path.join(photo_dir, filename)
    plt.figure(figsize=(12, 6))
    plt.bar(daily_counts['date'], daily_counts['count'], color='skyblue')
    plt.title(f'Статистика выполнения привычки "{habitInfo.name}" по дням')
    plt.xlabel('Дата')
    plt.ylabel('Количество выполненных действий')
    plt.xticks(rotation=45, ha='right')
    plt.gca().xaxis.set_major_locator(plt.MaxNLocator(10))
    plt.tight_layout()
    plt.grid(axis='y')
    plt.savefig(filepath)
    plt.close()
    try:
        with open(filepath, 'rb') as photo:
            await call.message.answer_photo(photo, caption=f'Статистика по привычке {habitInfo.name}\n\n' f'Даты выполнения:\n{dates_text}', reply_markup=menuUserCancelHistory, parse_mode='html')
    except Exception as e:
        print(f"Ошибка при отправке фото: {e}")
        await call.message.answer(f"Произошла ошибка при отправке статистики.")
    finally:
        try:
            os.remove(filepath)
            print(f"Файл {filepath} удален.")
        except Exception as e:
            print(f"Ошибка при удалении файла {filepath}: {e}")

@dp.callback_query_handler(lambda c: c.data == 'cancel_user_history')
async def cancel_user_history(call: types.CallbackQuery):
    await call.message.delete()
    if not Habits.select().where(Habits.user_id == call.message.chat.id).exists():
        return await call.message.answer('У вас нет привычек, добавьте их через главное меню.', reply_markup=menuUser)
    habits = InlineKeyboardMarkup()
    for habit in Habits.select().where(Habits.user_id == call.message.chat.id):
        habits.add(
            InlineKeyboardButton(text=f'{habit.name}', callback_data=f'habits_history|{habit.id}')
        )
    habits.add(
        InlineKeyboardButton(text="Назад", callback_data='cancel_user')
    )
    await call.message.answer('Выберите привычку:', reply_markup=habits)

@dp.callback_query_handler(lambda c: c.data == 'notices')
async def notices(call: types.CallbackQuery):
    await call.message.delete()
    userinfo = Users.select().where(Users.user_id == call.message.chat.id)[0]
    notices_set = InlineKeyboardMarkup()
    if userinfo.notices:
        notices_set.add(
            InlineKeyboardButton(text='Выключить', callback_data=f'fire_notices|{call.message.chat.id}')
        )
    else:
        notices_set.add(
            InlineKeyboardButton(text='Включить', callback_data=f'fire_notices|{call.message.chat.id}')
        )
    notices_set.add(
        InlineKeyboardButton(text="Изменить время", callback_data=f'changetime_notices|{call.message.chat.id}')
    )
    notices_set.add(
        InlineKeyboardButton(text="Назад", callback_data='cancel_settings')
    )
    await call.message.answer(f'Настройка уведомлений\n\nУведомления будут приходить в бота в <code>{userinfo.time_notices}</code> по мск', reply_markup=notices_set, parse_mode='html')

@dp.callback_query_handler(lambda c: c.data == 'cancel_settings')
async def cancel_settings(call: types.CallbackQuery):
    await call.message.delete()
    await call.message.answer('Настройки:', reply_markup=settings)

@dp.callback_query_handler(lambda c: 'fire_notices|' in c.data)
async def fire_notices(call: types.CallbackQuery):
    await call.message.delete()
    user_id = call.data.split('|')[1]
    userinfo = Users.select().where(Users.user_id == call.message.chat.id)[0]
    Users.update(notices=not userinfo.notices).where(Users.user_id == user_id).execute()
    userinfo = Users.select().where(Users.user_id == call.message.chat.id)[0]
    notices_set = InlineKeyboardMarkup()
    if userinfo.notices:
        notices_set.add(
            InlineKeyboardButton(text='Выключить', callback_data=f'fire_notices|{call.message.chat.id}')
        )
    else:
        notices_set.add(
            InlineKeyboardButton(text='Включить', callback_data=f'fire_notices|{call.message.chat.id}')
        )
    notices_set.add(
        InlineKeyboardButton(text="Изменить время", callback_data=f'changetime_notices|{call.message.chat.id}')
    )
    notices_set.add(
        InlineKeyboardButton(text="Назад", callback_data='cancel_settings')
    )
    await call.message.answer(f'Настройка уведомлений\n\nУведомления будут приходить в бота в <code>{userinfo.time_notices}</code> по мск', reply_markup=notices_set, parse_mode='html')

@dp.callback_query_handler(lambda c: 'habits_executed|' in c.data)
async def habits_executed(call: types.CallbackQuery):
    await call.message.delete()
    habit_id = call.data.split('|')[1]
    now = arrow.now()
    formatted_date = now.format('DD MMMM YYYY', locale='ru')
    habitInfo = Habits.select().where(Habits.id == habit_id)[0]
    if habitInfo.history:
        habitInfo.history += f', {formatted_date}'
    else:
        habitInfo.history = formatted_date
    habitInfo.save()
    await call.message.answer(f'Привычка <code>{habitInfo.name}</code> отмечена как выполненная!', reply_markup=menuUser, parse_mode='html')

@dp.callback_query_handler(lambda c: 'changetime_notices|' in c.data)
async def change_time_notices(call: types.CallbackQuery):
    await call.message.delete()
    await call.message.answer("Введите новое время уведомлений в формате HH:MM (например, 14:30):", reply_markup=menuUserCancel)
    await UserState.waiting_for_time.set()

@dp.message_handler(state=UserState.waiting_for_time)
async def process_new_time(message: types.Message, state: FSMContext):
    new_time = message.text.strip()
    try:
        time_obj = arrow.get(new_time, 'HH:mm')
        formatted_time = time_obj.format('HH:mm')
    except arrow.parser.ParserError:
        await message.answer("Неверный формат времени. Пожалуйста, используйте HH:MM.", reply_markup=menuUserCancel)
        return
    Users.update(time_notices=formatted_time).where(Users.user_id == message.chat.id).execute()
    userinfo = Users.select().where(Users.user_id == message.chat.id)[0]
    notices_set = InlineKeyboardMarkup()
    if userinfo.notices:
        notices_set.add(
            InlineKeyboardButton(text='Выключить', callback_data=f'fire_notices|{message.chat.id}')
        )
    else:
        notices_set.add(
            InlineKeyboardButton(text='Включить', callback_data=f'fire_notices|{message.chat.id}')
        )
    notices_set.add(
        InlineKeyboardButton(text="Изменить время", callback_data=f'changetime_notices|{message.chat.id}')
    )
    notices_set.add(
        InlineKeyboardButton(text="Назад", callback_data='cancel_settings')
    )
    await message.answer(f"Время уведомлений изменено на <code>{formatted_time}</code> по мск.", parse_mode='html', reply_markup=notices_set)
    await state.finish()

@dp.callback_query_handler(lambda c: 'habits_' in c.data)
async def habitinfo(call: types.CallbackQuery):
    await call.message.delete()
    habit_id = call.data.split('_')[1]
    habitInfo = Habits.select().where(Habits.id == habit_id)[0]
    backuserhabit = InlineKeyboardMarkup()
    backuserhabit.add(
        InlineKeyboardButton(text='Изменить', callback_data=f'changeHabits_{habit_id}')
    ).add(
        InlineKeyboardButton(text='Удалить', callback_data=f'delHabits_{habit_id}')
    ).add(
        InlineKeyboardButton(text='Назад', callback_data='backUser_habit')
    )
    await call.message.answer(f'Привычка: <code>{habitInfo.name}</code>\nЦель: <code>{habitInfo.target}</code>\nДни выполнения: <code>{habitInfo.days}</code>', reply_markup=backuserhabit, parse_mode='html')

@dp.callback_query_handler(lambda c: 'changeHabits_' in c.data)
async def changeHabits(call: types.CallbackQuery, state: FSMContext):
    await call.message.delete()
    habit_id = call.data.split('_')[1]
    await state.update_data(habit_id=habit_id)
    await call.message.answer('Введите новое название привычки', reply_markup=menuUserCancel)
    await UserState.upd_habit.set()

@dp.message_handler(state=UserState.upd_habit)
async def upd_habit(message: types.Message, state: FSMContext):
    await state.update_data(habit=message.text)
    await message.answer('Введите новую цель\n(Например, "пить 2 литра воды в день")', reply_markup=menuUserCancel)
    await UserState.upd_habit_second.set()

@dp.message_handler(state=UserState.upd_habit_second)
async def upd_habit_second(message: types.Message, state: FSMContext):
    await state.update_data(target=message.text)
    await message.answer('Введите дни недели, когда привычка должна выполняться (например, понедельник, среда)', reply_markup=menuUserCancel)
    await UserState.upd_habit_third.set()

@dp.message_handler(state=UserState.upd_habit_third)
async def upd_habit_third(message: types.Message, state: FSMContext):
    await state.update_data(days=message.text)
    data = await state.get_data()
    days = data['days']
    days = [day.strip().lower() for day in days.split(',')]
    lastmenu_addhabit = InlineKeyboardMarkup()
    lastmenu_addhabit.add(
        InlineKeyboardButton(text='Сохранить', callback_data=f'updhabit_')
    ).add(
        InlineKeyboardButton(text='Отмена', callback_data='cancel_user')
    )
    await message.answer(f'Ваша привычка: <code>{data["habit"]}</code>\nВаша цель: <code>{data["target"]}</code>\nДни выполнения: <code>{",".join(days)}</code>', reply_markup=lastmenu_addhabit, parse_mode='html')
    await UserState.upd_habit_fourth.set()

@dp.callback_query_handler(lambda c: c.data == 'updhabit_', state=UserState.upd_habit_fourth)
async def updhabit_finish(call: types.CallbackQuery, state: FSMContext):
    await call.message.delete()
    data = await state.get_data()
    days = data['days']
    days = [day.strip().lower() for day in days.split(',')]
    Habits.update(user_id=call.message.chat.id, name=data["habit"], target=data["target"], days=','.join(days)).where(Habits.id == data["habit_id"]).execute()
    await call.message.answer(f'Обновил привычку: <code>{data["habit"]}</code>\nЦель: <code>{data["target"]}</code>\nДни выполнения: <code>{",".join(days)}</code>', reply_markup=menuUser, parse_mode='html')
    await state.reset_state(with_data=False)

@dp.callback_query_handler(lambda c: 'delHabits_' in c.data)
async def delHabit(call: types.CallbackQuery):
    await call.message.delete()
    habit_id = call.data.split('_')[1]
    habitInfo = Habits.select().where(Habits.id == habit_id)[0]
    habitInfo.delete_instance()
    await call.message.answer('Удалил!', reply_markup=menuUser)

@dp.callback_query_handler(lambda c: c.data == 'backUser_habit', state="*")
async def backUser_habit(call: types.CallbackQuery):
    await call.message.delete()
    habits = InlineKeyboardMarkup()
    for habit in Habits.select().where(Habits.user_id == call.message.chat.id):
        habits.add(
            InlineKeyboardButton(text=f'{habit.name}', callback_data=f'habits_{habit.id}')
        )
    habits.add(
        InlineKeyboardButton(text="Назад", callback_data='cancel_user')
    )
    await call.message.answer('Ваши привычки:', reply_markup=habits)

@dp.message_handler(state=UserState.add_habit)
async def add_habit(message: types.Message, state: FSMContext):
    await state.update_data(habit=message.text)
    await message.answer('Введите вашу цель\n(Например, "пить 2 литра воды в день")', reply_markup=menuUserCancel)
    await UserState.add_habit_second.set()

@dp.message_handler(state=UserState.add_habit_second)
async def add_habit_second(message: types.Message, state: FSMContext):
    await state.update_data(target=message.text)
    await message.answer('Введите дни недели, когда привычка должна выполняться (например, понедельник, среда)', reply_markup=menuUserCancel)
    await UserState.add_habit_third.set()

@dp.message_handler(state=UserState.add_habit_third)
async def add_habit_third(message: types.Message, state: FSMContext):
    data = await state.get_data()
    habit = data['habit']
    target = data['target']
    await state.update_data(days=message.text)
    lastmenu_addhabit = InlineKeyboardMarkup()
    lastmenu_addhabit.add(
        InlineKeyboardButton(text='Сохранить', callback_data=f'savehabit_')
    ).add(
        InlineKeyboardButton(text='Отмена', callback_data='cancel_user')
    )
    await message.answer(f'Ваша привычка: <code>{habit}</code>\nВаша цель: <code>{target}</code>\nДни выполнения: {message.text}', reply_markup=lastmenu_addhabit, parse_mode='html')
    await UserState.add_habit_fourth.set()

@dp.callback_query_handler(lambda c: c.data == 'savehabit_', state=UserState.add_habit_fourth)
async def savehabit(call: types.CallbackQuery, state: FSMContext):
    await call.message.delete()
    data = await state.get_data()
    habit = data['habit']
    target = data['target']
    days = data['days']
    days = [day.strip().lower() for day in days.split(',')]
    Habits.create(user_id=call.message.chat.id, name=habit, target=target, days=','.join(days))
    await call.message.answer(f'Добавил новую привычку: <code>{habit}</code>\nЦель: <code>{target}</code>\nДни выполнения: <code>{", ".join(days)}</code>', reply_markup=menuUser, parse_mode='html')
    await state.reset_state(with_data=False)

@dp.callback_query_handler(lambda c: c.data == 'cancel_user', state="*")
async def cancel_user(call: types.CallbackQuery, state: FSMContext):
    await call.message.delete()
    await state.finish()
    await call.message.answer("🔝 Главное меню", reply_markup=menuUser)

def register_handlers_user():
    dp.register_message_handler(start, commands=['start'])
    dp.register_message_handler(handler)