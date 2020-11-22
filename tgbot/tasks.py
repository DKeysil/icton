import aiocron
from datetime import datetime, timedelta
from loop import loop
from motor_client import SingletonClient
from dateutil.rrule import rrule
from bson.objectid import ObjectId
from loguru import logger
from bot.modules.coming_subjects.ComingSubjects import get_min_obj
from bot import bot


@aiocron.crontab('0-59/10 * * * *', loop=loop)
async def send_subj_notification():
    logger.info('Начинаю отправку уведомления о занятиях раз в 10 минут')
    time = datetime(datetime.now().year,
                    datetime.now().month,
                    datetime.now().day,
                    datetime.now().hour,
                    datetime.now().minute)

    db = SingletonClient.get_data_base()
    subscriptions_list = db.SubjectNotifications.find({}).limit(await db.SubjectNotifications.count_documents({}))

    async for subscription in subscriptions_list:
        subject_id = ObjectId(subscription['subject_id'])
        user = await db.Users.find_one({
            '_id': ObjectId(subscription['user_id'])
        })
        subject = await db.Subjects.find_one({
            '_id': subject_id
        })
        min_obj = get_min_obj([subject])

        logger.info(min_obj)

        if min_obj[1] - time == timedelta(minutes=20):
            string = f'Через 20 минут у вас начнется занятие - <b>{min_obj[0]["title"]}</b> - Аудитория {min_obj[0]["audience"]}'
            await bot.send_message(chat_id=user['telegram_id'], text=string)


@aiocron.crontab('0 20 */1 * *', loop=loop)
async def send_everyday_subj_notification():
    logger.info('Начинаю отправку ежедневных уведомлений о занятиях')
    day_start = datetime(datetime.now().year,
                         datetime.now().month,
                         datetime.now().day,
                         0,
                         0) + timedelta(days=1)
    day_end = datetime(datetime.now().year,
                       datetime.now().month,
                       datetime.now().day,
                       23,
                       59) + timedelta(days=1)

    db = SingletonClient.get_data_base()
    subscriptions_list = db.SubjectNotifications.find({}).sort('user_id', 1).limit(await db.SubjectNotifications.count_documents({}))
    users = {}

    async for subscription in subscriptions_list:
        subject_id = ObjectId(subscription['subject_id'])
        user = await db.Users.find_one({
            '_id': ObjectId(subscription['user_id'])
        })

        subject = await db.Subjects.find_one({
            '_id': subject_id
        })
        min_obj = get_min_obj([subject])
        if users.get(user.get('telegram_id')):
            users[user['telegram_id']].append(min_obj)
            logger.info('append new min_obj')
        else:
            users.update({user['telegram_id']: [min_obj]})
            logger.info('update users dict')

    logger.info(users)
    for telegram_id in users.keys():
        logger.info(telegram_id)
        string = 'Список занятий на завтра:\n\n'
        for min_obj in users[telegram_id]:
            if day_start < min_obj[1] < day_end:
                string += f'{min_obj[1].strftime("<b>%H:%M</b>")} - {min_obj[0]["title"]} - Аудитория {min_obj[0]["audience"]}\n'
        if string != 'Список занятий на завтра:\n\n':
            await bot.send_message(chat_id=telegram_id, text=string)
        else:
            await bot.send_message(chat_id=telegram_id, text='Завтра занятий нет :)')
