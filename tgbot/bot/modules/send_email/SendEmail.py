from bot import dp, types
import smtplib, email
from motor_client import SingletonClient
from aiogram.dispatcher.filters.state import State, StatesGroup


async def format_message():
    pass


async def confirm_users_email():
    pass


@dp.message_handler(lambda message: message.chat.type == 'private', commands=['send_email'])
async def send_email(message: types.Message):
    db = SingletonClient.get_data_base()
    telegram_id = message.from_user.id

    user = await db.Users.find_one({
        "telegram_id": telegram_id
    })
    if user['email_confirmation']:
        await format_message()
    else:
        await confirm_users_email()
    pass
