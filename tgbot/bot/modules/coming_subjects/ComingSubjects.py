from bot import dp, types, FSMContext
from motor_client import SingletonClient


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
