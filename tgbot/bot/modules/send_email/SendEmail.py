from bot import dp, types, FSMContext
import os
import smtplib, email, mimetypes, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import re
import time
import random
from motor_client import SingletonClient
from aiogram.dispatcher.filters.state import State, StatesGroup
from loguru import logger


class SendingEmail(StatesGroup):
    confirmation = State()
    code_accepting = State()
    format_direction = State()
    format_email = State()
    finish = State()


async def format_message():
    pass


async def generate_code():
    code = ''
    random.seed(time.time())
    for i in range(6):
        num = random.randint(0, 9)
        code += str(num)
    return code


async def send_an_email(addr, subject, text):
    addr_from = "beti.itmo@gmail.com"
    password = os.environ['EMAIL_PASSWORD']

    port = 465
    context = ssl.create_default_context()

    msg = MIMEMultipart()
    msg['From'] = addr_from
    msg['To'] = addr
    msg['Subject'] = subject

    body = text
    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
        server.login(addr_from, password)
        server.sendmail(addr_from, addr, msg.as_string())
        server.quit()
    pass


@dp.message_handler(state=[SendingEmail.confirmation])
async def confirm_users_email(message: types.Message, state: FSMContext):
    filtered_message = re.search(r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)', message.text)
    logger.info(f'got a mailbox: {message.text}')
    if filtered_message.group(0) == message.text:
        logger.info('accepted')
        user_email = message.text
        await state.update_data(email=user_email)
        await message.answer('На вашу почту был отправлен код подтверждения.\nПожалуйста введите его:')
        logger.info(f'send a confirmation email to {user_email}')
        code = await generate_code()
        logger.info(f'confirmation code: {code}')
        await state.update_data(code=code)

        subject = "ПОДТВЕРЖДЕНИЕ ПОЧТЫ"
        addr = user_email
        text = code + "\nЭто ваш код подтверждения.\n" \
                      "Пожалуйста, не отвечайте на это сообщение.\nFrom Beti with love."
        await send_an_email(addr, subject, text)
        await SendingEmail.code_accepting.set()
    else:
        logger.info('got an incorrect email')
        await message.reply('Неверный формат.\nВведите <b>ваш email</b>.')


@dp.message_handler(state=[SendingEmail.code_accepting])
async def code_accepting(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        code = data.get('code')
        user_email = data.get('email')
    db = SingletonClient.get_data_base()
    user = db.Users.find_one({
        "telegram_id": message.from_user.id
    })
    if message.text == code:
        logger.info('email has been accepted')
        await message.answer('Вы успешно подтвердили свою почту')
        await db.Users.update_one({"telegram_id": message.from_user.id}, {'$set': {"email": user_email,
                                                                                   "email_confirmation": True}})
        await SendingEmail.format_direction.set()
    else:
        logger.info('got an incorrect confirmation code')
        await message.reply('Вы ввели неправильный код. Попробуйте еще раз.')


@dp.message_handler(lambda message: message.chat.type == 'private', commands=['send_email'])
async def send_email_message(message: types.Message, state: FSMContext):
    logger.info('command: /send_email')
    db = SingletonClient.get_data_base()
    telegram_id = message.from_user.id

    user = await db.Users.find_one({
        "telegram_id": telegram_id
    })
    logger.info(user)
    if user['email_confirmation']:
        logger.info('Ready to format an email')
        await SendingEmail.format_direction.set()
    else:
        logger.info('Can not sand an email.\nNeed email confirmation')
        await message.answer('Во избежание спама и датамусора мне нужно подтвердить ваш email.\nПожалуйста, '
                             'введите его:')
        await SendingEmail.confirmation.set()
