from bot import dp, types, FSMContext
from motor_client import SingletonClient
from loguru import logger
from bson.objectid import ObjectId


@dp.message_handler(commands=['hwlist'])
@dp.message_handler(lambda message: message.chat.type == 'private' and message.text == 'Список домашних заданий')
async def admin_menu(message: types.Message):
    telegram_id = message.from_user.id
    db = SingletonClient.get_data_base()

    user = await db.Users.find_one({
        "telegram_id": telegram_id
    })

    if not user:
        return await message.reply('Вы не зарегистрированы. Зайдите в бота и напишите <code>/start</code>')
    elif not user.get('group_id'):
        return await message.reply('Вы не указали группу.')

    subjects_cursor = db.Subjects.find({
        "group_id": ObjectId(user.get("group_id"))
    })

    subjects_list = await subjects_cursor.to_list(length=await db.Subjects.count_documents({}))
    subjects_ids_list = [subject['_id'] for subject in subjects_list]

    homeworks_cursor = db.Homework.find({
        "subject_id": {"$in": subjects_ids_list}
    }).sort('deadline', 1)
    homeworks = await homeworks_cursor.to_list(length=await db.Homework.count_documents({}))
    homeworks_ = get_homeworks_list(homeworks, 0)
    logger.info(homeworks)

    markup = types.InlineKeyboardMarkup()
    if message.chat.type == 'private':
        string = '<b>Список ваших домашних заданий:</b>\n'
    else:
        string = f'<b>Список домашних заданий для {user["second_name"]} {user["first_name"]}:</b>\n'

    for homework in homeworks_:
        _string = homework['text'][0:15] + '...' + f" 📅 {homework['deadline'].strftime('%d.%m.%Y')}"
        button = types.InlineKeyboardButton(text=_string, callback_data=f'hw,{homework["_id"]}')
        markup.add(button)

    logger.info(get_homeworks_list(homeworks, 1))
    if get_homeworks_list(homeworks, 1):
        button_1 = types.InlineKeyboardButton(text="❌", callback_data=f'lsthw,n,0,{user["_id"]}')
        button_2 = types.InlineKeyboardButton(text="➡️", callback_data=f'lsthw,r,1,{user["_id"]}')
        markup.row(button_1, button_2)

    await message.answer(string, reply_markup=markup, disable_web_page_preview=True)


@dp.callback_query_handler(lambda callback_query: callback_query.data.split(',')[0] == 'lsthw')
async def handle_lsthw_callback_query(callback_query: types.CallbackQuery):
    """
    Обработчик нажатия на кнопку под сообщением с ближайшими парами.
    Лямбда проверяет, чтобы обрабатывалось только y кнопки
    Args:
        callback_query (types.CallbackQuery): Документация на сайте телеграма
    """

    split_data = callback_query.data.split(',')
    if split_data[1] == 'n':
        return await callback_query.answer(text='Там больше ничего нет...')

    page = int(split_data[2])
    user_id = ObjectId(split_data[3])

    db = SingletonClient.get_data_base()

    user = await db.Users.find_one({
        "_id": user_id
    })

    subjects_cursor = db.Subjects.find({
        "group_id": ObjectId(user.get("group_id"))
    }).sort('deadline', -1)

    subjects_list = await subjects_cursor.to_list(length=await db.Subjects.count_documents({}))
    subjects_ids_list = [subject['_id'] for subject in subjects_list]

    homeworks_cursor = db.Homework.find({
        "subject_id": {"$in": subjects_ids_list}
    }).sort('deadline', 1)
    homeworks = await homeworks_cursor.to_list(length=await db.Homework.count_documents({}))
    homeworks_ = get_homeworks_list(homeworks, page)

    markup = types.InlineKeyboardMarkup()

    for homework in homeworks_:
        _string = homework['text'][0:15] + '...' + f" 📅 {homework['deadline'].strftime('%d.%m.%Y')}"
        button = types.InlineKeyboardButton(text=_string, callback_data=f'hw,{homework["_id"]}')
        markup.add(button)

    # Проверяет, есть ли пары на предыдущих страницах.
    min_obj_list = get_homeworks_list(homeworks, page - 1)
    if min_obj_list:
        left_button = types.InlineKeyboardButton(
            text='⬅️', callback_data=f'lsthw,l,{page - 1},{user_id}')
    else:
        left_button = types.InlineKeyboardButton(
            text='❌', callback_data=f'lsthw,n,{page},{user_id}')

    # Проверяет, есть ли пары на следующих страницах.
    min_obj_list = get_homeworks_list(homeworks, page + 1)
    if min_obj_list:
        right_button = types.InlineKeyboardButton(
            text='➡️', callback_data=f'lsthw,r,{page + 1},{user_id}')
    else:
        right_button = types.InlineKeyboardButton(
            text='❌', callback_data=f'lsthw,n,{page},{user_id}')

    markup.row(left_button, right_button)

    if callback_query.message.chat.type == 'private':
        string = '<b>Список ваших домашних заданий:</b>\n'
    else:
        string = f'<b>Список домашних заданий для {user["second_name"]} {user["first_name"]}:</b>\n'
    _message = await callback_query.message.edit_text(string, reply_markup=markup, parse_mode='HTML',
                                                      disable_web_page_preview=True)
    await callback_query.answer()


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('hw'))
async def handle_hw_callback(callback_query: types.CallbackQuery, state: FSMContext):
    homework_id = ObjectId(callback_query.data.split(',')[1])
    db = SingletonClient.get_data_base()
    homework = await db.Homework.find_one({
        '_id': homework_id
    })
    string = homework['text']
    string += f"\n\nДедлайн - {homework['deadline']}"
    await callback_query.message.reply(string)


def get_homeworks_list(hw_list, page):
    logger.info(hw_list)
    try:
        return hw_list[page*5:page*5 + 5]
    except IndexError:
        return []
