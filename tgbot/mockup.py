from motor_client import SingletonClient
from dateutil.rrule import WEEKLY
from datetime import datetime
import asyncio


async def fill_db():
    db = SingletonClient.get_data_base()
    result = await db.Groups.insert_many([
        {
            "admin_id": 284431,
            "title": "K3221"
        },
        {
            "admin_id": 345234639,
            "title": "K3222"
        }
    ])

    group_1, group_2 = result.inserted_ids

    await db.Subjects.insert_many([
        {
            "title": "Математика. Практика.",
            "freq": {"FREQ": WEEKLY, "interval": 2, "byweekday": 3, "dt": datetime(year=2020, month=11, day=26, hour=15, minute=20)},
            "group_id": group_1,
            "audience": "318"
        },
        {
            "title": "Математика. Практика.",
            "freq": {"FREQ": WEEKLY, "interval": 2, "byweekday": 2,
                          "dt": datetime(year=2020, month=11, day=25, hour=11, minute=40)},
            "group_id": group_2,
            "audience": "330"
        },
        {
            "title": "Математика. Лекция.",
            "freq": {"FREQ": WEEKLY, "byweekday": 3, "dt": datetime(year=2020, month=11, day=26, hour=17, minute=00)},
            "group_id": group_1,
            "audience": "550"
        }
    ])


loop = asyncio.get_event_loop()
loop.run_until_complete(fill_db())
