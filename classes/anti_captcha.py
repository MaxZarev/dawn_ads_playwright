import asyncio
from typing import Tuple

from config.config import anti_captcha_key, logger
import httpx
class AntiCaptcha:
    API_URL = "https://api.anti-captcha.com/"
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10)

    async def solve_captcha(self, image: str) -> Tuple[str, bool]:
        """
        Решение капчи
        :param image: код картинки в base 64
        :return: Кортеж с результатом решения капчи и статусом, если статус False, то вместо результата будет текст ошибки
        """
        logger.info(f'Solving captcha...')
        for _ in range(3):
            task_id, status = await self.create_task(image)
            if status:
                result, status = await self.get_task_result(task_id)
                if status:
                    return result, status
            await asyncio.sleep(3)
        return "Failed to solve captcha", False

    async def create_task(self, image: str) -> Tuple[int, bool]:
        """
        Создание задачи для решения капчи, возвращает номер задачи и статус принятия задачи
        :param image: код картинки в base 64 (body в docs https://anti-captcha.com/ru/apidoc/task-types/ImageToTextTask)
        :return: Кортеж с айди задачи и статусом принятия задачи, если статус False, то вместо айди задачи будет текст ошибки
        """
        logger.info(f'Creating task for solving captcha...')
        data = {
            "clientKey": anti_captcha_key,
            "task": {
                "type": "ImageToTextTask",
                "body": image,
                "phrase": False,
                "case": False,
                "numeric": 1,
                "math": True,
            },
        }
        try:
            response = await self.client.post(self.API_URL + 'createTask', json=data)
            response.raise_for_status()
            response_data = response.json()
            if response_data.get('errorId') != 0:
                logger.error(f"Error: {response_data.get('errorDescription')}")
                return -1, False
            return response_data.get('taskId'), True
        except Exception as e:
            logger.error(f"Error: {e}")
            return -1, False

    async def get_task_result(self, task_id: int):
        """
        Получение результата решения капчи по айди задачи
        :param task_id: айди задачи str
        :return: Кортеж с результатом решения капчи и статусом, если статус False, то вместо результата будет текст ошибки
        """
        logger.info(f'Getting captcha result...')
        data = {
            "clientKey": anti_captcha_key,
            "taskId": task_id
        }
        try:
            for _ in range(10):
                await asyncio.sleep(10)
                response = await self.client.post(self.API_URL + 'getTaskResult', json=data)
                response.raise_for_status()
                response_data = response.json()
                if response_data.get('errorId') == 0:
                    if response_data.get('status') == 'ready':
                        return response_data.get('solution').get('text'), True
        except Exception as e:
            logger.error(f"Error: {e}")
            return "Failed to get captcha result", False


