from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

menuUser = ReplyKeyboardMarkup(resize_keyboard=True)
menuUser.add('➕ Добавить привычку', '📋 Мои привычки', '✅ Отметить выполнение').add('📊 Статистика', '⚙️ Настройки',  '❓ Помощь')

menuAdmin = InlineKeyboardMarkup()
menuAdmin.add( 
    InlineKeyboardButton(text='Рассылка', callback_data='mailing'),
    InlineKeyboardButton(text='Статистика', callback_data='stats')
)

menu = InlineKeyboardMarkup()
menu.add(
    InlineKeyboardButton(text='Отмена', callback_data='cancel')
)

support = InlineKeyboardMarkup()
support.add(
    InlineKeyboardButton(text='rastik002', url='https://t.me/rastik_lzt')
)

menuUserCancel = InlineKeyboardMarkup()
menuUserCancel.add(
    InlineKeyboardButton(text='Отмена', callback_data='cancel_user')
)

settings = InlineKeyboardMarkup()
settings.add(
    InlineKeyboardButton(text='Уведомления', callback_data='notices')
)