from bot import dp, types, FSMContext
from motor_client import SingletonClient
from datetime import datetime
from loguru import logger
from dateutil.rrule import rrule


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
        return await message.reply('Вы не указали группу. Зайдите в бота и напишите <code>/set_group</code>')

    group = await db.Groups.find_one({
        "_id": user.get("group_id")
    })

    subjects_cursor = db.Subjects.find({
        "group_id": group.get("_id")
    })

    subjects_list = await subjects_cursor.to_list(length=await db.Groups.count_documents({}))

    logger.info(f'from {user["telegram_id"]}, group {group["title"]}, subjects_list {subjects_list}')

    now = datetime.now()

    rrule_list = [(subject, list(rrule(**(subject['freq']),
                                       until=datetime(year=2020, month=12, day=31)))) for subject in
                  subjects_list]
    min_obj = (None, datetime(year=2025, month=12, day=31))
    for obj in rrule_list:
        subj = obj[0]
        dts = obj[1]
        for dt in dts:
            if now < dt < min_obj[1]:
                min_obj = (subj, dt)
                break

    if not min_obj[0]:
        logger.info(f'from {user["telegram_id"]}, group {group["title"]}, Ближайшая пара не найдена')
        return await message.answer('Ближайшая пара не найдена')

    logger.info(f'from {user["telegram_id"]}, group {group["title"]}, Closest subj {min_obj[0]}')
    min_subj = min_obj[0]
    string = '<b>Ваше ближайшее занятие:</b>\n'
    string += f'{min_subj["title"]}\n'
    string += f'Аудитория: {min_subj["audience"]}\n'
    string += f'Когда: {min_obj[1].strftime("<b>%H:%M</b> %d.%m.%Y")}'
    # TODO: добавить прикрепление ссылки на зум, если она есть.
    # TODO: добавить кнопку, чтобы записаться на напоминания
    # TODO: добавить кнопку "посмотреть ДЗ"
    # TODO: добавить кнопку, чтобы перелестнуть на следующий ближайший
    if _id := min_subj.get('teacher_id'):
        teacher = await db.Teachers.find_one({
            '_id': _id
        })
        string += f'Преподаватель: {teacher["second_name"] + teacher["first_name"]}\n'

    await message.answer(string)
