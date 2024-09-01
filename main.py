import asyncio
import random
import sys

from classes.damn import Damn
from database.account import Account
from config.config import workers, shuffle_profiles, logger
from database.database import initialize_database
from utils import get_list_from_file


semaphore = asyncio.Semaphore(workers)

async def safe_run(profile: int, email: str):
    async with semaphore:
        try:
            await worker(profile, email)
        except Exception as e:
            logger.error(e)

async def worker(profile: int, email: str):
    logger.info(f"Starting worker for profile {profile} with email {email}")
    email, password = email.split(':')
    client = Damn(profile, email, password)
    try:
        await client.post_init()
        await client.run()
    except Exception as e:
        logger.error(e)
    finally:
        await client.close_browser()

async def main():
    await initialize_database()
    message = """ Выберите режим работы:
    1. Регистрация, авторизация и фарм
    2. Вывод результатов и статусов
    """
    answer = input(message)
    if answer == '1':
        profiles = get_list_from_file('config/profiles.txt')
        mails = get_list_from_file('config/emails.txt')
        if len(profiles) != len(mails):
            raise ValueError('Количество почт и профилей не совпадает')
        work_base = dict(zip(profiles, mails))

        if shuffle_profiles:
            random.shuffle(profiles)

        tasks = [safe_run(profile, email) for profile, email in work_base.items()]
        await asyncio.gather(*tasks)
    if answer == '2':
        accounts = await Account.get_accounts()
        for account in accounts:
            print(f"Profile: {account.profile} | Email: {account.email} | Reg: {account.registration_status} | Confirm: {account.confirm_status} | Login: {account.login_status} | Tasks: {account.tasks_status} | Points: {account.points}")

if __name__ == '__main__':
    asyncio.run(main())
