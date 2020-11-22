from motor_client import SingletonClient
from dateutil.rrule import WEEKLY, DAILY
from datetime import datetime
import asyncio
from bson.objectid import ObjectId


async def fill_db():
    db = SingletonClient.get_data_base()
    await db.Groups.delete_many({})
    result = await db.Groups.insert_many([
        {
            '_id': ObjectId('5fb8f4b3c921b198c8613ae8'),
            "admin_id": 284431,
            "title": "K3221"
        },
        {
            '_id': ObjectId('5fb8f4b3c921b198c8613ae9'),
            "admin_id": 345234639,
            "title": "K3222"
        }
    ])

    group_1, group_2 = result.inserted_ids

    await db.Subjects.delete_many({})

    result = await db.Subjects.insert_many([
        {
            '_id': ObjectId('5fb8f62e9430d03786e79896'),
            "title": "Математика. Практика.",
            "freq": {"freq": WEEKLY, "interval": 2, "byweekday": 3, "dtstart": datetime(year=2020, month=11, day=26, hour=15, minute=20)},
            "group_id": group_1,
            "audience": "318"
        },
        {
            '_id': ObjectId('5fb8f62e9430d03786e79897'),
            "title": "Математика. Практика.",
            "freq": {"freq": WEEKLY, "interval": 2, "byweekday": 2,
                          "dtstart": datetime(year=2020, month=11, day=25, hour=11, minute=40)},
            "group_id": group_2,
            "audience": "330"
        },
        {
            '_id': ObjectId('5fb8f62e9430d03786e79898'),
            "title": "Математика. Лекция.",
            "freq": {"freq": WEEKLY, "byweekday": 3, "dtstart": datetime(year=2020, month=11, day=26, hour=17, minute=00)},
            "group_id": group_1,
            "audience": "550"
        },
        {
            '_id': ObjectId('5fb8f62e9430d03786e79899'),
            "title": "Физика. Постоянно.",
            "freq": {"freq": DAILY, "dtstart": datetime(year=2020, month=11, day=22, hour=10, minute=40)},
            "group_id": group_1,
            "audience": "123"
        }
    ])

    subject_1, subject_2, subject_3, subject_4 = result.inserted_ids

    # await db.ZoomLinks.delete_many({})
    #
    # await db.ZoomLinks.insert_one({
    #     "subject_id": subject_3,
    #     "date": datetime(2020, 11, 26, 17, 0),
    #     "link": "https://itmo.zoom.us/j/81197734335?pwd=VEMyREVQTEdSWVRVc2dPMWFBS2kyUT09"
    # })


loop = asyncio.get_event_loop()
loop.run_until_complete(fill_db())
