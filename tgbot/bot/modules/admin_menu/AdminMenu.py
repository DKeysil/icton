from bot import dp, types, FSMContext
from motor_client import SingletonClient
from loguru import logger
from aiogram.dispatcher.filters.state import State, StatesGroup
from bson.objectid import ObjectId
from dateutil.rrule import rrule
from datetime import datetime
from bot.modules.menu.Menu import menu_markup


class Menu(StatesGroup):
    admin = State()
    choose_action = State()
    add_homework = State()
    add_zoom_link = State()
    finish_ = State()


@dp.message_handler(lambda message: message.chat.type == 'private', commands=['admin'])
@dp.message_handler(lambda message: message.chat.type == 'private' and message.text == 'Функции админа')
async def admin_menu(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    db = SingletonClient.get_data_base()

    user = await db.Users.find_one({
        "telegram_id": telegram_id
    })
    logger.info(user)
    if not user:
        return await message.answer('Вы не зарегистрированы в боте.')

    group = await db.Groups.find_one({
        "admin_id": user['_id']
    })
    if not group:
        return await message.answer('Вы не админ группы.')

    await Menu.admin.set()
    await choose_action_menu(message)


@dp.message_handler(lambda message: message.text == 'Выйти', state=[Menu.admin, Menu.add_homework, Menu.add_zoom_link, Menu.choose_action])
async def exit_(message: types.Message, state: FSMContext):
    markup = await menu_markup(message.from_user.id)
    await message.answer('Done', reply_markup=markup)
    await state.finish()


@dp.message_handler(lambda message: message.text == 'Добавить ДЗ или ссылку на zoom', state=[Menu.admin])
async def choose_action_menu(message: types.Message):
    string = 'Меню добавления домашнего задания / ссылки на zoom.\nДомашнее задание | Ссылка на zoom | Название | Дата'
    markup = types.ReplyKeyboardMarkup()
    markup.add(types.KeyboardButton(text='Выйти'))
    await message.answer(string, reply_markup=markup)

    telegram_id = message.from_user.id
    db = SingletonClient.get_data_base()

    user = await db.Users.find_one({
        "telegram_id": telegram_id
    })

    markup = types.InlineKeyboardMarkup()
    min_obj_list = await get_min_obj_list(user, 0)

    for obj in min_obj_list:
        subj = obj[0]
        string = ''
        hw = await db.Homework.find_one({"subject_id": ObjectId(subj['_id']), "date": obj[1]})
        if hw:
            string += '✅ | '
        else:
            string += '❌ | '
        zm = await db.ZoomLinks.find_one({"subject_id": ObjectId(subj['_id']), "date": obj[1]})
        if zm:
            string += '✅ | '
        else:
            string += '❌ | '
        string += f"{subj['title']} {obj[1].strftime('%H:%M %d.%m.%Y')}"
        button = types.InlineKeyboardButton(text=string, callback_data=f'cha,{subj["_id"]},{obj[1]}')
        markup.add(button)

    """
    callback_data:
    1) am - название модуля
    2) l, r, n - left, right, none
    3) int - номер страницы
    4) user_id
    """
    if await get_min_obj_list(user, 0):
        button_1 = types.InlineKeyboardButton(text="❌", callback_data=f'am,n,0,{user["_id"]}')
        button_2 = types.InlineKeyboardButton(text="➡️", callback_data=f'am,r,1,{user["_id"]}')
        markup.row(button_1, button_2)

    string = 'Список ближайших пар и статус домашнего задания:'
    await message.answer(string, reply_markup=markup, disable_web_page_preview=True)


@dp.callback_query_handler(lambda callback_query: callback_query.data.split(',')[0] == 'am', state=[Menu.admin])
async def handle_am_callback_query(callback_query: types.CallbackQuery):
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

    min_obj_list = await get_min_obj_list(user, page)

    markup = types.InlineKeyboardMarkup()

    for obj in min_obj_list:
        subj = obj[0]
        string = ''
        hw = await db.Homework.find_one({"subject_id": ObjectId(subj['_id']), "date": obj[1]})
        if hw:
            string += '✅ | '
        else:
            string += '❌ | '
        zm = await db.ZoomLinks.find_one({"subject_id": ObjectId(subj['_id']), "date": obj[1]})
        if zm:
            string += '✅ | '
        else:
            string += '❌ | '
        string += f"{subj['title']} {obj[1].strftime('%H:%M %d.%m.%Y')}"
        button = types.InlineKeyboardButton(text=string, callback_data=f'cha,{subj["_id"]},{obj[1]}')
        markup.add(button)

    # Проверяет, есть ли пары на предыдущих страницах.
    min_obj_list = await get_min_obj_list(user, page - 1)
    if min_obj_list:
        left_button = types.InlineKeyboardButton(
            text='⬅️', callback_data=f'am,l,{page - 1},{user_id}')
    else:
        left_button = types.InlineKeyboardButton(
            text='❌', callback_data=f'am,n,{page},{user_id}')

    # Проверяет, есть ли пары на следующих страницах.
    min_obj_list = await get_min_obj_list(user, page + 1)
    if min_obj_list:
        right_button = types.InlineKeyboardButton(
            text='➡️', callback_data=f'am,r,{page + 1},{user_id}')
    else:
        right_button = types.InlineKeyboardButton(
            text='❌', callback_data=f'am,n,{page},{user_id}')

    markup.row(left_button, right_button)

    string = 'Список ближайших пар и статус домашнего задания:'
    _message = await callback_query.message.edit_text(string, reply_markup=markup, parse_mode='HTML',
                                                      disable_web_page_preview=True)
    await callback_query.answer()


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('cha'), state=[Menu.admin])
async def choose_action(callback_query: types.CallbackQuery, state: FSMContext):
    db = SingletonClient.get_data_base()
    subject_id = ObjectId(callback_query.data.split(',')[1])
    date = callback_query.data.split(',')[2]
    subject = await db.Subjects.find_one({
        '_id': ObjectId(subject_id)
    })
    await state.update_data(subject=subject)
    await state.update_data(date=date)

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text='Добавить домашнее задание', callback_data='tp,homework'))
    markup.add(types.InlineKeyboardButton(text='Добавить ссылку на zoom', callback_data='tp,zoom'))
    await callback_query.message.edit_text(f'Выберите что вы хотите добавить для <b>{subject["title"]}</b>:', reply_markup=markup)
    await Menu.choose_action.set()


@dp.callback_query_handler(lambda callback_query: callback_query.data == 'tp,homework', state=[Menu.choose_action])
async def add_homework(callback_query: types.CallbackQuery, state: FSMContext):
    subject = await state.get_data('subject')
    subject = subject['subject']
    await callback_query.message.answer(f'Пришлите домашнее задание, которое будет прикреплено к предмету <b>{subject["title"]}</b>')
    await Menu.add_homework.set()


@dp.message_handler(state=[Menu.add_homework])
async def get_homework(message: types.Message, state: FSMContext):
    db = SingletonClient.get_data_base()
    subject = await state.get_data("subject")
    subject = subject['subject']
    date = await state.get_data("date")
    date = datetime.fromisoformat(date['date'])
    result = await db.Homework.insert_one({
        'subject_id': subject['_id'],
        'text': message.text,
        'date': date
    })
    if result.acknowledged:
        logger.info(f"new homework for {subject['title']}")
        await message.answer('Домашнее задание добавлено.')
        await Menu.admin.set()
        await choose_action_menu(message)


@dp.callback_query_handler(lambda callback_query: callback_query.data == 'tp,zoom', state=[Menu.choose_action])
async def add_zoom_link(callback_query: types.CallbackQuery, state: FSMContext):
    subject = await state.get_data('subject')
    subject = subject['subject']
    await callback_query.message.answer(f'Пришлите ссылку на zoom, которая будет прикреплена к предмету <b>{subject["title"]}</b>')
    await Menu.add_zoom_link.set()


@dp.message_handler(state=[Menu.add_zoom_link])
async def set_zoom_link(message: types.Message, state: FSMContext):
    db = SingletonClient.get_data_base()
    subject = await state.get_data("subject")
    subject = subject['subject']
    date = await state.get_data("date")
    date = datetime.fromisoformat(date['date'])
    result = await db.ZoomLinks.insert_one({
        'subject_id': subject['_id'],
        'link': message.text,
        'date': date
    })
    if result.acknowledged:
        logger.info(f"new zoom link for {subject['title']}")
        await message.answer('Ссылка на zoom добавлена.')
        await Menu.admin.set()
        await choose_action_menu(message)


async def get_min_obj_list(user, page):
    db = SingletonClient.get_data_base()
    subjects_cursor = db.Subjects.find({
        "group_id": ObjectId(user.get("group_id"))
    })

    subjects_list = await subjects_cursor.to_list(length=await db.Groups.count_documents({}))

    logger.info(subjects_list)

    rrule_list = [(subject, list(rrule(**(subject['freq']),
                                       until=datetime(year=2020, month=12, day=31)))) for subject in subjects_list]
    min_obj_list = []
    for obj in rrule_list:
        subj = obj[0]
        dts = obj[1]
        for dt in dts:
            if datetime.now() < dt:
                min_obj_list.append((subj, dt))

    min_obj_list.sort(key=lambda x: x[1])

    try:
        return min_obj_list[page * 5: page * 5 + 5]
    except IndexError:
        return []
