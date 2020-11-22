from bot import dp, types, FSMContext
from motor_client import SingletonClient
from datetime import datetime
from loguru import logger
from dateutil.rrule import rrule
from bson import objectid


@dp.message_handler(lambda message: message.text == 'Ближайшие пары')
@dp.message_handler(commands=['subj'])
async def coming_subjects(message: types.Message):
    # TODO: 1) найти пользователя 2) найти его группу 3) найти предметы, которые относятся к его группе 4) найти
    #  ближайший и вернуть информацию 5) добавить кнопку, чтобы перелестнуть на следующий ближайший
    telegram_id = message.from_user.id
    db = SingletonClient.get_data_base()

    user = await db.Users.find_one({
        "telegram_id": telegram_id
    })

    if not user:
        return await message.reply('Вы не зарегистрированы. Зайдите в бота и напишите <code>/start</code>')
    elif not user.get('group_id'):
        return await message.reply('Вы не указали группу.')

    group = await db.Groups.find_one({
        "_id": user.get("group_id")
    })

    subjects_cursor = db.Subjects.find({
        "group_id": objectid.ObjectId(user.get("group_id"))
    })

    subjects_list = await subjects_cursor.to_list(length=await db.Subjects.count_documents({}))
    logger.info(user)
    logger.info(group)

    logger.info(f'from {user["telegram_id"]}, group {group["title"]}, subjects_list {subjects_list}')

    min_obj = get_min_obj(subjects_list)

    logger.info(f'from {user["telegram_id"]}, group {group["title"]}, Closest subj {min_obj[0]}')
    min_subj = min_obj[0]

    string, markup = await get_coming_subjects_string(min_obj, message, user)

    # TODO: добавить кнопку "посмотреть ДЗ"
    # перелистывание предметов
    """
    callback_data:
    1) cs - название модуля
    2) l, r, n - left, right, none
    3) int - номер страницы
    4) user_id
    """
    if get_min_obj(subjects_list, 1):
        button_1 = types.InlineKeyboardButton(text="❌", callback_data=f'cs,n,0,{user["_id"]}')
        button_2 = types.InlineKeyboardButton(text="➡️", callback_data=f'cs,r,1,{user["_id"]}')
        markup.row(button_1, button_2)

    if _id := min_subj.get('teacher_id'):
        teacher = await db.Teachers.find_one({
            '_id': _id
        })
        string += f'Преподаватель: {teacher["second_name"] + teacher["first_name"]}\n'

    await message.answer(string, reply_markup=markup, disable_web_page_preview=True)


@dp.callback_query_handler(lambda callback_query: callback_query.data.split(',')[0] == 'cs')
async def handle_cs_callback_query(callback_query: types.CallbackQuery):
    """
    Обработчик нажатия на кнопку под сообщением с ближайшей парой.
    Лямбда проверяет, чтобы обрабатывалось только y кнопки
    Args:
        callback_query (types.CallbackQuery): Документация на сайте телеграма
    """

    split_data = callback_query.data.split(',')
    if split_data[1] == 'n':
        return await callback_query.answer(text='Там больше ничего нет...')

    page = int(split_data[2])
    user_id = objectid.ObjectId(split_data[3])

    db = SingletonClient.get_data_base()

    user = await db.Users.find_one({
        "_id": user_id
    })

    subjects_cursor = db.Subjects.find({
        "group_id": objectid.ObjectId(user.get("group_id"))
    })

    subjects_list = await subjects_cursor.to_list(length=await db.Subjects.count_documents({}))

    min_obj = get_min_obj(subjects_list, page)
    min_subj = min_obj[0]

    string, markup = await get_coming_subjects_string(min_obj, callback_query.message, user)

    # Проверяет, есть ли пары на предыдущих страницах.
    left_min_obj = get_min_obj(subjects_list, page - 1)
    if left_min_obj:
        left_button = types.InlineKeyboardButton(
            text='⬅️', callback_data=f'cs,l,{page - 1},{user_id}')
    else:
        left_button = types.InlineKeyboardButton(
            text='❌', callback_data=f'cs,n,{page},{user_id}')

    # Проверяет, есть ли пары на следующих страницах.
    right_min_obj = get_min_obj(subjects_list, page + 1)
    if right_min_obj:
        right_button = types.InlineKeyboardButton(
            text='➡️', callback_data=f'cs,r,{page + 1},{user_id}')
    else:
        right_button = types.InlineKeyboardButton(
            text='❌', callback_data=f'cs,n,{page},{user_id}')

    markup.row(left_button, right_button)

    _message = await callback_query.message.edit_text(string, reply_markup=markup, parse_mode='HTML',
                                                      disable_web_page_preview=True)
    await callback_query.answer()


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('SubscribeNotifications'))
async def subscribe_update(callback_query: types.CallbackQuery):
    subject_id = callback_query.data.split(',')[1]
    db = SingletonClient.get_data_base()
    telegram_id = callback_query.from_user.id
    user = await db.Users.find_one({
        "telegram_id": telegram_id
    })

    logger.info(f'subscribe notifications request from {telegram_id}')

    if not user:
        logger.info(f'subscribe notifications request from {telegram_id}. user not registered')
        return await callback_query.answer('Вы не зарегистрированы в боте.')

    subscription = await db.SubjectNotifications.find_one({
        "user_id": user['_id'],
        "subject_id": objectid.ObjectId(subject_id)
    })

    if subscription:
        logger.info(f'subscribe notifications request from {telegram_id}. user already subscribed')
        return await callback_query.answer('Вы уже подписаны на напоминания.')

    result = await db.SubjectNotifications.insert_one({
        "user_id": user['_id'],
        "subject_id": objectid.ObjectId(subject_id)
    })

    if result.acknowledged:
        logger.info(f'subscribe notifications request from {telegram_id}. user successfully subscribed')
        return await callback_query.answer('Вы подписались на напоминания о паре.')


def get_min_obj(subjects_list, item: int = 0):
    if item < 0:
        return None
    now = datetime.now()

    rrule_list = [(subject, list(rrule(**(subject['freq']),
                                       until=datetime(year=2020, month=12, day=31)))) for subject in subjects_list]
    min_obj_list = []
    for obj in rrule_list:
        subj = obj[0]
        dts = obj[1]
        for dt in dts:
            if now < dt:
                min_obj_list.append((subj, dt))
    min_obj_list.sort(key=lambda x: x[1])
    try:
        logger.info(f"min obj {min_obj_list[item]}, item {item}")
        return min_obj_list[item]
    except IndexError:
        return None


async def get_coming_subjects_string(min_obj, message: types.Message, user):
    db = SingletonClient.get_data_base()
    min_subj = min_obj[0]
    markup = types.InlineKeyboardMarkup()
    if message.chat.type == 'private':
        string = '<b>Ваше ближайшее занятие:</b>\n'
    else:
        string = f'<b>Ближайшие занятие для {user["second_name"]} {user["first_name"]}:</b>\n'
    string += f'{min_subj["title"]}\n'
    string += f'Аудитория: {min_subj["audience"]}\n'
    string += f'Когда: {min_obj[1].strftime("<b>%H:%M</b> %d.%m.%Y")}\n'
    # Прикрепление ссылки на зум.
    zoom_link = await db.ZoomLinks.find_one({
        "date": min_obj[1],
        "subject_id": min_subj['_id']
    })
    if zoom_link:
        string += f"Ссылка на <a href=\"{zoom_link['link']}\">zoom</a>."

    # кнопка подписки на напоминания
    button = types.InlineKeyboardButton(text="🔔 Подписаться на напоминания",
                                        callback_data=f'SubscribeNotifications,{min_subj["_id"]}')
    markup.add(button)

    return string, markup
