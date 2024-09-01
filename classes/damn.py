from typing import Optional

from tenacity import retry, wait_fixed, stop_after_attempt
from playwright.async_api import expect

from classes.ads import Ads
from classes.mail import Mail
from config.config import ref_code, logger

from classes.anti_captcha import AntiCaptcha
from database.account import Account


class Damn(Ads):
    _url = 'chrome-extension://fpdkjdnhkakefebpekbdhillbhonfjjp/'

    def __init__(
            self,
            profile_number: int,
            email: str,
            password: str,
    ):
        super().__init__(profile_number)
        self.anti_captcha = AntiCaptcha()
        self.mail = Mail(email, password)
        self.db: Optional[Account] = None

    async def run(self):
        """
        Запуск процесса регистрации, авторизации и фарма.
        :return: None
        """

        if not await self.mail.check_email_valid():
            with open('emails_failed.txt', 'a') as f:
                f.write(f'{self.mail.email}\n')
            return

        account = await Account().create_account(profile=self.profile_number, email=self.mail.email)
        if not account.registration_status:
            await self.register()
        if not account.confirm_status:
            await self.confirm_email()
        if not account.login_status:
            await self.login()
        points = await self.get_points()
        await Account.set_points(self.profile_number, points)
        logger.info(f"Profile {self.profile_number} finished with {points} points")

    @retry(wait=wait_fixed(5), stop=stop_after_attempt(3))
    async def register(self):
        """
        Register new account
        :return:
        """
        logger.info(f"Starting registration for profile {self.profile_number} with email {self.mail.email}")
        await self.page.goto(self._url + 'signup.html', wait_until='load')
        answer = await self.get_and_solve_captcha()

        await self.page.locator('id=fullname').fill(self.mail.email.split('@')[0])
        await self.page.locator('id=username').fill(self.mail.email)
        await self.page.locator('id=password').fill(self.mail.password)
        await self.page.locator('id=cnfpassword').fill(self.mail.password)
        await self.page.locator('id=refercode').fill(ref_code)

        await self.page.get_by_placeholder('?').fill(answer)
        await self.page.get_by_role('button', name='Create account').click()
        await self.page.wait_for_timeout(5000)

        error_locator = self.page.locator('id=error')
        if await error_locator.is_visible(timeout=5000):
            await self.page.reload()
            logger.error(f'{self.profile_number} Error during registration')
            raise Exception('Error during registration')

        await expect(self.page.get_by_text('Account created!')).to_be_visible()
        await Account.change_status(self.profile_number, 'registration')

    async def confirm_email(self):
        """
        Confirm email
        :return:
        """
        if (link := await self.mail.get_confirm_link()):
            await self.page.goto(link, wait_until='load')
            await Account.change_status(self.profile_number, 'confirm')

    @retry(wait=wait_fixed(5), stop=stop_after_attempt(3))
    async def login(self):
        logger.info(f"Starting login for profile {self.profile_number} with email {self.mail.email}")
        await self.page.goto(self._url + 'signin.html', wait_until='load')
        await self.page.locator('id=email').fill(self.mail.email)
        await self.page.locator('id=password').fill(self.mail.password)
        answer = await self.get_and_solve_captcha()
        await self.page.locator('id=puzzelAns').fill(answer)
        await self.page.get_by_role('button', name='Login').click()
        await self.page.wait_for_timeout(5000)
        await self.page.locator('id=isnetworkconnected').wait_for(state='visible')
        await Account.change_status(self.profile_number, 'login')
        await self.page.get_by_role('button', name='Boost rewards').click()
        await self.page.locator('id=twitterShareBtn').click(no_wait_after=True, timeout=5000)
        await self.page.wait_for_timeout(5000)
        await self.page.locator('id=discordShareBtn').click(no_wait_after=True, timeout=5000)
        await self.page.wait_for_timeout(5000)
        await self.page.locator('id=telegramShareBtn').click(no_wait_after=True, timeout=5000)
        await self.page.wait_for_timeout(5000)
        await self.page.get_by_text('Back').click()
        await self.page.bring_to_front()
        await self.page.wait_for_timeout(5000)
        await Account.change_status(self.profile_number, 'tasks')

    async def get_and_solve_captcha(self) -> str:
        """
        Ждет появления капчи на странице и решает ее
        :return: решенная капча
        """
        await self.page.locator('id=captcha').wait_for(state='visible')
        image = await self.page.locator('id=puzzleImage').get_attribute('src')
        image_base64 = image.split(',')[1]
        answer, status = await self.anti_captcha.solve_captcha(image_base64)
        if not status:
            logger.error(f'{self.profile_number} Failed to solve captcha')
            raise Exception('Failed to solve captcha')
        return answer

    async def get_points(self) -> str:
        """
        Получает актуальное количество поинтов
        :return: количество поинтов
        """
        logger.info(f"Getting points for profile {self.profile_number}")
        await self.page.goto(self._url + 'dashboard.html', wait_until='load')
        point_locator = self.page.locator('id=dawnbalance')
        await point_locator.wait_for(state='visible')
        points = await point_locator.inner_text()
        return points
