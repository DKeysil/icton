from bot import dp, types, FSMContext
from motor_client import SingletonClient
from loguru import logger
from aiogram.dispatcher.filters.state import State, StatesGroup


class Start(StatesGroup):
    name = State()
    isu_num = State()
    finish_ = State()


@dp.message_handler(lambda message: message.chat.type == 'private', commands=['start'])
async def start(message: types.Message):
    logger.info('command: /start')
    telegram_id = message.from_user.id
    logger.info(telegram_id)
    db = SingletonClient.get_data_base()

    user = await db.Users.find_one({
        "telegram_id": telegram_id
    })

    logger.info(user)

    if user:
        logger.info(f'user exist.')
        return await message.reply('Вы уже зарегистрированы.')

    await message.reply('Введите <b>Фамилию Имя Отчество</b>.')
    await Start.name.set()


@dp.message_handler(state=[Start.name])
async def set_name(message: types.Message, state: FSMContext):
    await state.update_data(telegram_id=message.from_user.id)
    if len(message.text.split(' ')) == 3:
        second_name, first_name, third_name = message.text.split(' ')
        await state.update_data(second_name=second_name)
        await state.update_data(first_name=first_name)
        await state.update_data(third_name=third_name)

        logger.info(f'Start by: {message.from_user.id}. Name: {second_name + " " + first_name + " " + third_name}')
        await message.answer('Введите номер ису в формате: <b>284431</b>.')
        await Start.isu_num.set()
    else:
        await message.reply('Неверный формат.\n\nВведите <b>Фамилию Имя Отчество</b>.')


@dp.message_handler(state=[Start.isu_num])
async def set_isu_num(message: types.Message, state: FSMContext):
    try:
        if len(message.text.split(' ')) > 1:
            raise ValueError
        isu_number = int(message.text)

        await state.update_data(isu_number=isu_number)
        logger.info(f'Start by: {message.from_user.id}. Name: {isu_number}')

        await finish(message, state)

    except ValueError:
        await message.reply('Неверный формат.\n\nВведите номер ису в формате: <b>284431</b>.')


async def finish(message: types.Message, state: FSMContext):
    string = 'Проверьте введённые данные:\n\n'
    async with state.proxy() as data:
        string += f"ФИО: {data.get('second_name')} {data.get('first_name')} {data.get('third_name')}\n"
        string += f'Номер в ИСУ: {data.get("isu_number")}'
    await Start.finish_.set()
    await message.answer(string, reply_markup=under_event_keyboard())


def under_event_keyboard():
    markup = types.InlineKeyboardMarkup()

    button = types.InlineKeyboardButton(text="✅ Подтвердить", callback_data='Accept')
    markup.add(button)

    button = types.InlineKeyboardButton(text="❌ Начать заново", callback_data='Restart')
    markup.add(button)
    return markup


@dp.callback_query_handler(lambda callback_query: callback_query.data == 'Accept', state=[Start.finish_])
async def accept_callback(callback_query: types.CallbackQuery, state: FSMContext):
    db = SingletonClient.get_data_base()

    async with state.proxy() as data:
        result = await db.Users.insert_one({
            'telegram_id': data.get('telegram_id'),
            'first_name': data.get('first_name'),
            'second_name': data.get('second_name'),
            'third_name': data.get('third_name'),
            'isu_number': data.get('isu_number'),
            'email_confirmation': False
        })
        logger.info(f'Start by: {callback_query.message.from_user.id}\n'
                    f'insert_one user in db status: {result.acknowledged}')

    await callback_query.message.edit_reply_markup()
    await callback_query.message.answer('Вы успешно зарегистрировались.')
    await state.finish()


@dp.callback_query_handler(lambda callback_query: callback_query.data == 'Restart', state=[Start.finish_])
async def decline_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await Start.name.set()
    logger.info(f'New event by: {callback_query.message.from_user.id}\nrestarted')
    await callback_query.message.answer('Попробуем ещё раз.\n\nВведите <b>Фамилию Имя Отчество</b>.')
