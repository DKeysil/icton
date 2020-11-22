from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from bot import bot
from bot import dp, types, FSMContext
import os
import smtplib, mimetypes, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import re
import time
import random
from motor_client import SingletonClient
from aiogram.dispatcher.filters.state import State, StatesGroup
from loguru import logger
from email import encoders


class SendingEmail(StatesGroup):
    confirmation = State()
    code_accepting = State()
    format_direction = State()
    format_email = State()


class FormatEmail(StatesGroup):
    subject = State()
    body = State()


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
    process_attachment(msg)

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
    if message.text == code:
        logger.info('email has been accepted')
        await message.answer('Вы успешно подтвердили свою почту\nТеперь вы можете пользоваться командой /send_email')
        await db.Users.update_one({"telegram_id": message.from_user.id}, {'$set': {"email": user_email,
                                                                                   "email_confirmation": True}})
        await format_direction(message, state, db)
        await SendingEmail.format_email.set()
    else:
        logger.info('got an incorrect confirmation code')
        await message.reply('Вы ввели неправильный код. Попробуйте еще раз.')


async def format_direction(message, state, db):
    async with state.proxy() as data:
        group = data.get('group_id')
    subjects = db.Subjects.find({'group_id': group})
    for subject in await subjects.to_list(length=100):
        teacher_id = subject['teacher_id']
        teacher = await db.Teachers.find_one({"_id": teacher_id})
        text = f"{teacher['first_name']} {teacher['second_name']} {teacher['third_name']}" \
               f"\nНомер ису: {teacher['isu_number']}"
        await message.answer(text, reply_markup=sending_email_keyboard(teacher['email']))
        logger.info('Preparing email to {0}'.format(teacher['email']))
    pass


@dp.message_handler(lambda message: message.chat.type == 'private', commands=['send_email'])
async def send_email_message(message: types.Message, state: FSMContext, teacher_email=''):
    logger.info('command: /send_email')
    db = SingletonClient.get_data_base()
    telegram_id = message.from_user.id

    user = await db.Users.find_one({
        "telegram_id": telegram_id
    })
    await state.update_data(group_id=user['group_id'])
    logger.info(user)
    if user['email_confirmation']:
        if not teacher_email:
            logger.info('Ready to format an email')
            await format_direction(message, state, db)
            await SendingEmail.format_email.set()
        else:
            await state.update_data(teacher_email=teacher_email)
            await message.answer('Введите текст заголовка:')
            await FormatEmail.subject.set()

    else:
        logger.info('Can not sand an email.\nNeed email confirmation')
        await message.answer('Во избежание спама и датамусора мне нужно подтвердить ваш email.\nПожалуйста, '
                             'введите его:')
        await SendingEmail.confirmation.set()


def sending_email_keyboard(teacher_email):
    markup = types.InlineKeyboardMarkup()

    button = types.InlineKeyboardButton(text="Написать письмо", callback_data=teacher_email)
    markup.add(button)
    return markup


def sending_file_keyboard():
    markup = types.InlineKeyboardMarkup()

    button = types.InlineKeyboardButton(text="Прикрепить файл", callback_data='attach_file')
    markup.add(button)

    button = types.InlineKeyboardButton(text="Завершить", callback_data='send')
    markup.add(button)
    return markup


def send_keyboard():
    markup = types.InlineKeyboardMarkup()

    button = types.InlineKeyboardButton(text="Отправить", callback_data='send')
    markup.add(button)
    return markup


@dp.callback_query_handler(state=[SendingEmail.format_email])
async def format_message(callback_query: types.CallbackQuery, state: FSMContext):
    teacher_email = callback_query.data
    await callback_query.message.edit_reply_markup()
    await callback_query.message.answer('Введите текст заголовка')
    await FormatEmail.subject.set()
    await state.update_data(teacher_email=teacher_email)


@dp.message_handler(state=FormatEmail.subject)
async def set_subject(message: types.Message, state:FSMContext):
    if message.text != '':
        subject = message.text
        logger.info('subject: {0}'.format(subject))
        await state.update_data(subject=subject)
        await message.answer("Введите текст вашего письма")
        await FormatEmail.body.set()
    else:
        logger.info('Empty subject has been inputted')
        await message.reply('Заголовок не может быть пустым.\nПожалуйста введите текст заголовка:')


@dp.message_handler(state=[FormatEmail.body])
async def set_text(message: types.Message, state: FSMContext):
    text = message.text
    await state.update_data(text=text)
    logger.info(text)
    await message.answer('Ваше сообщение почти отправлено!', reply_markup=sending_file_keyboard())


@dp.callback_query_handler(lambda callback_query: callback_query.data == 'send', state=[FormatEmail.body])
async def send(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_reply_markup()
    await callback_query.message.answer('Ваше сообщение успешно отправлено.')
    logger.info('Sending complete')
    async with state.proxy() as data:
        subject = data.get('subject')
        text = data.get('text')
        teacher_email = data.get('teacher_email')
    await send_an_email(teacher_email, subject, text)

    await state.finish()


@dp.callback_query_handler(lambda callback_query: callback_query.data == 'attach_file', state=[FormatEmail.body])
async def attach_files_to_email(callback_query: types.CallbackQuery):
    logger.info('Attaching files')
    await callback_query.message.edit_reply_markup()
    await callback_query.message.answer('Отправьте в чат все файлы, которые хотите прикрепить,'
                                        ' а после нажмите "Отправить"', reply_markup=send_keyboard())


def process_attachment(msg):
    dirpath = r'/nvsywbot/buffer'
    dir = os.listdir(dirpath)
    for file in dir:
        attach_file(msg,dirpath+"/"+file)
        os.remove(dirpath+"/"+file)


def attach_file(msg, filepath):
    filename = os.path.basename(filepath)
    ctype, encoding = mimetypes.guess_type(filepath)
    if ctype is None or encoding is not None:
        ctype = 'application/octet-stream'
    maintype, subtype = ctype.split('/', 1)
    if maintype == 'text':
        with open(filepath) as fp:
            file = MIMEText(fp.read(), _subtype=subtype)
            fp.close()
    elif maintype == 'image':
        with open(filepath, 'rb') as fp:
            file = MIMEImage(fp.read(), _subtype=subtype)
            fp.close()
    elif maintype == 'audio':
        with open(filepath, 'rb') as fp:
            file = MIMEAudio(fp.read(), _subtype=subtype)
            fp.close()
    else:
        with open(filepath, 'rb') as fp:
            file = MIMEBase(maintype, subtype)
            file.set_payload(fp.read())
            fp.close()
            encoders.encode_base64(file)
    file.add_header('Content-Disposition', 'attachment', filename=filename)
    msg.attach(file)


@dp.message_handler(content_types=['document'], state=FormatEmail.body)
async def adding_file_to_email(message: types.Message):
    logger.info('Added new document to buffer')
    file_info = await bot.get_file(message.document.file_id)
    filepath = r'/nvsywbot/buffer/{0}'.format(message.document.file_name)
    await bot.download_file(file_info.file_path, destination=filepath)


