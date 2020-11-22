from bot import dp
from aiogram import executor
from loguru import logger
from loop import loop


if __name__ == "__main__":

    logger.info('Bot is starting.')

    executor.start_polling(dp, loop=loop, skip_updates=True)
