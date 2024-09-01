from __future__ import annotations
from typing import Optional
import asyncio

import httpx
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from tenacity import retry, wait_fixed, stop_after_attempt

from config.config import logger

lock = asyncio.Lock()


class Ads:
    _ads_url = "http://local.adspower.net:50325/api/v1/browser/"

    def __init__(self, profile_number: int):
        self.profile_number = profile_number
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.session = httpx.AsyncClient(timeout=30)

    async def post_init(self):
        self.browser = await self._start_browser()
        self.context = self.browser.contexts[0]
        self.page = self.context.pages[0]
        await self._prepare_browser()

    async def _prepare_browser(self) -> None:
        """
        Закрывает все страницы кроме текущей
        :return: None
        """
        pages = self.context.pages
        if len(pages) > 1:
            for page in pages:
                if self.page != page:
                    await page.close()

    @retry(wait=wait_fixed(5), stop=stop_after_attempt(3))
    async def _start_browser(self) -> Browser:
        """
        Start browser or connect to existing one
        :return: Browser instance
        """
        if not (endpoint := await self._check_browser_status()):
            endpoint = await self._open_browser()
            await asyncio.sleep(10)

        pw = await async_playwright().start()
        return await pw.chromium.connect_over_cdp(endpoint, slow_mo=1000)

    @retry(wait=wait_fixed(10), stop=stop_after_attempt(3))
    async def _open_browser(self) -> dict:
        """
        Отправляет запрос на запуск браузера по номеру профиля в адс
        :return:
        """
        params = dict(serial_number=self.profile_number)
        try:
            async with lock:
                await asyncio.sleep(1)
                response = await self.session.get(self._ads_url + 'start', params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('data').get('ws').get('puppeteer')
        except Exception as e:
            logger.error(f"{self.profile_number} Ошибка запуска профиля в ADS: {e}")
            raise

    @retry(wait=wait_fixed(10), stop=stop_after_attempt(3))
    async def _check_browser_status(self) -> Optional[str]:
        """
        Проверяет статус браузера по номеру профиля
        :return: websocket endpoint
        """
        params = dict(serial_number=self.profile_number)
        try:
            async with lock:
                await asyncio.sleep(1)
                response = await self.session.get(self._ads_url + 'active', params=params)
            response.raise_for_status()
            data = response.json()
            if data['data']['status'] == 'Active':
                return data.get('data').get('ws').get('puppeteer')
            return None
        except Exception as e:
            logger.error(f"Error: {e}")
            raise

    async def close_browser(self):
        """
        Отправляет запрос на остановку браузера по номеру профиля
        """
        params = dict(serial_number=self.profile_number)
        async with lock:
            await asyncio.sleep(1)
            await self.session.get(self._ads_url + 'stop', params=params)


if __name__ == '__main__':
    pass
