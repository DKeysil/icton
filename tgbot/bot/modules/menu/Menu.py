from bot import dp, types
from motor_client import SingletonClient


@dp.message_handler(lambda message: message.chat.type == 'private', commands=['menu'])
async def start(message: types.Message):
    markup = await menu_markup(message.from_user.id)
    await message.answer('Теперь вам доступно меню.', reply_markup=markup)


async def menu_markup(telegram_id):
    db = SingletonClient.get_data_base()

    user = await db.Users.find_one({
        "telegram_id": telegram_id
    })

    group = await db.Groups.find_one({
        "_id": user.get("group_id")
    })

    coming_subjects = types.KeyboardButton('Ближайшие пары')
    btn_list = [
        [coming_subjects]
    ]
    if user.get('_id') == group.get('admin_id'):
        admin_menu = types.KeyboardButton('Функции админа')
        btn_list.append([admin_menu])

    menu_keyboard_markup = types.ReplyKeyboardMarkup(btn_list)
    return menu_keyboard_markup
