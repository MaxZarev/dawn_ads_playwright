import asyncio
import re
from typing import Optional

from imap_tools import MailBox, AND
from config.config import logger

class Mail:
    link_pattern = r"https://api\.moramba\.io:3031/chromeapi/dawn/v1/user/verifylink\?key=[a-f0-9-]+"
    imap_settings = {
        'rambler.ru': 'imap.rambler.ru',
        'hotmail.com': 'imap-mail.outlook.com',
        'outlook.com': 'imap-mail.outlook.com',
        'mail.ru': 'imap.mail.ru',
        'gmail.com': 'imap.gmail.com'
    }

    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.imap_server = self.imap_settings.get(self.email.split('@')[1])
        self.mailbox: Optional[MailBox] = None

    async def check_email_valid(self) -> bool:
        """
        Проверка валидности почты, через подключение imap
        :return: True если почта валидна, иначе False
        """
        try:
            self.mailbox = await asyncio.to_thread(lambda: MailBox(self.imap_server).login(self.email, self.password))
            logger.info(f"Account: {self.email} | Email is valid")
            return True
        except Exception as e:
            logger.error(f"Account: {self.email} | Failed to check email for link: {e}")
            return False

    def search_for_link_sync(self) -> Optional[str]:
        """
        Ищет письмо с ссылкой во входящих
        :return: ссылка или None
        """
        for msg in self.mailbox.fetch(AND(from_='hello@dawninternet.com')):
            body = msg.text or msg.html
            if body:
                match = re.search(self.link_pattern, body)
                if match:
                    return match.group(0)
        return None

    def search_for_link_in_spam_sync(self, spam_folder: str
    ) -> Optional[str]:
        """
        Ищет папку спама и внутри нее письмо с ссылкой
        :param spam_folder: название папки спама
        :return: ссылка или None
        """
        if self.mailbox.folder.exists(spam_folder):
            self.mailbox.folder.set(spam_folder)
            return self.search_for_link_sync()
        return None

    async def get_confirm_link(self) -> Optional[str]:
        """
        Получение ссылки для подтверждения аккаунта из почты
        :return: возвращает ссылку подтверждения или None
        """
        self.mailbox = await asyncio.to_thread(lambda: MailBox(self.imap_server).login(self.email, self.password))
        try:
            for attempt in range(10):
                link = await asyncio.to_thread(lambda: self.search_for_link_sync())
                if link:
                    return link
                if attempt < 9:
                    await asyncio.sleep(5)
            logger.warning(f"Account: {self.email} | Не смогли найти ссылку во входящих, пойдем искать в спаме...")

            self.mailbox = await asyncio.to_thread(lambda: MailBox(self.imap_server).login(self.email, self.password))
            spam_folders = ("SPAM", "Spam", "spam", "Junk", "junk")
            for spam_folder in spam_folders:
                link = await asyncio.to_thread(lambda: self.search_for_link_in_spam_sync(spam_folder))
                if link:
                    return link
                await asyncio.sleep(5)
            logger.error(f"Account: {self.email} | Не смогли найти ссылку в спаме...")
            return None

        except Exception as e:
            logger.error(f"Account: {self.email} | Failed to get confirm link: {e}")
            return None


