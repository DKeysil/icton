from bot import dp
from aiogram import executor
import asyncio
from loguru import logger


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    logger.info('Bot is starting.')

    executor.start_polling(dp, loop=loop, skip_updates=True)
